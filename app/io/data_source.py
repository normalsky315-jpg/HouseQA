"""data.json 來源外掛。

把「data.json 從哪裡來」抽象成 :class:`DataSource`，讓 HouseQA 可從本地檔案
或 NKUinfos 的 GitHub 倉庫即時取得最新資料。新增來源（例如未來的 Admin API）
只需新增一個 :class:`DataSource` 子類別，呼叫端不需更動。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from app.config import DataConfig
from app.io.json_loader import JsonLoader
from app.utils.logger import get_logger

logger = get_logger(__name__)


class DataSource(ABC):
    """data.json 來源抽象基底。"""

    #: 給使用者看的來源描述。
    description: str = "data source"

    @abstractmethod
    def load(self) -> dict[str, Any]:
        """取得並解析 data.json。

        Returns:
            解析後的 dict（含 ``projects``）。
        """
        raise NotImplementedError


class LocalDataSource(DataSource):
    """從本地檔案載入 data.json。"""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.description = f"本地檔案 {self.path}"

    def load(self) -> dict[str, Any]:
        logger.info("資料來源：%s", self.description)
        return JsonLoader.load(self.path)


class RemoteDataSource(DataSource):
    """從 HTTP(S) URL 載入 data.json，失敗時可退回備援來源。"""

    def __init__(
        self,
        url: str,
        timeout: int = 30,
        fallback: DataSource | None = None,
    ) -> None:
        self.url = url
        self.timeout = timeout
        self.fallback = fallback
        self.description = f"遠端 {url}"

    def load(self) -> dict[str, Any]:
        logger.info("資料來源：%s", self.description)
        try:
            import requests  # 延遲匯入，純本地使用時不需安裝

            response = requests.get(self.url, timeout=self.timeout)
            response.raise_for_status()
            response.encoding = response.encoding or "utf-8"
            return JsonLoader.parse(response.text)
        except Exception as exc:  # noqa: BLE001 - 任何遠端錯誤都嘗試退回
            logger.warning("遠端載入失敗：%s（%s）", self.url, exc)
            if self.fallback is not None:
                logger.info("改用備援來源：%s", self.fallback.description)
                return self.fallback.load()
            raise


def build_data_source(override: str | None, config: DataConfig) -> DataSource:
    """依設定與命令列參數建立 :class:`DataSource`。

    ``override``（來自 ``--data``）優先於 ``config.source``。可接受的值：
        - ``"github"`` / ``"remote"``：使用 config 設定的 GitHub raw 連結。
        - ``"local"``：使用 config 設定的本地路徑。
        - ``http(s)://...``：任意遠端 URL。
        - 其他：視為本地檔案路徑。

    遠端來源一律以本地檔案作為備援，確保離線或 GitHub 暫時無法存取時仍可執行。

    Args:
        override: 命令列指定的來源（可為 ``None``）。
        config: 資料來源設定。

    Returns:
        對應的 :class:`DataSource`。
    """
    local = LocalDataSource(config.local)
    spec = (override or config.source or "local").strip()

    if spec in ("github", "remote"):
        return RemoteDataSource(config.raw_url, config.timeout, fallback=local)
    if spec == "local":
        return local
    if spec.startswith(("http://", "https://")):
        return RemoteDataSource(spec, config.timeout, fallback=local)
    return LocalDataSource(spec)
