"""正規化器（Normalizer）的共同介面。

每個 Normalizer 負責把某類值（品牌、地址、面積、樓層……）轉成可比較的
標準形式。比對引擎透過此介面套用正規化，新增正規化器不需修改引擎。
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class Normalizer(Protocol):
    """正規化器協定。"""

    def normalize(self, value: Any) -> Any:
        """將輸入值轉為標準化形式。

        Args:
            value: 原始值。

        Returns:
            標準化後的值。
        """
        ...
