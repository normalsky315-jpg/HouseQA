"""AI 差異分析器測試（以假的 client，不需 API key）。"""

from __future__ import annotations

from app.ai.anthropic_analyzer import AnthropicAnalyzer
from app.config import AiConfig
from app.models.diff_result import (
    FieldResult,
    ProjectResult,
    SourceComparison,
    Status,
)


def _result() -> ProjectResult:
    return ProjectResult(
        project_id="1",
        name="測試建案",
        sources=["591", "house958"],
        fields=[
            FieldResult(
                key="loan", label="貸款成數", house_value="80%", status=Status.FAIL,
                comparisons=[
                    SourceComparison(source="591", value="75%", status=Status.FAIL),
                    SourceComparison(source="house958", value=None, status=Status.WARNING),
                ],
            ),
            FieldResult(
                key="dev", label="建商", house_value="A建設", status=Status.PASS,
                comparisons=[SourceComparison(source="591", value="A建設", status=Status.PASS)],
            ),
        ],
    )


def test_prompt_includes_only_fail_fields() -> None:
    prompt = AnthropicAnalyzer._build_prompt(_result())
    assert "測試建案" in prompt
    assert "貸款成數" in prompt and "75%" in prompt
    assert "建商" not in prompt  # PASS 欄位不納入


def test_available_false_without_key(monkeypatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert AnthropicAnalyzer(AiConfig()).available() is False


def test_analyze_with_fake_client() -> None:
    class _Block:
        type = "text"
        text = "- 貸款成數：[來源過期] 591 較舊\n總結：更新 591 後再確認"

    class _Resp:
        content = [_Block()]

    class _Messages:
        def create(self, **kwargs):
            assert kwargs["model"] == "claude-opus-4-8"
            assert "測試建案" in kwargs["messages"][0]["content"]
            return _Resp()

    class _FakeClient:
        messages = _Messages()

    analyzer = AnthropicAnalyzer(AiConfig())
    analyzer._client = _FakeClient()  # 注入假 client，跳過真實 API
    out = analyzer.analyze(_result())
    assert "來源過期" in out


def test_analyze_returns_empty_when_no_fail() -> None:
    clean = ProjectResult(
        project_id="2", name="全過建案",
        fields=[FieldResult(key="dev", label="建商", house_value="A", status=Status.PASS,
                            comparisons=[SourceComparison(source="591", value="A", status=Status.PASS)])],
    )
    assert AnthropicAnalyzer(AiConfig())._build_prompt(clean) == ""
