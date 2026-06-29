"""面積／數值正規化。

把含單位的字串（``1253.51坪``、``基地1253.51坪``）轉成純數值，
供 tolerance 規則進行誤差比對。
"""

from __future__ import annotations

from app.normalize.text import extract_number


class AreaNormalizer:
    """面積字串正規化器，輸出浮點數（單位：坪）。"""

    def normalize(self, value: str | int | float | None) -> float | None:
        """擷取面積數值。

        Args:
            value: 原始值，例如 ``"基地1253.51坪"`` 或 ``1253.51``。

        Returns:
            浮點數面積；無法解析時回傳 ``None``。
        """
        return extract_number(value)
