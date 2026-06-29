"""樓層正規化。

把不同寫法的樓層描述統一成 ``{地上}F/B{地下}`` 標準格式：
    ``20F/B3``            -> ``20F/B3``
    ``地上20層，地下3層``  -> ``20F/B3``
無法解析（如 ``多期多棟``）時，回傳清理後的原字串以利人工檢視。
"""

from __future__ import annotations

import re

from app.normalize.text import clean_text

_ABOVE_RE = re.compile(r"地上\s*(\d+)|(\d+)\s*F|(\d+)\s*(?=/\s*B)", re.IGNORECASE)
_BELOW_RE = re.compile(r"地下\s*(\d+)|B\s*(\d+)", re.IGNORECASE)


class FloorNormalizer:
    """樓層字串正規化器。"""

    def normalize(self, value: str | None) -> str:
        """正規化樓層描述。

        Args:
            value: 原始樓層字串。

        Returns:
            ``"<地上>F/B<地下>"`` 格式；無法解析時回傳清理後原字串。
        """
        text = clean_text(value)
        if not text:
            return ""
        # 多期多棟等非單一樓層描述視為無法比對（後續判為 WARNING）。
        if any(token in text for token in ("多期", "各期", "多棟")):
            return ""

        above_match = _ABOVE_RE.search(text)
        below_match = _BELOW_RE.search(text)
        if not above_match:
            return text

        above = above_match.group(1) or above_match.group(2) or above_match.group(3)
        result = f"{above}F"
        if below_match:
            below = below_match.group(1) or below_match.group(2)
            result += f"/B{below}"
        return result
