"""Parser 外掛介面。

每個資料來源對應一個 Parser，負責把 HTML 轉成中立的 :class:`SourceRecord`。
Parser 與 Fetcher 分離：Fetcher 只管取得 HTML，Parser 只管解析，彼此可獨立
替換與測試。
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.models.source_record import SourceRecord


class Parser(ABC):
    """HTML → SourceRecord 的解析器抽象基底。"""

    #: 來源識別字串，需與對應 Fetcher 一致。
    source: str = "base"

    @abstractmethod
    def parse(self, html: str, url: str = "") -> SourceRecord:
        """解析 HTML 並回傳中立資料模型。

        Args:
            html: 來源頁面 HTML。
            url: 原始網址（寫入結果以利追蹤）。

        Returns:
            填妥標準欄位的 :class:`SourceRecord`。
        """
        raise NotImplementedError
