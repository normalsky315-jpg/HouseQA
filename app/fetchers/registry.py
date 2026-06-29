"""Fetcher 註冊表。

依 URL 自動挑選能處理的 Fetcher。新增來源只需 :meth:`register` 一個
新的 :class:`Fetcher`，呼叫端程式碼不需更動。
"""

from __future__ import annotations

from app.fetchers.base import Fetcher
from app.utils.logger import get_logger

logger = get_logger(__name__)


class FetcherRegistry:
    """管理並挑選 Fetcher 的註冊表。"""

    def __init__(self) -> None:
        self._fetchers: list[Fetcher] = []

    def register(self, fetcher: Fetcher) -> None:
        """註冊一個 Fetcher。"""
        self._fetchers.append(fetcher)
        logger.debug("註冊 Fetcher：%s", fetcher.source)

    def for_url(self, url: str) -> Fetcher | None:
        """取得能處理指定 URL 的第一個 Fetcher。

        Args:
            url: 目標網址。

        Returns:
            對應的 Fetcher；找不到時回傳 ``None``。
        """
        for fetcher in self._fetchers:
            if fetcher.can_handle(url):
                return fetcher
        return None
