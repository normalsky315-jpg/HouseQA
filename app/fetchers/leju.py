"""樂居（leju.com.tw）抓取器。

樂居有 Cloudflare 防護且內容由 JS 動態渲染，需以 Playwright（真實瀏覽器）
載入並等待渲染完成。具備快取、逾時與失敗重試。
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
    "(KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36"
)
# Cloudflare 挑戰與前端渲染所需的額外等待（毫秒）。
_RENDER_WAIT_MS = 6000


class LejuFetcher(Fetcher):
    """以 Playwright 抓取樂居社區頁。"""

    source = "leju"

    def __init__(self, config: FetchConfig, cache: HtmlCache) -> None:
        self._config = config
        self._cache = cache

    def can_handle(self, url: str) -> bool:
        """判斷是否為樂居網址。"""
        return "leju.com.tw" in url

    def fetch(self, url: str, force_download: bool = False) -> str:
        """抓取樂居社區頁 HTML，必要時自動重試。

        Args:
            url: 樂居社區頁網址。
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
                logger.info("下載樂居（第 %d/%d 次）：%s", attempt, self._config.retry, url)
                html = self._download(url)
                if "Just a moment" in html or "cf-challenge" in html:
                    raise RuntimeError("Cloudflare 挑戰未通過")
                self._cache.set(url, html)
                return html
            except Exception as exc:  # noqa: BLE001 - 統一轉為重試
                last_error = exc
                wait = self._config.retry_backoff * attempt
                logger.warning("下載失敗：%s（%s），%.1f 秒後重試", url, exc, wait)
                if attempt < self._config.retry:
                    time.sleep(wait)

        raise RuntimeError(f"樂居下載失敗（已重試 {self._config.retry} 次）：{last_error}")

    def _download(self, url: str) -> str:
        """單次以 Playwright 取得頁面內容（含渲染等待）。"""
        from playwright.sync_api import sync_playwright

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=self._config.headless)
            try:
                page = browser.new_page(user_agent=_USER_AGENT)
                page.goto(
                    url, wait_until="domcontentloaded", timeout=self._config.timeout * 1000
                )
                page.wait_for_timeout(_RENDER_WAIT_MS)
                return page.content()
            finally:
                browser.close()
