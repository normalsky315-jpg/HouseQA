"""house958.com（2026高雄推案分析）抓取器。

house958 為純靜態 HTML，使用 ``requests`` 即可（不需 Playwright）。
具備快取、逾時與失敗重試。
"""

from __future__ import annotations

import time

from app.config import FetchConfig
from app.fetchers.base import Fetcher
from app.fetchers.cache import HtmlCache
from app.utils.logger import get_logger

logger = get_logger(__name__)

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/137.0 Safari/537.36"
)


class House958Fetcher(Fetcher):
    """以 requests 抓取 house958.com 頁面。"""

    source = "house958"

    def __init__(self, config: FetchConfig, cache: HtmlCache) -> None:
        self._config = config
        self._cache = cache

    def can_handle(self, url: str) -> bool:
        """判斷是否為 house958 網址。"""
        return "house958.com" in url

    def fetch(self, url: str, force_download: bool = False) -> str:
        """抓取 house958 頁面 HTML，必要時自動重試。

        Args:
            url: 目標網址。
            force_download: 為 ``True`` 時忽略快取重新下載。

        Returns:
            頁面 HTML（已處理編碼）。

        Raises:
            RuntimeError: 重試耗盡後仍失敗。
        """
        if not force_download:
            cached = self._cache.get(url)
            if cached is not None:
                return cached

        last_error: Exception | None = None
        for attempt in range(1, self._config.retry + 1):
            try:
                logger.info(
                    "下載 house958（第 %d/%d 次）：%s",
                    attempt, self._config.retry, url,
                )
                html = self._download(url)
                self._cache.set(url, html)
                return html
            except Exception as exc:  # noqa: BLE001 - 統一轉為重試
                last_error = exc
                wait = self._config.retry_backoff * attempt
                logger.warning("下載失敗：%s（%s），%.1f 秒後重試", url, exc, wait)
                if attempt < self._config.retry:
                    time.sleep(wait)

        raise RuntimeError(
            f"house958 下載失敗（已重試 {self._config.retry} 次）：{last_error}"
        )

    def _download(self, url: str) -> str:
        """單次以 requests 取得頁面內容（自動偵測編碼）。"""
        import requests

        response = requests.get(
            url, headers={"User-Agent": _USER_AGENT}, timeout=self._config.timeout
        )
        response.raise_for_status()
        response.encoding = response.apparent_encoding or response.encoding or "utf-8"
        return response.text
