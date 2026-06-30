"""HTML QA 報表產生器（多來源）。

每個建案一個區塊；每欄顯示 HouseQA 值與「每個來源各自的值＋狀態」，並標示
整體 PASS（綠）／WARNING（黃）／FAIL（紅）。
"""

from __future__ import annotations

import html
from pathlib import Path
from typing import Any

from app.models.diff_result import ProjectResult, QAReport, Status
from app.reports.base import Reporter
from app.utils.logger import get_logger

logger = get_logger(__name__)


def _fmt(value: Any) -> str:
    """將欄位值格式化為 HTML 安全字串。"""
    if value is None or value == "":
        return "<span class='muted'>—</span>"
    if isinstance(value, (list, tuple)):
        value = "、".join(str(v) for v in value)
    return html.escape(str(value))


class HtmlReporter(Reporter):
    """產生 ``report.html``。"""

    name = "html"
    extension = "html"

    def generate(self, report: QAReport, output_dir: Path) -> Path:
        """產生 HTML 報表並回傳檔案路徑。"""
        output_dir.mkdir(parents=True, exist_ok=True)
        path = output_dir / "report.html"
        path.write_text(self._render(report), encoding="utf-8")
        logger.info("已輸出 HTML 報表：%s", path)
        return path

    def _render(self, report: QAReport) -> str:
        summary = report.summary()
        sources = report.used_sources()
        blocks = "\n".join(self._render_project(p, sources) for p in report.projects)
        src_label = "、".join(sources) if sources else "（無）"
        return f"""<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>HouseQA 比對報告</title>
<style>{_CSS}</style>
</head>
<body>
<header class="topbar">
  <h1>🏠 HouseQA 比對報告</h1>
  <div class="generated">產生時間：{html.escape(report.generated_at)}　｜　比對來源：{html.escape(src_label)}</div>
</header>
<section class="summary">
  <div class="card total"><span>建案總數</span><b>{summary['total']}</b></div>
  <div class="card pass"><span>PASS</span><b>{summary['pass']}</b></div>
  <div class="card warning"><span>WARNING</span><b>{summary['warning']}</b></div>
  <div class="card fail"><span>FAIL</span><b>{summary['fail']}</b></div>
</section>
{blocks}
</body>
</html>"""

    def _render_project(self, project: ProjectResult, sources: list[str]) -> str:
        badge = self._badge(project.status)

        links = []
        for src in sources:
            url = project.source_urls.get(src)
            if url:
                links.append(
                    f"<a href='{html.escape(url)}' target='_blank'>{html.escape(src)}↗</a>"
                )
            else:
                links.append(f"<span class='muted'>{html.escape(src)}：無</span>")
        meta = "　".join(links)

        if project.skipped:
            body = f"<div class='skip'>已略過：{html.escape(project.skip_reason)}</div>"
        elif project.error:
            body = f"<div class='error'>錯誤：{html.escape(project.error)}</div>"
        else:
            head_cols = "".join(f"<th>{html.escape(s)}</th>" for s in sources)
            rows = "\n".join(self._render_row(f, sources) for f in project.fields)
            body = (
                f"<table><thead><tr><th>欄位</th><th>HouseQA</th>{head_cols}"
                "<th>狀態</th></tr></thead>"
                f"<tbody>{rows}</tbody></table>"
            )

        ai = (
            f"<div class='ai'><b>🤖 AI 分析</b><br>"
            f"{html.escape(project.ai_analysis).replace(chr(10), '<br>')}</div>"
            if project.ai_analysis else ""
        )
        return f"""<section class="project">
  <div class="project-head">
    <h2>{html.escape(project.name)} <small>#{html.escape(project.project_id)}</small></h2>
    {badge}
  </div>
  <div class="project-meta">{meta}</div>
  {body}
  {ai}
</section>"""

    def _render_row(self, field, sources: list[str]) -> str:
        cells = []
        for src in sources:
            status = field.source_status(src)
            value = field.source_value(src)
            if status is None:
                cells.append("<td class='muted'>—</td>")
            else:
                cells.append(
                    f"<td style='border-left:3px solid {status.color}' "
                    f"title='{html.escape(self._msg(field, src))}'>{_fmt(value)}</td>"
                )
        return (
            f"<tr class='{field.status.value.lower()}'>"
            f"<td class='label'>{html.escape(field.label)}</td>"
            f"<td>{_fmt(field.house_value)}</td>"
            f"{''.join(cells)}"
            f"<td>{self._badge(field.status)}</td></tr>"
        )

    @staticmethod
    def _msg(field, source: str) -> str:
        for comp in field.comparisons:
            if comp.source == source:
                return comp.message
        return ""

    @staticmethod
    def _badge(status: Status) -> str:
        return (
            f"<span class='badge' style='background:{status.color}'>"
            f"{status.value}</span>"
        )


_CSS = """
* { box-sizing: border-box; }
body { font-family: "Microsoft JhengHei", "Segoe UI", system-ui, sans-serif;
  margin: 0; background: #f4f5f7; color: #1f2329; }
.topbar { background: #1f2329; color: #fff; padding: 20px 32px; }
.topbar h1 { margin: 0; font-size: 22px; }
.generated { color: #9aa0a6; font-size: 13px; margin-top: 4px; }
.summary { display: flex; gap: 16px; padding: 24px 32px; flex-wrap: wrap; }
.card { background: #fff; border-radius: 10px; padding: 16px 24px; min-width: 120px;
  box-shadow: 0 1px 3px rgba(0,0,0,.1); display: flex; flex-direction: column; }
.card span { color: #5f6368; font-size: 13px; }
.card b { font-size: 28px; margin-top: 4px; }
.card.pass b { color: #2e7d32; } .card.warning b { color: #f9a825; }
.card.fail b { color: #c62828; }
.project { background: #fff; margin: 0 32px 20px; border-radius: 10px;
  box-shadow: 0 1px 3px rgba(0,0,0,.1); overflow: hidden; }
.project-head { display: flex; align-items: center; justify-content: space-between;
  padding: 16px 24px; border-bottom: 1px solid #eee; }
.project-head h2 { margin: 0; font-size: 18px; }
.project-head small { color: #9aa0a6; font-weight: normal; }
.project-meta { padding: 8px 24px; font-size: 13px; }
.project-meta a { color: #1a73e8; text-decoration: none; margin-right: 4px; }
table { width: 100%; border-collapse: collapse; }
th, td { padding: 10px 18px; text-align: left; font-size: 14px;
  border-bottom: 1px solid #f0f0f0; vertical-align: top; }
th { background: #fafafa; color: #5f6368; font-weight: 600; }
td.label { font-weight: 600; white-space: nowrap; }
tr.fail { background: #fff5f5; } tr.warning { background: #fffbf0; }
.badge { color: #fff; padding: 2px 10px; border-radius: 12px; font-size: 12px;
  font-weight: 600; white-space: nowrap; }
.muted { color: #bdc1c6; }
.skip, .error { padding: 16px 24px; color: #5f6368; }
.error { color: #c62828; }
.ai { margin: 0 24px 16px; padding: 14px 18px; background: #f1f8ff;
  border-left: 3px solid #1a73e8; font-size: 14px; line-height: 1.7; border-radius: 4px; }
"""
