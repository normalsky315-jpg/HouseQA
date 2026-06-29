"""讀取與驗證 NKUinfos 匯出的 data.json。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.utils.logger import get_logger

logger = get_logger(__name__)


class JsonLoader:
    """負責解析並驗證 data.json 結構（與來源無關）。"""

    @staticmethod
    def parse(text: str) -> dict[str, Any]:
        """解析 JSON 文字並驗證結構。

        Args:
            text: data.json 的原始字串內容。

        Returns:
            解析後的 dict，至少包含 ``projects`` 鍵。

        Raises:
            ValueError: JSON 格式錯誤或缺少 ``projects``。
        """
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"data.json 解析失敗：{exc}") from exc

        if not isinstance(data, dict) or "projects" not in data:
            raise ValueError("data.json 結構錯誤：缺少 'projects' 欄位")

        logger.info("解析 data.json，共 %d 筆建案", len(data.get("projects", [])))
        return data

    @staticmethod
    def load(path: str | Path) -> dict[str, Any]:
        """從本地檔案讀取並解析 data.json。

        Args:
            path: data.json 路徑。

        Returns:
            解析後的 dict。

        Raises:
            FileNotFoundError: 檔案不存在。
            ValueError: JSON 格式錯誤或缺少 ``projects``。
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"找不到資料檔：{path}")
        return JsonLoader.parse(path.read_text(encoding="utf-8"))
