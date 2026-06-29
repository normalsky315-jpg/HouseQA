"""來源轉接器（Source Adapter）。

把「某個來源如何為一個建案找到網址、抓取、解析」打包成 :class:`SourceAdapter`，
讓 :class:`~app.pipeline.QAPipeline` 以一致方式處理多個來源。新增來源＝新增一個
轉接器，pipeline 與比對引擎都不需更動。

對應方式採「混合制」：優先使用 data.json 中手動指定的網址（如 ``s591``、
``s958``），否則由各來源自行嘗試自動比對（house958 以建案名稱比對索引頁）。
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from app.config import Config
from app.fetchers.base import Fetcher
from app.fetchers.cache import HtmlCache
from app.fetchers.house958 import House958Fetcher
from app.fetchers.leju import LejuFetcher
from app.fetchers.site591 import Site591Fetcher
from app.models.project import Project
from app.parsers.base import Parser
from app.parsers.parser591 import Parser591
from app.parsers.parser_house958 import ParserHouse958
from app.parsers.parser_leju import ParserLeju
from app.utils.logger import get_logger

logger = get_logger(__name__)

HOUSE958_BASE = "http://house958.com/"
HOUSE958_INDEX_PAGES = ["H1.html"]  # 楠梓區（含高大）索引頁；可視需要增列其他分區。


def _norm_name(value: str) -> str:
    """建案名稱正規化（供名稱比對用）：去括號、符號、空白並轉小寫。"""
    text = re.sub(r"[【】（）()・·.,，、／/\s]", "", value or "")
    return text.lower()


@dataclass
class SourceAdapter:
    """單一來源的抓取／解析組合。"""

    name: str
    fetcher: Fetcher
    parser: Parser
    resolver: Callable[[Project], str | None]

    def resolve_url(self, project: Project) -> str | None:
        """為指定建案找出此來源的網址（找不到回傳 ``None``）。"""
        try:
            return self.resolver(project)
        except Exception as exc:  # noqa: BLE001 - 對應失敗不應中斷流程
            logger.warning("來源 %s 對應網址失敗：%s", self.name, exc)
            return None


class House958Index:
    """house958 建案索引：爬分區索引頁，建立「名稱 → 建案頁網址」對照。"""

    def __init__(
        self, fetcher: House958Fetcher, base_url: str, index_pages: list[str]
    ) -> None:
        self._fetcher = fetcher
        self._base = base_url
        self._pages = index_pages
        self._map: dict[str, str] | None = None

    def _build(self) -> dict[str, str]:
        mapping: dict[str, str] = {}
        for page in self._pages:
            try:
                html = self._fetcher.fetch(urljoin(self._base, page))
            except Exception as exc:  # noqa: BLE001
                logger.warning("house958 索引頁載入失敗：%s（%s）", page, exc)
                continue
            soup = BeautifulSoup(html, "lxml")
            for anchor in soup.find_all("a"):
                href = anchor.get("href")
                if not isinstance(href, str):
                    continue
                core = re.search(r"【(.+?)】", anchor.get_text())
                if core and href.endswith(".html"):
                    mapping.setdefault(_norm_name(core.group(1)), urljoin(self._base, href))
        logger.info("house958 索引建立完成，共 %d 筆", len(mapping))
        return mapping

    def match(self, name: str) -> str | None:
        """以建案名稱比對出 house958 網址。

        先精確比對；再嘗試「索引核心名稱包含於建案名稱」，但若建案名稱多出
        數字（代表不同期別，如 ``高大之森2``）則不配對，避免期別誤判。
        """
        if self._map is None:
            self._map = self._build()
        target = _norm_name(name)
        if target in self._map:
            return self._map[target]
        for core, url in self._map.items():
            if core and core in target:
                extra = target.replace(core, "")
                if not any(ch.isdigit() for ch in extra):
                    return url
        return None


def build_source_adapters(
    config: Config, cache: HtmlCache
) -> list[SourceAdapter]:
    """依設定建立啟用的來源轉接器清單。

    Args:
        config: 全域設定（``config.sources`` 決定啟用哪些來源）。
        cache: 共用的 HTML 快取。

    Returns:
        已啟用的 :class:`SourceAdapter` 清單。
    """
    adapters: list[SourceAdapter] = []
    enabled = config.sources or ["591"]

    if "591" in enabled:
        adapters.append(
            SourceAdapter(
                name="591",
                fetcher=Site591Fetcher(config.fetch, cache),
                parser=Parser591(),
                resolver=lambda p: getattr(p, "s591", "") or None,
            )
        )

    if "house958" in enabled:
        fetcher = House958Fetcher(config.fetch, cache)
        index = House958Index(fetcher, HOUSE958_BASE, HOUSE958_INDEX_PAGES)
        adapters.append(
            SourceAdapter(
                name="house958",
                fetcher=fetcher,
                parser=ParserHouse958(),
                resolver=lambda p: (p.extra.get("s958") or index.match(p.name)) or None,
            )
        )

    if "leju" in enabled:
        # 樂居社區網址為不可推導的亂碼 ID，故僅採 data.json 手動指定（sleju）。
        adapters.append(
            SourceAdapter(
                name="leju",
                fetcher=LejuFetcher(config.fetch, cache),
                parser=ParserLeju(),
                resolver=lambda p: p.extra.get("leju") or p.extra.get("sleju") or None,
            )
        )

    logger.info("啟用來源：%s", [a.name for a in adapters])
    return adapters
