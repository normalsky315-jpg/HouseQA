"""HouseQA 主流程編排。

把載入、抓取、解析、比對、報表串成單一可重用的流程物件。各步驟皆透過
來源轉接器（:class:`~app.sources.SourceAdapter`）與抽象介面協作，因此本檔案
不直接依賴任何特定網站或報表格式，亦天生支援多來源比對。
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from app.compare.engine import CompareEngine
from app.config import Config
from app.fetchers.cache import HtmlCache
from app.models.diff_result import ProjectResult, QAReport
from app.models.project import Project
from app.models.source_record import SourceRecord
from app.reports.excel_report import ExcelReporter
from app.reports.html_report import HtmlReporter
from app.reports.json_report import JsonReporter
from app.reports.registry import ReporterRegistry
from app.sources import build_source_adapters
from app.utils.logger import get_logger
from app.utils.timer import Timer

logger = get_logger(__name__)


class QAPipeline:
    """串接所有元件的 QA 流程。"""

    def __init__(self, config: Config) -> None:
        """依設定建立流程，並註冊內建來源與報表外掛。"""
        self.config = config
        self.cache = HtmlCache(config.cache.dir, config.cache.days)
        self.adapters = build_source_adapters(config, self.cache)
        self.engine = CompareEngine(config.compare)

        self.reporters = ReporterRegistry()
        self.reporters.register(HtmlReporter())
        self.reporters.register(ExcelReporter())
        self.reporters.register(JsonReporter())

    def run(
        self,
        projects: list[Project],
        *,
        force_download: bool = False,
        cache_only: bool = False,
    ) -> QAReport:
        """對一批建案執行完整比對流程。

        Args:
            projects: 待比對建案清單。
            force_download: 忽略快取重新下載。
            cache_only: 只使用快取，缺快取者略過（不連線）。

        Returns:
            完整的 :class:`QAReport`。
        """
        results: list[ProjectResult] = []
        with Timer() as timer:
            for index, project in enumerate(projects, start=1):
                logger.info("(%d/%d) 處理建案：%s", index, len(projects), project.name)
                results.append(
                    self._process_one(project, force_download, cache_only)
                )

        report = QAReport(
            projects=results,
            generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )
        logger.info("流程完成，耗時 %.1f 秒；%s", timer.elapsed, report.summary())
        return report

    def _process_one(
        self, project: Project, force_download: bool, cache_only: bool
    ) -> ProjectResult:
        """處理單一建案：彙集所有來源後比對，全程容錯。"""
        records: list[SourceRecord] = []
        for adapter in self.adapters:
            record = self._collect(adapter, project, force_download, cache_only)
            if record is not None:
                records.append(record)

        if not records:
            return ProjectResult(
                project_id=project.project_id,
                name=project.name,
                skipped=True,
                skip_reason="沒有任何可用來源（無網址或無快取）",
            )
        return self.engine.compare(project, records)

    def _collect(
        self, adapter, project: Project, force_download: bool, cache_only: bool
    ) -> SourceRecord | None:
        """以單一來源抓取並解析建案資料；失敗回傳 ``None`` 不中斷其他來源。"""
        url = adapter.resolve_url(project)
        if not url:
            return None
        try:
            if cache_only:
                html = self.cache.get(url)
                if html is None:
                    logger.info("略過 %s（cache-only 無快取）：%s", adapter.name, url)
                    return None
            else:
                html = adapter.fetcher.fetch(url, force_download=force_download)
            return adapter.parser.parse(html, url=url)
        except Exception as exc:  # noqa: BLE001 - 單一來源容錯
            logger.error("來源 %s 處理失敗：%s（%s）", adapter.name, project.name, exc)
            return None

    def generate_reports(
        self, report: QAReport, formats: list[str]
    ) -> list[Path]:
        """依指定格式產生報表。

        Args:
            report: QA 報告。
            formats: 報表格式名稱清單（html / excel / json）。

        Returns:
            產生的檔案路徑清單。
        """
        outputs: list[Path] = []
        for fmt in formats:
            reporter = self.reporters.get(fmt)
            if reporter is None:
                logger.warning("未知的報表格式，略過：%s", fmt)
                continue
            outputs.append(reporter.generate(report, self.config.report.dir))
        return outputs
