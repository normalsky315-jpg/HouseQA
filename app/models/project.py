"""HouseQA 來源資料模型（來自 NKUinfos 的 data.json）。

這是「正確答案」的一方。欄位刻意保留 data.json 的原始命名與型別，
解析衍生欄位（公設比、建蔽率、基地面積、棟數、車位）的工作交由
:mod:`app.compare.fields` 處理，使本模型維持單純的資料容器。
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class Project(BaseModel):
    """單一建案在 NKUinfos 的資料。

    僅納入 QA 比對需要用到的欄位，其餘 data.json 欄位以 ``extra`` 保留，
    未來新增比對欄位時不需修改本類別。
    """

    name: str = ""
    dev: str = ""
    status: str = ""
    addr: str = ""
    permit: str = ""
    floor: str = ""
    count: int | None = None
    units: int | None = None
    layout: str = ""
    loan: str = ""
    handover: str = ""
    kit: list[str] = Field(default_factory=list)
    bath: list[str] = Field(default_factory=list)
    other: list[str] = Field(default_factory=list)
    amenities: dict[str, list[str]] = Field(default_factory=dict)
    notes: str = ""
    lat: float | None = None
    lng: float | None = None
    s591: str = ""

    # 保留尚未明確建模的欄位，維持向後相容與可擴充性。
    extra: dict[str, Any] = Field(default_factory=dict)

    @property
    def project_id(self) -> str:
        """從 s591 網址擷取建案編號，無法擷取時回退為名稱。

        Returns:
            建案編號字串，例如 ``"139790"``；若 s591 不含編號則回傳名稱。
        """
        for part in self.s591.rstrip("/").split("/"):
            if part.isdigit():
                return part
        return self.name

    @property
    def has_source(self) -> bool:
        """是否具備可抓取的 591 網址。"""
        return bool(self.s591.strip())
