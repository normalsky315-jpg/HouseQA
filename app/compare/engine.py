"""比對引擎（Compare Engine）。

引擎是整套系統的核心，且刻意與任何資料來源解耦：它只認得
:class:`Project`、:class:`SourceRecord`、:class:`FieldSpec` 與 :class:`Rule`。
支援同時與多個來源比對——逐欄對每個來源各評一次，再彙總為整體狀態。
新增來源時完全不需修改本檔案。
"""

from __future__ import annotations

from typing import Any

from app.compare.fields import FIELD_SPECS, FieldSpec
from app.compare.rules import Rule, RuleFactory
from app.config import CompareConfig
from app.models.diff_result import (
    FieldResult,
    ProjectResult,
    SourceComparison,
    Status,
)
from app.models.project import Project
from app.models.source_record import SourceRecord
from app.utils.logger import get_logger

logger = get_logger(__name__)


class CompareEngine:
    """依設定的規則，逐欄比對 HouseQA 與一個或多個外部來源。"""

    def __init__(
        self,
        compare_config: CompareConfig,
        field_specs: list[FieldSpec] | None = None,
    ) -> None:
        """建立比對引擎。

        Args:
            compare_config: 比對規則設定（來自 config.yaml）。
            field_specs: 欲比對的欄位清單，預設使用全域 :data:`FIELD_SPECS`。
        """
        self._specs = field_specs if field_specs is not None else FIELD_SPECS
        self._rules: dict[str, Rule] = self._build_rules(compare_config)

    def _build_rules(self, config: CompareConfig) -> dict[str, Rule]:
        """為每個欄位建立對應的規則實例。"""
        default_rule = RuleFactory.create(config.default)
        rules: dict[str, Rule] = {}
        for spec in self._specs:
            spec_cfg = config.rules.get(spec.key)
            rules[spec.key] = (
                RuleFactory.create(spec_cfg) if spec_cfg else default_rule
            )
        return rules

    def compare(
        self, project: Project, records: list[SourceRecord]
    ) -> ProjectResult:
        """比對單一建案與多個來源。

        Args:
            project: HouseQA 來源資料。
            records: 各外部來源的解析結果（可為多筆）。

        Returns:
            含逐欄結果的 :class:`ProjectResult`。
        """
        results = [self._compare_field(spec, project, records) for spec in self._specs]
        logger.info(
            "比對完成：%s（%d 欄 × %d 來源）",
            project.name, len(results), len(records),
        )
        return ProjectResult(
            project_id=project.project_id,
            name=project.name,
            source_urls={r.source: r.url for r in records},
            sources=[r.source for r in records],
            fields=results,
        )

    def _compare_field(
        self, spec: FieldSpec, project: Project, records: list[SourceRecord]
    ) -> FieldResult:
        """比對單一欄位（對每個來源各評一次），永不拋出例外。"""
        house_value: Any = None
        comparisons: list[SourceComparison] = []
        try:
            house_value = spec.house(project)
            rule = self._rules[spec.key]
            for record in records:
                source_value = spec.source(record)
                status, message = rule.evaluate(
                    house_value, source_value, spec.normalizer
                )
                comparisons.append(
                    SourceComparison(
                        source=record.source,
                        value=source_value,
                        status=status,
                        message=message,
                    )
                )
        except Exception as exc:  # noqa: BLE001 - 欄位級容錯
            logger.warning("欄位比對發生例外：%s - %s", spec.key, exc)
            comparisons.append(
                SourceComparison(
                    source="-", value=None, status=Status.WARNING,
                    message=f"比對發生錯誤：{exc}",
                )
            )

        return FieldResult(
            key=spec.key,
            label=spec.label,
            house_value=house_value,
            comparisons=comparisons,
            status=FieldResult.aggregate(comparisons),
        )
