"""比對規則單元測試。"""

from __future__ import annotations

from app.compare.rules import RuleFactory
from app.models.diff_result import Status


def test_exact_rule() -> None:
    rule = RuleFactory.create({"type": "exact"})
    assert rule.evaluate("中德建設", "中德建設")[0] is Status.PASS
    assert rule.evaluate("A", "B")[0] is Status.FAIL


def test_contains_rule() -> None:
    rule = RuleFactory.create({"type": "contains"})
    assert rule.evaluate("中德建設", "中德建設股份有限公司")[0] is Status.PASS
    assert rule.evaluate("xyz", "abc")[0] is Status.FAIL


def test_tolerance_rule_bands() -> None:
    rule = RuleFactory.create({"type": "tolerance", "tolerance": 0.05})
    assert rule.evaluate(1000, 1000)[0] is Status.PASS
    assert rule.evaluate(1000, 1040)[0] is Status.PASS      # 4% 內
    assert rule.evaluate(1000, 1080)[0] is Status.WARNING   # 8%，2 倍容忍內
    assert rule.evaluate(1000, 1300)[0] is Status.FAIL      # 30%


def test_contains_all_rule() -> None:
    rule = RuleFactory.create({"type": "contains_all"})
    materials = "櫻花廚具；衛浴：TOTO、Hansgrohe、Panasonic"
    assert rule.evaluate(["TOTO衛浴", "Hansgrohe龍頭"], materials)[0] is Status.PASS
    assert rule.evaluate(["TOTO", "不存在品牌"], materials)[0] is Status.WARNING
    assert rule.evaluate(["不存在A", "不存在B"], materials)[0] is Status.FAIL


def test_missing_values_warn() -> None:
    rule = RuleFactory.create({"type": "exact"})
    assert rule.evaluate("有值", None)[0] is Status.WARNING
    assert rule.evaluate(None, "有值")[0] is Status.WARNING
