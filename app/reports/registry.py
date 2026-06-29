"""Reporter 註冊表。"""

from __future__ import annotations

from app.reports.base import Reporter
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ReporterRegistry:
    """管理並挑選 Reporter 的註冊表。"""

    def __init__(self) -> None:
        self._reporters: dict[str, Reporter] = {}

    def register(self, reporter: Reporter) -> None:
        """以格式名稱註冊 Reporter。"""
        self._reporters[reporter.name] = reporter
        logger.debug("註冊 Reporter：%s", reporter.name)

    def get(self, name: str) -> Reporter | None:
        """依格式名稱取得 Reporter。"""
        return self._reporters.get(name)

    def names(self) -> list[str]:
        """已註冊的格式名稱清單。"""
        return list(self._reporters)
