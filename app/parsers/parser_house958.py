"""house958.com 建案頁解析器。

house958 的建案頁以「◎標籤 : 值」逐行陳列基本資料，解析以標籤文字為錨點，
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

# house958 標籤 → HouseQA 標準欄位 key。
_LABEL_MAP: dict[str, str] = {
    "個案名稱": "name",
    "基地位置": "addr",
    "基地面積": "base_area",
    "樓層規劃": "floor",
    "推出住家": "units",
    "投資興建": "dev",
    "公設比例": "public_ratio",
    "住家規劃": "layout",
    # 以下保留於 raw，目前不參與比對：
    "地段地號": "land_no",
    "都計分區": "zoning",
    "公開日期": "open_date",
    "管理費用": "mgmt_fee",
    "總銷金額": "total_sales",
    "推出店面": "shops",
}
_COMPARED_KEYS = {
    "name", "addr", "base_area", "floor", "units", "dev", "public_ratio", "layout",
}


class ParserHouse958(Parser):
    """house958 建案頁 → SourceRecord。"""

    source = "house958"

    def parse(self, html: str, url: str = "") -> SourceRecord:
        """解析 house958 建案頁 HTML。

        Args:
            html: 頁面 HTML。
            url: 原始網址。

        Returns:
            填妥標準欄位的 :class:`SourceRecord`。
        """
        soup = BeautifulSoup(html, "lxml")
        text = soup.get_text("\n", strip=True)

        raw: dict[str, str] = {}
        for chunk in text.split("◎")[1:]:
            line = chunk.split("\n", 1)[0]
            match = re.match(r"\s*(.+?)\s*[:：]\s*(.*)", line)
            if not match:
                continue
            label = clean_text(match.group(1))
            value = clean_text(match.group(2))
            if label and value:
                raw.setdefault(label, value)

        fields: dict[str, object] = {}
        for label, value in raw.items():
            key = _LABEL_MAP.get(label)
            if key in _COMPARED_KEYS:
                fields[key] = value

        if "name" not in fields:
            fields["name"] = self._title_name(soup)

        logger.info(
            "解析 house958 完成：%s（%d 個欄位）", fields.get("name"), len(fields)
        )
        return SourceRecord(source=self.source, url=url, fields=fields, raw=raw)

    @staticmethod
    def _title_name(soup: BeautifulSoup) -> str:
        """退而求其次：由 <title> 取得名稱（去除建商前綴與括號）。"""
        title = clean_text(soup.title.get_text() if soup.title else "")
        inner = re.search(r"【(.+?)】", title)
        return inner.group(1) if inner else title
