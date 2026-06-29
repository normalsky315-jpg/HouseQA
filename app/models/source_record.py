"""外部資料來源的中立資料模型。

:class:`SourceRecord` 是所有 Parser 的共同輸出格式，刻意與任何特定網站
（591、樂居、建商官網……）解耦。Compare Engine 只認得本模型，因此未來
新增資料來源時，只要新增對應的 Fetcher + Parser 產出 SourceRecord，
完全不需修改比對引擎。
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class SourceRecord(BaseModel):
    """經 Parser 解析後的單一建案外部資料。

    Attributes:
        source: 來源識別字串，例如 ``"591"``、``"leju"``。
        url: 原始頁面網址。
        fields: 已正規化為 HouseQA 標準欄位 key 的資料。值可能為
            ``str``、``int``、``float``、``list`` 或 ``None``。
        raw: Parser 抽取到的原始「標籤→文字」對照，保留供除錯與
            未來擴充使用，不參與比對。
    """

    source: str
    url: str = ""
    fields: dict[str, Any] = Field(default_factory=dict)
    raw: dict[str, str] = Field(default_factory=dict)

    def get(self, key: str, default: Any = None) -> Any:
        """讀取標準欄位值。

        Args:
            key: 標準欄位 key（見 :mod:`app.compare.fields`）。
            default: 找不到時回傳的預設值。

        Returns:
            欄位值或預設值。
        """
        return self.fields.get(key, default)
