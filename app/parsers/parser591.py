"""591 新建案詳情頁解析器。

591 的詳情頁由多個「標籤 → 值」列組成（``li > span/strong + p``）。本解析器
以「標籤文字」為錨點抽取資料，而非依賴固定 CSS class，因此 591 改版調整版面
時仍具相當的容錯能力（符合附註說明對 Parser 的要求）。
"""

from __future__ import annotations

import re

from bs4 import BeautifulSoup

from app.models.source_record import SourceRecord
from app.normalize.text import clean_text
from app.parsers.base import Parser
from app.utils.logger import get_logger

logger = get_logger(__name__)

# 591 標籤文字 → HouseQA 標準欄位 key。
_LABEL_MAP: dict[str, str] = {
    "投資建設": "dev",
    "基地地址": "addr",
    "樓層規劃": "floor",
    "車位規劃": "parking",
    "格局規劃": "layout",
    "公設比": "public_ratio",
    "建蔽率": "coverage_ratio",
    "基地面積": "base_area",
    "建造執照": "permit",
    "交屋時間": "handover",
    "貸款成數": "loan",
    "建材說明": "materials",
    "建案類別": "status",
    "營造公司": "constructor",
    "建築設計": "architect",
}

# 值字串中需移除的雜訊（地圖／導航連結文字）。
_NOISE_RE = re.compile(r"(查看地圖|導航)\s*[>＞]?")


class Parser591(Parser):
    """591 詳情頁 → SourceRecord。"""

    source = "591"

    def parse(self, html: str, url: str = "") -> SourceRecord:
        """解析 591 詳情頁 HTML。

        Args:
            html: 頁面 HTML。
            url: 原始網址。

        Returns:
            填妥標準欄位的 :class:`SourceRecord`。
        """
        soup = BeautifulSoup(html, "lxml")
        raw = self._extract_rows(soup)

        fields: dict[str, object] = {}
        for label, value in raw.items():
            key = _LABEL_MAP.get(label)
            if key and value:
                fields[key] = value

        fields["name"] = self._extract_name(soup)
        self._split_building_units(raw, fields)

        logger.info("解析 591 完成：%s（%d 個欄位）", fields.get("name"), len(fields))
        return SourceRecord(source=self.source, url=url, fields=fields, raw=raw)

    # ------------------------------------------------------------------ #
    # 內部解析輔助
    # ------------------------------------------------------------------ #
    def _extract_rows(self, soup: BeautifulSoup) -> dict[str, str]:
        """抽取所有「標籤 → 值」列。

        以 ``li`` 為單位，標籤取自第一個 ``span``／``strong`` 的直接文字
        （略過 tooltip 說明），值取自 ``p`` 元素。
        """
        rows: dict[str, str] = {}
        for li in soup.find_all("li"):
            label_el = li.find(["span", "strong"])
            value_el = li.find("p")
            if not label_el or not value_el:
                continue

            self._strip_noise(value_el)
            label = self._direct_text(label_el)
            value = _NOISE_RE.sub("", value_el.get_text(" ", strip=True)).strip()
            if label and value and label not in rows:
                rows[label] = clean_text(value)
        return rows

    @staticmethod
    def _strip_noise(element) -> None:
        """移除值元素中的互動／提示子節點（如「付款方式」按鈕、tooltip）。"""
        noise_classes = {"paymethod", "t5-tooltip", "t5-tooltip__arrow"}
        for tag in element.find_all(["i"]):
            tag.decompose()
        for tag in element.find_all(class_=True):
            if noise_classes.intersection(tag.get("class", [])):
                tag.decompose()

    @staticmethod
    def _direct_text(element) -> str:
        """取得元素的直接文字（忽略巢狀子元素，如 tooltip）。"""
        for child in element.children:
            if isinstance(child, str):
                text = clean_text(child)
                if text:
                    return text
        return clean_text(element.get_text(" ", strip=True))

    @staticmethod
    def _extract_name(soup: BeautifulSoup) -> str:
        """從 ``<title>`` 擷取建案名稱。

        標題格式為「<建案名>建案詳情-591新建案」，取「建案詳情」前的部分。
        """
        title = clean_text(soup.title.get_text() if soup.title else "")
        name = re.split(r"建案詳情|[-－]591", title)[0]
        return name.strip()

    @staticmethod
    def _split_building_units(raw: dict[str, str], fields: dict[str, object]) -> None:
        """從「棟戶規劃」拆出棟數與戶數（``1幢，2棟，314戶`` → 2 / 314）。"""
        text = raw.get("棟戶規劃", "")
        if not text:
            return
        buildings = re.search(r"(\d+)\s*棟", text)
        units = re.search(r"(\d+)\s*戶", text)
        if buildings:
            fields["buildings"] = int(buildings.group(1))
        if units:
            fields["units"] = int(units.group(1))
