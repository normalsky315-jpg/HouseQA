"""文字正規化基礎工具。

提供全形轉半形、空白壓縮、數值擷取等共用函式，供其他正規化器使用。
"""

from __future__ import annotations

import re
import unicodedata

_WHITESPACE_RE = re.compile(r"\s+")
_NUMBER_RE = re.compile(r"-?\d+(?:\.\d+)?")


def clean_text(value: str | None) -> str:
    """基礎文字清理：去除前後空白、壓縮連續空白、全形轉半形。

    Args:
        value: 原始字串，``None`` 視為空字串。

    Returns:
        清理後的字串。
    """
    if not value:
        return ""
    text = unicodedata.normalize("NFKC", str(value))
    text = text.replace("​", "").replace("\xa0", " ")
    return _WHITESPACE_RE.sub(" ", text).strip()


def collapse(value: str | None) -> str:
    """完全移除所有空白字元，便於比較含空白差異的字串。"""
    return _WHITESPACE_RE.sub("", clean_text(value))


def extract_number(value: str | int | float | None) -> float | None:
    """擷取字串中的第一個數值。

    Args:
        value: 來源值，可為字串或數字。

    Returns:
        擷取到的浮點數；找不到時回傳 ``None``。
    """
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    match = _NUMBER_RE.search(str(value))
    return float(match.group()) if match else None


def sum_numbers(value: str | int | float | None) -> float | None:
    """加總字串中所有數值（用於車位等「平面X+機械Y」格式）。

    Args:
        value: 來源值。

    Returns:
        所有數值的總和；無數值時回傳 ``None``。
    """
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    numbers = [float(m) for m in _NUMBER_RE.findall(str(value))]
    return sum(numbers) if numbers else None
