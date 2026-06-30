"""AI 差異分析器的共同介面。

把「分析比對差異」抽象成 :class:`Analyzer`，讓未來可替換不同的 AI 後端
（Anthropic、OpenAI……）或停用 AI，而不影響流程其餘部分。
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.models.diff_result import ProjectResult


class Analyzer(ABC):
    """差異分析器抽象基底。"""

    @abstractmethod
    def available(self) -> bool:
        """是否具備執行條件（例如已設定 API key）。"""
        raise NotImplementedError

    @abstractmethod
    def analyze(self, result: ProjectResult) -> str:
        """分析單一建案的比對結果，回傳人類可讀的分析文字。

        Args:
            result: 已完成比對的 :class:`ProjectResult`。

        Returns:
            分析文字（繁體中文）；無可分析內容時回傳空字串。
        """
        raise NotImplementedError
