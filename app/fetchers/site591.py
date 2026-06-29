"""591 新建案抓取器（使用 Playwright）。

591 為 Nuxt 動態網站，須以瀏覽器渲染後才能取得完整 HTML，故採用 Playwright
而非單純 requests。具備快取、逾時、失敗自動重試等能力。
"""

from __future__ import annotations

import time

from app.config import FetchConfig
from app.fetchers.base import Fetcher
from app.fetchers.cache import HtmlCache
from app.utils.logger import get_logger

logger = get_logger(__name__)


class Site591Fetcher(Fetcher):
    """以 Playwright 抓取 591 新建案／物件詳情頁。"""

    source = "591"

    def __init__(self, config: FetchConfig, cache: HtmlCache) -> None:
        """建立 591 抓取器。

        Args:
            config: 抓取設定（無頭模式、逾時、重試次數等）。
            cache: HTML 快取實例。
        """
        self._config = config
        self._cache = cache

    def can_handle(self, url: str) -> bool:
        """判斷是否為 591 網址。"""
        return "591.com.tw" in url

    def fetch(self, url: str, force_download: bool = False) -> str:
        """抓取 591 頁面 HTML，必要時自動重試。

        Args:
            url: 591 詳情頁網址。
            force_download: 為 ``True`` 時忽略快取重新下載。

        Returns:
            渲染後的 HTML 字串。

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
                logger.info("下載 591（第 %d/%d 次）：%s", attempt, self._config.retry, url)
                html = self._download(url)
                self._cache.set(url, html)
                return html
            except Exception as exc:  # noqa: BLE001 - 統一轉為重試
                last_error = exc
                wait = self._config.retry_backoff * attempt
                logger.warning("下載失敗：%s（%s），%.1f 秒後重試", url, exc, wait)
                if attempt < self._config.retry:
                    time.sleep(wait)

        raise RuntimeError(f"591 下載失敗（已重試 {self._config.retry} 次）：{last_error}")

    def _download(self, url: str) -> str:
        """實際以 Playwright 取得頁面內容（單次嘗試）。"""
        # 延遲匯入：未安裝 Playwright 時仍可使用 --cache-only 流程。
        from playwright.sync_api import sync_playwright

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=self._config.headless)
            try:
                page = browser.new_page()
                page.goto(
                    url,
                    wait_until=self._config.wait_until,
                    timeout=self._config.timeout * 1000,
                )
                return page.content()
            finally:
                browser.close()
