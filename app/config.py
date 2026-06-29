"""應用程式設定載入。

從 ``config.yaml`` 讀取設定並轉成型別化的 dataclass，提供合理預設值，
讓其他模組不必直接接觸 YAML 結構，也不需在程式中寫死任何門檻。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

DEFAULT_CONFIG_PATH = Path("config.yaml")


@dataclass(slots=True)
class FetchConfig:
    """抓取（Fetcher）相關設定。"""

    headless: bool = True
    timeout: int = 60
    wait_until: str = "networkidle"
    retry: int = 3
    retry_backoff: float = 2.0


@dataclass(slots=True)
class CacheConfig:
    """HTML 快取相關設定。"""

    dir: Path = Path("cache")
    days: int = 7


@dataclass(slots=True)
class ReportConfig:
    """報表輸出相關設定。"""

    dir: Path = Path("reports")
    formats: list[str] = field(default_factory=lambda: ["html", "excel"])


@dataclass(slots=True)
class LogConfig:
    """記錄（logging）相關設定。"""

    dir: Path = Path("logs")
    file: str = "houseqa.log"
    level: str = "INFO"


@dataclass(slots=True)
class DataConfig:
    """data.json 來源設定。"""

    source: str = "github"  # github | local | <url> | <path>
    owner: str = "normalsky315-jpg"
    repo: str = "NKUinfos"
    branch: str = "main"
    remote_path: str = "data.json"
    local: Path = Path("data/data.json")
    timeout: int = 30

    @property
    def raw_url(self) -> str:
        """組出 GitHub raw 連結。"""
        return (
            f"https://raw.githubusercontent.com/"
            f"{self.owner}/{self.repo}/{self.branch}/{self.remote_path}"
        )


@dataclass(slots=True)
class CompareConfig:
    """比對規則設定。

    Attributes:
        default: 未列出欄位採用的預設規則設定。
        rules: 欄位 key 對應的規則設定字典。
    """

    default: dict[str, Any] = field(default_factory=lambda: {"type": "exact"})
    rules: dict[str, dict[str, Any]] = field(default_factory=dict)


@dataclass(slots=True)
class Config:
    """HouseQA 全域設定。"""

    fetch: FetchConfig = field(default_factory=FetchConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    report: ReportConfig = field(default_factory=ReportConfig)
    log: LogConfig = field(default_factory=LogConfig)
    data: DataConfig = field(default_factory=DataConfig)
    sources: list[str] = field(default_factory=lambda: ["591"])
    compare: CompareConfig = field(default_factory=CompareConfig)

    @classmethod
    def load(cls, path: str | Path = DEFAULT_CONFIG_PATH) -> "Config":
        """從 YAML 檔載入設定；檔案不存在時回傳全預設設定。

        Args:
            path: 設定檔路徑。

        Returns:
            填妥的 :class:`Config` 實例。
        """
        path = Path(path)
        raw: dict[str, Any] = {}
        if path.exists():
            with open(path, "r", encoding="utf-8") as handle:
                raw = yaml.safe_load(handle) or {}

        fetch = FetchConfig(**raw.get("fetch", {}))

        cache_raw = dict(raw.get("cache", {}))
        if "dir" in cache_raw:
            cache_raw["dir"] = Path(cache_raw["dir"])
        cache = CacheConfig(**cache_raw)

        report_raw = dict(raw.get("report", {}))
        if "dir" in report_raw:
            report_raw["dir"] = Path(report_raw["dir"])
        report = ReportConfig(**report_raw)

        log_raw = dict(raw.get("log", {}))
        if "dir" in log_raw:
            log_raw["dir"] = Path(log_raw["dir"])
        log = LogConfig(**log_raw)

        data_raw = dict(raw.get("data", {}))
        if "local" in data_raw:
            data_raw["local"] = Path(data_raw["local"])
        data = DataConfig(**data_raw)

        compare_raw = raw.get("compare", {})
        compare = CompareConfig(
            default=compare_raw.get("default", {"type": "exact"}),
            rules=compare_raw.get("rules", {}),
        )

        sources = list(raw.get("sources", ["591"]))

        return cls(
            fetch=fetch, cache=cache, report=report, log=log,
            data=data, sources=sources, compare=compare,
        )
