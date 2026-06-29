"""比對結果模型（支援多來源）。

一個欄位可同時與多個外部來源（591、house958、樂居……）比對：
:class:`SourceComparison` 是「單一來源對某欄位的看法」，:class:`FieldResult`
彙總同一欄位所有來源的看法並計算整體狀態，:class:`ProjectResult` 與
:class:`QAReport` 組成整份報告。
"""

from __future__ import annotations

import enum
from typing import Any

from pydantic import BaseModel, Field


class Status(str, enum.Enum):
    """比對狀態。"""

    PASS = "PASS"
    WARNING = "WARNING"
    FAIL = "FAIL"

    @property
    def color(self) -> str:
        """對應的報表顏色（HTML / Excel 共用）。"""
        return {
            Status.PASS: "#2e7d32",
            Status.WARNING: "#f9a825",
            Status.FAIL: "#c62828",
        }[self]


class SourceComparison(BaseModel):
    """單一來源對某欄位的比對結果。"""

    source: str
    value: Any = None
    status: Status
    message: str = ""


class FieldResult(BaseModel):
    """單一欄位彙總所有來源後的比對結果。"""

    key: str
    label: str
    house_value: Any = None
    comparisons: list[SourceComparison] = Field(default_factory=list)
    status: Status

    @staticmethod
    def aggregate(comparisons: list[SourceComparison]) -> Status:
        """由各來源狀態決定欄位整體狀態。

        規則（體現「多來源佐證」精神）：
            - 只要**任一**來源 PASS → 整體 PASS（你的資料有來源背書）。
            - 沒有 PASS，但有來源 FAIL（明確不符）→ 整體 FAIL。
            - 其餘（皆無法確定）→ WARNING。
        """
        statuses = {c.status for c in comparisons}
        if Status.PASS in statuses:
            return Status.PASS
        if Status.FAIL in statuses:
            return Status.FAIL
        return Status.WARNING

    def source_value(self, source: str) -> Any:
        """取得指定來源在此欄位的值（找不到回傳 ``None``）。"""
        for comp in self.comparisons:
            if comp.source == source:
                return comp.value
        return None

    def source_status(self, source: str) -> Status | None:
        """取得指定來源在此欄位的狀態（找不到回傳 ``None``）。"""
        for comp in self.comparisons:
            if comp.source == source:
                return comp.status
        return None


class ProjectResult(BaseModel):
    """單一建案的完整比對結果。"""

    project_id: str
    name: str
    source_urls: dict[str, str] = Field(default_factory=dict)
    sources: list[str] = Field(default_factory=list)
    skipped: bool = False
    skip_reason: str = ""
    error: str = ""
    fields: list[FieldResult] = Field(default_factory=list)
    ai_analysis: str = ""

    @property
    def status(self) -> Status:
        """建案整體狀態：任一 FAIL 即 FAIL，否則任一 WARNING 即 WARNING。"""
        if self.error or self.skipped:
            return Status.WARNING
        statuses = {f.status for f in self.fields}
        if Status.FAIL in statuses:
            return Status.FAIL
        if Status.WARNING in statuses:
            return Status.WARNING
        return Status.PASS if self.fields else Status.WARNING

    def count(self, status: Status) -> int:
        """統計指定狀態的欄位數量。"""
        return sum(1 for f in self.fields if f.status is status)


class QAReport(BaseModel):
    """整份 QA 報告。"""

    projects: list[ProjectResult] = Field(default_factory=list)
    generated_at: str = ""

    @property
    def total(self) -> int:
        """建案總數。"""
        return len(self.projects)

    def count_status(self, status: Status) -> int:
        """統計整體為指定狀態的建案數。"""
        return sum(1 for p in self.projects if p.status is status)

    def used_sources(self) -> list[str]:
        """整份報告實際出現過的來源名稱（依出現順序）。"""
        seen: list[str] = []
        for project in self.projects:
            for source in project.sources:
                if source not in seen:
                    seen.append(source)
        return seen

    def summary(self) -> dict[str, int]:
        """產生摘要統計字典。"""
        return {
            "total": self.total,
            "pass": self.count_status(Status.PASS),
            "warning": self.count_status(Status.WARNING),
            "fail": self.count_status(Status.FAIL),
        }
