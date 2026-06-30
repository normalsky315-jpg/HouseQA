"""以 Anthropic Claude 進行差異分析。

當欄位比對為 FAIL 時，把「HouseQA 值 vs 各來源值」交給 Claude，請它判斷最可能
的差異原因（來源過期、NKUinfos 需更新、格式差異、同義詞、多期案……）並給建議。

需設定環境變數 ``ANTHROPIC_API_KEY``。未安裝 SDK 或未設金鑰時會優雅略過。
"""

from __future__ import annotations

import os
from typing import Any

from app.ai.base import Analyzer
from app.config import AiConfig
from app.models.diff_result import ProjectResult, Status
from app.utils.logger import get_logger

logger = get_logger(__name__)

_SYSTEM = (
    "你是台灣房地產資料品質分析師。使用者維護一套建案資料庫（NKUinfos），"
    "並與多個外部來源（591、house958、樂居）逐欄比對。以下提供某建案『不一致』"
    "的欄位與各來源的值。請針對每個欄位用一句話判斷最可能原因，並從下列類別"
    "擇一標註：[來源過期]、[NKUinfos需更新]、[格式差異_實為相同]、[同義詞]、"
    "[多期或多棟]、[無法判定]。最後加一行總結建議。"
    "請用繁體中文、條列、精簡，直接給結論，不要客套或重述題目。"
)


class AnthropicAnalyzer(Analyzer):
    """使用 Claude 分析比對差異。"""

    def __init__(self, config: AiConfig) -> None:
        self._config = config
        self._client: Any = None

    def available(self) -> bool:
        """是否已設定 API key 且可匯入 SDK。"""
        if not os.environ.get("ANTHROPIC_API_KEY"):
            return False
        try:
            import anthropic  # noqa: F401
        except ImportError:
            return False
        return True

    def _client_instance(self) -> Any:
        if self._client is None:
            import anthropic

            self._client = anthropic.Anthropic()
        return self._client

    def analyze(self, result: ProjectResult) -> str:
        """分析單一建案的 FAIL 欄位，回傳 Claude 的判斷。"""
        prompt = self._build_prompt(result)
        if not prompt:
            return ""
        try:
            client = self._client_instance()
            response = client.messages.create(
                model=self._config.model,
                max_tokens=self._config.max_output_tokens,
                thinking={"type": "adaptive"},
                system=_SYSTEM,
                messages=[{"role": "user", "content": prompt}],
            )
            text = "".join(
                block.text for block in response.content if block.type == "text"
            ).strip()
            logger.info("AI 分析完成：%s", result.name)
            return text
        except Exception as exc:  # noqa: BLE001 - AI 失敗不應中斷流程
            logger.warning("AI 分析失敗：%s - %s", result.name, exc)
            return f"（AI 分析失敗：{exc}）"

    @staticmethod
    def _build_prompt(result: ProjectResult) -> str:
        """由 FAIL 欄位組出提示字串；無 FAIL 欄位時回傳空字串。"""
        lines: list[str] = []
        for field in result.fields:
            if field.status is not Status.FAIL:
                continue
            sources = "；".join(
                f"{comp.source}={comp.value}"
                for comp in field.comparisons
                if comp.value not in (None, "")
            )
            lines.append(f"- {field.label}：NKUinfos={field.house_value}；{sources}")
        if not lines:
            return ""
        return f"建案：{result.name}\n不一致欄位：\n" + "\n".join(lines)
