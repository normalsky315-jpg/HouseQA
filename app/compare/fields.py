"""可比對欄位的註冊表（site-agnostic）。

每個 :class:`FieldSpec` 定義一個標準欄位如何從 :class:`Project`（HouseQA）
與 :class:`SourceRecord`（任一外部來源）取值，以及取值後該套用的正規化器。

比對引擎只依賴本註冊表與規則，不認得任何特定網站，因此新增資料來源
（樂居、建商官網……）時，只要該來源的 Parser 以相同 key 填入 SourceRecord，
即可自動納入比對，無需修改引擎。
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from app.models.project import Project
from app.models.source_record import SourceRecord
from app.normalize.address import AddressNormalizer
from app.normalize.area import AreaNormalizer
from app.normalize.floor import FloorNormalizer
from app.normalize.text import clean_text, extract_number, sum_numbers

_addr_norm = AddressNormalizer()
_floor_norm = FloorNormalizer()
_area_norm = AreaNormalizer()

_CJK_DIGITS = {"一": "1", "二": "2", "三": "3", "四": "4", "五": "5", "六": "6"}

# 視為「未填寫」的佔位字串，正規化後當作空值（比對結果為 WARNING 而非 FAIL）。
_PLACEHOLDERS = {"", "-", "暫無", "無", "待定", "未定", "待補", "待確認", "各期不同", "n/a"}
# 交屋時間中代表「已可交屋」的同義詞，統一為「完工」。
_DONE_TERMS = ("已完工", "隨時交屋", "可立即交屋", "立即交屋", "現房", "成屋", "即可交屋")
# 建商名稱常見後綴，比對前移除只留核心字號。
_DEV_SUFFIXES = (
    "股份有限公司", "有限公司", "建設開發", "開發", "建設", "營建", "營造",
    "建築", "實業", "事業", "機構", "地產", "國際",
)


# --------------------------------------------------------------------------- #
# 共用文字解析輔助
# --------------------------------------------------------------------------- #
def _find_pct(text: str, label: str) -> float | None:
    """從文字擷取「<label>數值%」的百分比數值（取範圍中的第一個）。"""
    match = re.search(rf"{label}\s*約?\s*([\d.]+)", clean_text(text))
    return float(match.group(1)) if match else None


def _find_base_area(text: str) -> float | None:
    """從 notes 擷取「基地<數值>坪」的基地面積。"""
    match = re.search(r"基地\s*([\d.]+)\s*坪", clean_text(text))
    return float(match.group(1)) if match else None


def _find_buildings(text: str) -> int | None:
    """擷取棟數（``2棟`` / ``2棟20層`` → 2）。"""
    match = re.search(r"(\d+)\s*棟", clean_text(text))
    return int(match.group(1)) if match else None


_PARKING_RE = re.compile(r"(?:全)?(?:平面|機械|車位|坡道)[^；;。、]*")


def _find_parking(text: str) -> int | None:
    """加總車位描述中的數量（``平面130+機械44位`` → 174）。"""
    cleaned = clean_text(text)
    total = 0
    found = False
    for seg in _PARKING_RE.findall(cleaned):
        for num in re.findall(r"\d+", seg):
            total += int(num)
            found = True
    return total if found else None


def _expand_room_range(match: re.Match[str]) -> str:
    """把 ``2~3房`` 展開成 ``2房3房``。"""
    low, high = int(match.group(1)), int(match.group(2))
    if 0 < low <= high <= 9 and high - low < 8:
        return "".join(f"{i}房" for i in range(low, high + 1))
    return match.group(0)


def normalize_layout(value: Any) -> str:
    """把格局描述正規化為房型集合字串（``2房3房``）。

    處理：中文數字轉阿拉伯數字、展開 ``2~3房`` 範圍、移除 ``+1`` 之類的加房
    註記，再擷取所有 ``N房`` 房型去重排序，使 ``二房…三房``、``2~3房``、
    ``2房／3房`` 正規化後一致。
    """
    text = clean_text(value)
    for cjk, ar in _CJK_DIGITS.items():
        text = text.replace(cjk, ar)
    text = re.sub(r"\s+", "", text)  # 去空白，吸收樂居「2 房」之類寫法
    text = re.sub(r"(\d)[~～\-](\d)房", _expand_room_range, text)
    text = re.sub(r"\+\d+", "", text)  # 去除 3+1房 的「+1」避免誤判出 1房
    rooms = sorted(set(re.findall(r"\d房", text)))
    return "".join(rooms)


_ITEM_PLACEHOLDER_RE = re.compile(r"待補|待確認|待公布|未公布|資訊待補|建材待補")


def clean_items(items: Any) -> list[str]:
    """過濾建材清單中的佔位字（``資訊待補``、``建材待補``）。

    全部都是佔位字時回傳空清單，使該欄位比對為 WARNING（未填）而非 FAIL。
    """
    if not isinstance(items, (list, tuple)):
        return []
    return [
        str(i) for i in items
        if str(i).strip() and not _ITEM_PLACEHOLDER_RE.search(str(i))
    ]


def normalize_name(value: Any) -> str:
    """建案名稱正規化：移除分隔符號與空白。"""
    return re.sub(r"[\s・·.,，、／/]+", "", clean_text(value))


def normalize_handover(value: Any) -> str:
    """交屋時間正規化。

    將「第三季度／第3季」轉成 ``Q3``、「已完工／隨時交屋」等同義詞統一為
    ``完工``、移除「年」與空白，使 ``2029Q3`` 與 ``2029年第三季度`` 一致；
    ``待定`` 等佔位字則視為空值。
    """
    text = clean_text(value)
    if text in _PLACEHOLDERS:
        return ""
    if any(term in text for term in _DONE_TERMS):
        return "完工"
    text = re.sub(
        r"第\s*([一二三四1-4])\s*季(?:度)?",
        lambda m: "Q" + _CJK_DIGITS.get(m.group(1), m.group(1)),
        text,
    )
    return re.sub(r"[年\s]", "", text).upper()


def normalize_permit(value: Any) -> str:
    """建照正規化。

    移除括號、「築字第」等贅字與末尾的換照版本號（``-02``），使
    ``109高市工建00940號`` 與 ``(109)高市工建築字第00940-02號`` 一致；
    ``-``／``暫無`` 等視為空值。
    """
    text = clean_text(value)
    if text in _PLACEHOLDERS:
        return ""
    text = re.sub(r"[（）()\s]", "", text)
    text = text.replace("築", "").replace("字", "").replace("第", "")
    return re.sub(r"-\d+(號)?$", r"\1", text)


def normalize_dev(value: Any) -> str:
    """建商名稱正規化：去括號補充與公司後綴，只留核心字號。

    使 ``興連城開發``、``興連城建設有限公司`` 正規化後皆為 ``興連城``。
    """
    text = re.sub(r"[（(].*?[）)]", "", clean_text(value))
    for suffix in _DEV_SUFFIXES:
        text = text.replace(suffix, "")
    return re.sub(r"\s", "", text)


@dataclass(frozen=True, slots=True)
class FieldSpec:
    """單一可比對欄位的定義。

    Attributes:
        key: 標準欄位 key，對應 config.yaml 的規則設定。
        label: 報表顯示用的中文名稱。
        house: 從 :class:`Project` 取值的函式。
        source: 從 :class:`SourceRecord` 取值的函式。
        normalizer: 取值後套用的正規化器（可為 ``None``）。
    """

    key: str
    label: str
    house: Callable[[Project], Any]
    source: Callable[[SourceRecord], Any]
    normalizer: Callable[[Any], Any] | None = None


# --------------------------------------------------------------------------- #
# 標準欄位註冊表
# --------------------------------------------------------------------------- #
FIELD_SPECS: list[FieldSpec] = [
    FieldSpec("name", "名稱", lambda p: p.name, lambda s: s.get("name"), normalize_name),
    FieldSpec("dev", "建商", lambda p: p.dev, lambda s: s.get("dev"), normalize_dev),
    FieldSpec("addr", "基地位置", lambda p: p.addr, lambda s: s.get("addr"), _addr_norm.normalize),
    FieldSpec("floor", "樓層", lambda p: p.floor, lambda s: s.get("floor"), _floor_norm.normalize),
    FieldSpec("buildings", "棟數", lambda p: _find_buildings(p.layout), lambda s: s.get("buildings")),
    FieldSpec("units", "戶數", lambda p: p.units, lambda s: s.get("units"), extract_number),
    FieldSpec("parking", "車位", lambda p: _find_parking(p.layout), lambda s: s.get("parking"), sum_numbers),
    FieldSpec("layout", "格局", lambda p: p.layout, lambda s: s.get("layout"), normalize_layout),
    FieldSpec("base_area", "基地面積", lambda p: _find_base_area(p.notes), lambda s: s.get("base_area"), _area_norm.normalize),
    FieldSpec("public_ratio", "公設比", lambda p: _find_pct(p.notes, "公設比"), lambda s: s.get("public_ratio"), extract_number),
    FieldSpec("coverage_ratio", "建蔽率", lambda p: _find_pct(p.notes, "建蔽率"), lambda s: s.get("coverage_ratio"), extract_number),
    FieldSpec("permit", "建照", lambda p: p.permit, lambda s: s.get("permit"), normalize_permit),
    FieldSpec("handover", "交屋時間", lambda p: p.handover, lambda s: s.get("handover"), normalize_handover),
    FieldSpec("loan", "貸款成數", lambda p: p.loan, lambda s: s.get("loan"), extract_number),
    FieldSpec("kit", "廚具", lambda p: clean_items(p.kit), lambda s: s.get("materials")),
    FieldSpec("bath", "衛浴", lambda p: clean_items(p.bath), lambda s: s.get("materials")),
    # 註：data.json 的 `other`（特色配備／賣點）是使用者自行整理的行銷重點，
    # 並非規格建材，591 無對應欄位可核對，故「不」納入比對，以免產生假警報。
    # 真正的建材品牌由上方「廚具」「衛浴」負責核對。
]
