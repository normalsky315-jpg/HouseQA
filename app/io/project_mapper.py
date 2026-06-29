"""將 data.json 的 project dict 轉成 :class:`Project` 模型。"""

from __future__ import annotations

from typing import Any

from app.models.project import Project

# data.json 中已明確建模的欄位；其餘欄位收進 Project.extra。
_KNOWN_FIELDS = {
    "name", "dev", "status", "addr", "permit", "floor", "count", "units",
    "layout", "loan", "handover", "kit", "bath", "other", "amenities",
    "notes", "lat", "lng", "s591",
}


class ProjectMapper:
    """data.json dict → Project 的轉換器。"""

    @staticmethod
    def from_dict(data: dict[str, Any]) -> Project:
        """將單筆 project dict 轉成 :class:`Project`。

        未知欄位會保留在 ``Project.extra``，確保 data.json 新增欄位時
        不會遺失資料，也不需修改本轉換器。

        Args:
            data: data.json ``projects`` 陣列中的單一元素。

        Returns:
            對應的 :class:`Project` 實例。
        """
        extra = {k: v for k, v in data.items() if k not in _KNOWN_FIELDS}
        return Project(
            name=data.get("name", ""),
            dev=data.get("dev", ""),
            status=data.get("status", ""),
            addr=data.get("addr", ""),
            permit=data.get("permit", ""),
            floor=data.get("floor", ""),
            count=data.get("count"),
            units=data.get("units"),
            layout=data.get("layout", ""),
            loan=data.get("loan", ""),
            handover=data.get("handover", ""),
            kit=list(data.get("kit", []) or []),
            bath=list(data.get("bath", []) or []),
            other=list(data.get("other", []) or []),
            amenities=dict(data.get("amenities", {}) or {}),
            notes=data.get("notes", ""),
            lat=data.get("lat"),
            lng=data.get("lng"),
            s591=data.get("s591", ""),
            extra=extra,
        )

    @staticmethod
    def from_list(items: list[dict[str, Any]]) -> list[Project]:
        """批次轉換 project dict 清單。"""
        return [ProjectMapper.from_dict(item) for item in items]
