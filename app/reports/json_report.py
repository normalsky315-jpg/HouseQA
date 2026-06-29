"""JSON QA 報表產生器。

輸出 ``report.json``，便於後續程式化處理（例如未來的 AI 分析或前端儀表板）。
"""

from __future__ import annotations

import json
from pathlib import Path

from app.models.diff_result import QAReport
from app.reports.base import Reporter
from app.utils.logger import get_logger

logger = get_logger(__name__)


class JsonReporter(Reporter):
    """產生 ``report.json``。"""

    name = "json"
    extension = "json"

    def generate(self, report: QAReport, output_dir: Path) -> Path:
        """產生 JSON 報表並回傳檔案路徑。"""
        output_dir.mkdir(parents=True, exist_ok=True)
        path = output_dir / "report.json"
        payload = {
            "generated_at": report.generated_at,
            "summary": report.summary(),
            "projects": [p.model_dump(mode="json") for p in report.projects],
        }
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        logger.info("已輸出 JSON 報表：%s", path)
        return path
