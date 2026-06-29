"""地址正規化。

移除縣市區等行政區前綴與括號補充（地號等），讓 ``大學南路`` 與
``高雄市楠梓區大學南路（藍田西段12等地號）`` 正規化後一致。
"""

from __future__ import annotations

import re

from app.normalize.text import collapse

# 行政區層級用字，連同其前方名稱一併移除。
_ADMIN_RE = re.compile(r"^.*?[縣市]")
_DISTRICT_RE = re.compile(r"^.*?[區鄉鎮]")
# 括號補充（全形與半形）。
_PAREN_RE = re.compile(r"[（(].*?[）)]")


class AddressNormalizer:
    """地址字串正規化器。"""

    def normalize(self, value: str | None) -> str:
        """正規化地址字串。

        步驟：去除空白 → 去除括號補充 → 去除縣市與行政區前綴。

        Args:
            value: 原始地址。

        Returns:
            正規化後的路名／地址核心字串。
        """
        text = collapse(value)
        if not text:
            return ""
        text = _PAREN_RE.sub("", text)
        text = _ADMIN_RE.sub("", text, count=1)
        text = _DISTRICT_RE.sub("", text, count=1)
        # 移除「號」與「之N」，吸收 52~60號 與 52號~60號 之類的格式差異。
        text = text.replace("號", "")
        return text
