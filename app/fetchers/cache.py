"""HTML 快取。

所有抓取到的 HTML 依「URL 的 MD5 雜湊」存放於快取資料夾，預設 7 天有效，
逾期自動視為失效。支援強制重抓與清除全部快取。
"""

from __future__ import annotations

import hashlib
import time
from pathlib import Path

from app.utils.logger import get_logger

logger = get_logger(__name__)


class HtmlCache:
    """以檔案系統實作的 HTML 快取。"""

    def __init__(self, cache_dir: str | Path = "cache", days: int = 7) -> None:
        """建立快取。

        Args:
            cache_dir: 快取資料夾路徑。
            days: 快取有效天數。
        """
        self.dir = Path(cache_dir)
        self.ttl_seconds = max(days, 0) * 86400
        self.dir.mkdir(parents=True, exist_ok=True)

    def path_for(self, url: str) -> Path:
        """取得指定 URL 對應的快取檔路徑。"""
        digest = hashlib.md5(url.encode("utf-8")).hexdigest()
        return self.dir / f"{digest}.html"

    def is_valid(self, url: str) -> bool:
        """判斷指定 URL 是否有「未逾期」的快取。"""
        path = self.path_for(url)
        if not path.exists():
            return False
        if self.ttl_seconds == 0:
            return True
        age = time.time() - path.stat().st_mtime
        return age <= self.ttl_seconds

    def get(self, url: str) -> str | None:
        """讀取有效快取內容；無效或不存在時回傳 ``None``。"""
        if not self.is_valid(url):
            return None
        try:
            content = self.path_for(url).read_text(encoding="utf-8")
            logger.info("命中快取：%s", url)
            return content
        except OSError as exc:  # pragma: no cover - 罕見 IO 錯誤
            logger.warning("讀取快取失敗：%s - %s", url, exc)
            return None

    def set(self, url: str, html: str) -> None:
        """寫入快取。"""
        try:
            self.path_for(url).write_text(html, encoding="utf-8")
            logger.info("寫入快取：%s", url)
        except OSError as exc:  # pragma: no cover - 罕見 IO 錯誤
            logger.warning("寫入快取失敗：%s - %s", url, exc)

    def clear(self) -> int:
        """清除所有 HTML 快取檔。

        Returns:
            刪除的檔案數量。
        """
        count = 0
        for file in self.dir.glob("*.html"):
            try:
                file.unlink()
                count += 1
            except OSError:  # pragma: no cover
                pass
        logger.info("已清除 %d 筆快取", count)
        return count
