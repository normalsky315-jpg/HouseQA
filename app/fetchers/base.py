"""Fetcher 外掛介面。

每個資料來源（591、樂居、建商官網……）實作一個 Fetcher 子類別，
負責「把某個 URL 變成 HTML 字串」。上層只透過此抽象與 :class:`FetcherRegistry`
互動，不直接依賴任何特定來源實作。
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class Fetcher(ABC):
    """資料抓取器抽象基底。"""

    #: 來源識別字串，例如 ``"591"``。
    source: str = "base"

    @abstractmethod
    def can_handle(self, url: str) -> bool:
        """是否能處理指定 URL。

        Args:
            url: 目標網址。

        Returns:
            可處理回傳 ``True``。
        """
        raise NotImplementedError

    @abstractmethod
    def fetch(self, url: str, force_download: bool = False) -> str:
        """抓取指定 URL 的 HTML。

        Args:
            url: 目標網址。
            force_download: 為 ``True`` 時略過快取重新下載。

        Returns:
            HTML 原始字串。

        Raises:
            RuntimeError: 重試後仍無法取得內容。
        """
        raise NotImplementedError
