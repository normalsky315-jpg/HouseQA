"""Reporter 外掛介面。

每種輸出格式（HTML、Excel、JSON……）對應一個 Reporter。報表只消費
:class:`QAReport` 模型，與比對邏輯解耦；新增格式不需修改比對流程。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from app.models.diff_result import QAReport


class Reporter(ABC):
    """報表產生器抽象基底。"""

    #: 格式名稱，對應 CLI 的 ``--report`` 與 config 的 ``formats``。
    name: str = "base"
    #: 輸出副檔名（不含點）。
    extension: str = "txt"

    @abstractmethod
    def generate(self, report: QAReport, output_dir: Path) -> Path:
        """產生報表檔。

        Args:
            report: 完整 QA 報告資料。
            output_dir: 輸出資料夾。

        Returns:
            產生的檔案路徑。
        """
        raise NotImplementedError
