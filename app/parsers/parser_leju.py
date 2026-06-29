"""樂居社區頁解析器。

樂居以 ``dt`` 標籤／``dd`` 值成對陳列社區資料，解析以標籤文字為錨點，
轉成中立的 :class:`SourceRecord`。
"""

from __future__ import annotations

import re

from bs4 import BeautifulSoup

from app.models.source_record import SourceRecord
from app.normalize.text import clean_text
from app.parsers.base import Parser
from app.utils.logger import get_logger

logger = get_logger(__name__)

# 樂居標籤（已去除冒號）→ HouseQA 標準欄位 key。
_LABEL_MAP: dict[str, str] = {
    "地址": "addr",
    "總戶數": "units",
    "公設比": "public_ratio",
    "基地面積": "base_area",
    "車位數量": "parking",
    "建設公司": "dev",
    "坪數資料": "layout",
    "格局與坪數": "layout",
    # 以下保留於 raw，目前不參與比對：
    "總樓高": "floors_above",  # 樂居僅提供地上樓層，無地下，故不映射到比對用 floor
    "營造公司": "constructor",
    "建築設計": "architect",
    "土地使用分區": "zoning",
    "管理費": "mgmt_fee",
    "房屋開價": "price",
    "屋齡": "age",
}
_COMPARED_KEYS = {
    "addr", "units", "public_ratio", "base_area", "parking", "dev", "layout",
}


class ParserLeju(Parser):
    """樂居社區頁 → SourceRecord。"""

    source = "leju"

    def parse(self, html: str, url: str = "") -> SourceRecord:
        """解析樂居社區頁 HTML。

        Args:
            html: 頁面 HTML。
            url: 原始網址。

        Returns:
            填妥標準欄位的 :class:`SourceRecord`。
        """
        soup = BeautifulSoup(html, "lxml")
        raw = self._extract_pairs(soup)

        fields: dict[str, object] = {}
        for label, value in raw.items():
            key = _LABEL_MAP.get(label)
            if key in _COMPARED_KEYS and value:
                fields.setdefault(key, value)

        fields["name"] = self._extract_name(soup)
        logger.info("解析樂居完成：%s（%d 個欄位）", fields.get("name"), len(fields))
        return SourceRecord(source=self.source, url=url, fields=fields, raw=raw)

    @staticmethod
    def _extract_pairs(soup: BeautifulSoup) -> dict[str, str]:
        """抽取所有 ``dt`` 標籤 → ``dd`` 值（標籤去除冒號與空白）。"""
        pairs: dict[str, str] = {}
        for dt in soup.find_all("dt"):
            label = re.sub(r"[：:\s]", "", dt.get_text())
            dd = dt.find_next_sibling("dd")
            value = clean_text(dd.get_text(" ", strip=True)) if dd else ""
            if label and value:
                pairs.setdefault(label, value)
        return pairs

    @staticmethod
    def _extract_name(soup: BeautifulSoup) -> str:
        """由 <title> 取得社區名稱（取【】內或破折號前的部分）。"""
        title = clean_text(soup.title.get_text() if soup.title else "")
        inner = re.search(r"【(.+?)】", title)
        if inner:
            return inner.group(1)
        return re.split(r"[-－｜|]", title)[0].strip()
