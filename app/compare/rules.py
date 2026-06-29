"""可設定的比對規則。

規則由 :class:`RuleFactory` 依 config.yaml 的設定動態建立，因此比對門檻
（誤差容忍度、比對方式）完全不寫死在程式中。新增規則型別只需新增一個
:class:`Rule` 子類別並在工廠註冊，符合開放／封閉原則。

每個規則的 :meth:`Rule.evaluate` 接受「預期值」（HouseQA / data.json）與
「實際值」（外部來源），回傳 ``(Status, message)``。
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any

from app.models.diff_result import Status
from app.normalize.brand import BrandNormalizer
from app.normalize.text import clean_text, collapse, extract_number

Normalizer = Callable[[Any], Any]

_brand = BrandNormalizer()


_PLACEHOLDER_RE = re.compile(r"待定|待補|暫無|價格待定|資訊待補|未公布|待確認")


def _placeholder_stripped(text: str) -> str:
    """移除佔位字後剩下的有效內容（用來判斷來源是否其實「未公布」）。"""
    return _PLACEHOLDER_RE.sub("", clean_text(text)).strip()


def _is_empty(value: Any) -> bool:
    """判斷值是否視為「未提供」。"""
    if value is None:
        return True
    if isinstance(value, str):
        return clean_text(value) == ""
    if isinstance(value, (list, tuple, dict)):
        return len(value) == 0
    return False


class Rule(ABC):
    """比對規則基底類別。"""

    def __init__(self, **options: Any) -> None:
        self.options = options

    def evaluate(
        self,
        expected: Any,
        actual: Any,
        normalizer: Normalizer | None = None,
    ) -> tuple[Status, str]:
        """比對兩值並回傳狀態與訊息。

        會先處理「任一方缺值」的共同情況（回傳 WARNING），再交由
        子類別的 :meth:`_compare` 處理實際比對。
        """
        if _is_empty(expected) and _is_empty(actual):
            return Status.WARNING, "雙方皆無資料"
        if _is_empty(actual):
            return Status.WARNING, "來源未提供此欄位"
        if _is_empty(expected):
            return Status.WARNING, "HouseQA 未提供此欄位"
        return self._compare(expected, actual, normalizer)

    @abstractmethod
    def _compare(
        self, expected: Any, actual: Any, normalizer: Normalizer | None
    ) -> tuple[Status, str]:
        """子類別實作的核心比對邏輯（兩值均已確認非空）。"""
        raise NotImplementedError


def _normalized_empty(*values: Any) -> bool:
    """判斷正規化後是否有任一方變成空字串（代表佔位字、無法比對）。"""
    return any(v is None or str(v).strip() == "" for v in values)


class ExactRule(Rule):
    """完全一致規則：正規化後相等才 PASS。"""

    def _compare(self, expected: Any, actual: Any, normalizer):
        norm = normalizer or collapse
        exp, act = norm(expected), norm(actual)
        if _normalized_empty(exp, act):
            return Status.WARNING, "正規化後無可比對內容（可能為佔位字）"
        if exp == act:
            return Status.PASS, "完全一致"
        return Status.FAIL, f"不一致：HouseQA「{expected}」≠ 來源「{actual}」"


class ContainsRule(Rule):
    """包含規則：來源（正規化後）包含預期字串即 PASS。"""

    def _compare(self, expected: Any, actual: Any, normalizer):
        norm = normalizer or collapse
        exp, act = norm(expected), norm(actual)
        if _normalized_empty(exp, act):
            return Status.WARNING, "正規化後無可比對內容（可能為佔位字）"
        if exp and exp in act:
            return Status.PASS, "來源包含預期內容"
        if act and act in exp:
            return Status.WARNING, "預期內容包含來源（來源較簡略）"
        return Status.FAIL, f"來源未包含：「{expected}」"


class ContainsAllRule(Rule):
    """清單包含規則：預期清單每一項都被來源包含才 PASS。

    使用品牌正規化判斷包含關係，故 ``TOTO衛浴`` 可命中來源中的 ``TOTO``。
    全部命中 PASS；部分命中 WARNING；完全未命中 FAIL。
    """

    def _compare(self, expected: Any, actual: Any, normalizer):
        items = expected if isinstance(expected, (list, tuple)) else [expected]
        haystack = actual if isinstance(actual, str) else " ".join(map(str, actual))
        items = [str(i) for i in items if not _is_empty(i)]
        if not items:
            return Status.WARNING, "無可比對項目"
        if not _placeholder_stripped(haystack):
            return Status.WARNING, "來源資料未公布（如「待定」）"

        hits = [it for it in items if _brand.contains_brand(haystack, it)]
        missing = [it for it in items if it not in hits]
        if not missing:
            return Status.PASS, "所有項目皆命中"
        if hits:
            return Status.WARNING, f"部分未命中：{', '.join(missing)}"
        return Status.FAIL, f"皆未命中：{', '.join(missing)}"


class ContainsAnyRule(Rule):
    """寬鬆清單規則（資訊性欄位用）：只要任一項命中即 PASS，全部未命中為
    WARNING，永不 FAIL。適合「建材其他項」這類本就零散、非權威的欄位。
    """

    def _compare(self, expected: Any, actual: Any, normalizer):
        items = expected if isinstance(expected, (list, tuple)) else [expected]
        haystack = actual if isinstance(actual, str) else " ".join(map(str, actual))
        items = [str(i) for i in items if not _is_empty(i)]
        if not items:
            return Status.WARNING, "無可比對項目"
        hits = [it for it in items if _brand.contains_brand(haystack, it)]
        if hits:
            return Status.PASS, f"命中 {len(hits)}/{len(items)} 項"
        return Status.WARNING, "來源未提及這些項目（僅供參考）"


class ToleranceRule(Rule):
    """數值誤差規則。

    ``|expected - actual| / |expected| <= tolerance`` → PASS；
    在 2 倍容忍度內 → WARNING；否則 FAIL。``tolerance = 0`` 等同數值相等。
    """

    def _compare(self, expected: Any, actual: Any, normalizer):
        tol = float(self.options.get("tolerance", 0.0))
        exp = normalizer(expected) if normalizer else extract_number(expected)
        act = normalizer(actual) if normalizer else extract_number(actual)
        exp = extract_number(exp) if not isinstance(exp, (int, float)) else exp
        act = extract_number(act) if not isinstance(act, (int, float)) else act
        if exp is None or act is None:
            return Status.WARNING, "無法解析為數值"

        if exp == 0:
            diff = 0.0 if act == 0 else 1.0
        else:
            diff = abs(exp - act) / abs(exp)

        if diff <= tol:
            return Status.PASS, f"數值相符（{exp} vs {act}）"
        if diff <= tol * 2 or (tol == 0 and diff <= 0.02):
            return Status.WARNING, f"數值略有差異（{exp} vs {act}，差 {diff:.1%}）"
        return Status.FAIL, f"數值差異過大（{exp} vs {act}，差 {diff:.1%}）"


class RuleFactory:
    """依設定建立規則實例。"""

    _REGISTRY: dict[str, type[Rule]] = {
        "exact": ExactRule,
        "contains": ContainsRule,
        "contains_all": ContainsAllRule,
        "contains_any": ContainsAnyRule,
        "tolerance": ToleranceRule,
    }

    @classmethod
    def create(cls, spec: dict[str, Any]) -> Rule:
        """依規則設定建立 :class:`Rule`。

        Args:
            spec: 形如 ``{"type": "tolerance", "tolerance": 0.05}`` 的設定。

        Returns:
            對應的規則實例；未知型別退回 :class:`ExactRule`。
        """
        spec = dict(spec or {})
        rule_type = spec.pop("type", "exact")
        rule_cls = cls._REGISTRY.get(rule_type, ExactRule)
        return rule_cls(**spec)

    @classmethod
    def register(cls, name: str, rule_cls: type[Rule]) -> None:
        """註冊自訂規則型別，供未來擴充。"""
        cls._REGISTRY[name] = rule_cls
