"""集中式 logging 設定。

提供 :func:`setup_logging` 一次設定 root logger（檔案 + 主控台），
其餘模組僅需 ``logging.getLogger(__name__)`` 即可取得記錄器。
所有下載、解析、比對、錯誤皆透過此記錄器寫入 ``logs/houseqa.log``。
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

_CONFIGURED = False

_LOG_FORMAT = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(
    log_dir: str | Path = "logs",
    filename: str = "houseqa.log",
    level: str = "INFO",
) -> logging.Logger:
    """設定全域 logging，回傳 HouseQA 根記錄器。

    重複呼叫只會套用一次設定（具冪等性），避免重複新增 handler。

    Args:
        log_dir: 記錄檔資料夾，不存在時自動建立。
        filename: 記錄檔名稱。
        level: 記錄等級字串（DEBUG / INFO / WARNING / ERROR）。

    Returns:
        名為 ``houseqa`` 的記錄器。
    """
    global _CONFIGURED

    logger = logging.getLogger("houseqa")
    if _CONFIGURED:
        return logger

    log_level = getattr(logging, level.upper(), logging.INFO)
    logger.setLevel(log_level)
    logger.propagate = False

    directory = Path(log_dir)
    directory.mkdir(parents=True, exist_ok=True)

    formatter = logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT)

    file_handler = logging.FileHandler(directory / filename, encoding="utf-8")
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    stream = sys.stdout
    reconfigure = getattr(stream, "reconfigure", None)
    if callable(reconfigure):  # 確保 Windows 主控台能輸出中文與 emoji
        try:
            reconfigure(encoding="utf-8")
        except (OSError, ValueError):  # pragma: no cover - 視平台而定
            pass
    stream_handler = logging.StreamHandler(stream)
    stream_handler.setLevel(log_level)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    _CONFIGURED = True
    return logger


def get_logger(name: str) -> logging.Logger:
    """取得 ``houseqa`` 底下的子記錄器。

    Args:
        name: 子記錄器名稱，通常傳入 ``__name__``。

    Returns:
        對應的子記錄器。
    """
    return logging.getLogger("houseqa").getChild(name)
