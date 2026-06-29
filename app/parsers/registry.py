"""Parser 註冊表。

依來源名稱挑選對應 Parser。新增來源只需 :meth:`register` 一個新 Parser。
"""

from __future__ import annotations

from app.parsers.base import Parser
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ParserRegistry:
    """管理並挑選 Parser 的註冊表。"""

    def __init__(self) -> None:
        self._parsers: dict[str, Parser] = {}

    def register(self, parser: Parser) -> None:
        """以來源名稱註冊 Parser。"""
        self._parsers[parser.source] = parser
        logger.debug("註冊 Parser：%s", parser.source)

    def get(self, source: str) -> Parser | None:
        """依來源名稱取得 Parser。"""
        return self._parsers.get(source)
