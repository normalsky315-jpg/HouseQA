"""HouseQA 命令列介面。

支援：
    python compare.py                  # 比對全部建案並產生預設報表
    python compare.py --all
    python compare.py --project 139790 # 只比對指定建案編號
    python compare.py --update         # 強制重新下載（忽略快取）
    python compare.py --report html
    python compare.py --report excel
    python compare.py --cache-clear    # 清除所有快取後結束
    python compare.py --cache-only     # 僅用快取，不連線
"""

from __future__ import annotations

import argparse
from datetime import datetime

from app.config import Config
from app.io.data_source import build_data_source
from app.io.project_mapper import ProjectMapper
from app.models.project import Project
from app.pipeline import QAPipeline
from app.utils.logger import setup_logging

VERSION = "1.0.0"


def _build_parser() -> argparse.ArgumentParser:
    """建立 argparse 參數解析器。"""
    parser = argparse.ArgumentParser(
        prog="compare.py",
        description="HouseQA — NKUinfos 與 591 建案資料自動化 QA 比對系統",
    )
    parser.add_argument("--config", default="config.yaml", help="設定檔路徑")
    parser.add_argument(
        "--data", default=None,
        help="data.json 來源：github / local / 一個 URL / 本地路徑（預設讀 config）",
    )
    parser.add_argument("--all", action="store_true", help="比對全部建案（預設行為）")
    parser.add_argument("--project", metavar="ID", help="只比對指定建案編號")
    parser.add_argument(
        "--update", "--force-download", dest="force_download",
        action="store_true", help="忽略快取強制重新下載",
    )
    parser.add_argument("--cache-only", action="store_true", help="只使用快取，不連線")
    parser.add_argument("--cache-clear", action="store_true", help="清除所有快取後結束")
    parser.add_argument(
        "--report", action="append", metavar="FORMAT",
        help="輸出報表格式（html / excel / json），可重複指定；預設讀 config",
    )
    parser.add_argument("--version", action="version", version=f"HouseQA {VERSION}")
    return parser


def _banner() -> None:
    """輸出啟動橫幅。"""
    print("=" * 60)
    print(f"🏠 HouseQA  v{VERSION}")
    print(f"啟動時間：{datetime.now():%Y-%m-%d %H:%M:%S}")
    print("=" * 60)


def _select_projects(all_projects: list[Project], project_id: str | None) -> list[Project]:
    """依 --project 篩選建案。"""
    if not project_id:
        return all_projects
    return [p for p in all_projects if p.project_id == project_id]


def _print_summary(report, outputs) -> None:
    """於主控台輸出摘要。"""
    summary = report.summary()
    print()
    print("-" * 60)
    print(
        f"完成：共 {summary['total']} 案　"
        f"✅ PASS {summary['pass']}　"
        f"⚠️ WARNING {summary['warning']}　"
        f"❌ FAIL {summary['fail']}"
    )
    for path in outputs:
        print(f"📄 報表：{path}")
    print("-" * 60)


def main(argv: list[str] | None = None) -> int:
    """CLI 進入點。

    Args:
        argv: 參數清單（預設取自 ``sys.argv``）。

    Returns:
        程序結束碼：0 成功，1 發生可預期錯誤，2 找不到指定建案。
    """
    args = _build_parser().parse_args(argv)
    config = Config.load(args.config)
    setup_logging(config.log.dir, config.log.file, config.log.level)
    _banner()

    pipeline = QAPipeline(config)

    if args.cache_clear:
        removed = pipeline.cache.clear()
        print(f"🧹 已清除 {removed} 筆快取")
        return 0

    try:
        data = build_data_source(args.data, config.data).load()
    except Exception as exc:  # noqa: BLE001 - 對外回報友善錯誤
        print(f"❌ 載入資料失敗：{exc}")
        return 1

    projects = ProjectMapper.from_list(data.get("projects", []))
    selected = _select_projects(projects, args.project)
    if args.project and not selected:
        print(f"❌ 找不到建案編號：{args.project}")
        return 2

    report = pipeline.run(
        selected,
        force_download=args.force_download,
        cache_only=args.cache_only,
    )

    formats = args.report if args.report else config.report.formats
    outputs = pipeline.generate_reports(report, formats)
    _print_summary(report, outputs)
    return 0
