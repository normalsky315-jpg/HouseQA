"""Parser591 單元測試（使用倉庫內 test591.html 作為固定樣本）。"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.normalize.floor import FloorNormalizer
from app.parsers.parser591 import Parser591

_SAMPLE = Path("test591.html")


@pytest.fixture(scope="module")
def record():
    if not _SAMPLE.exists():
        pytest.skip("缺少 test591.html 樣本")
    html = _SAMPLE.read_text(encoding="utf-8")
    return Parser591().parse(html, url="https://newhouse.591.com.tw/139790/detail")


def test_basic_fields(record) -> None:
    assert record.source == "591"
    assert "高大之森" in record.get("name")
    assert "中德" in record.get("dev")
    assert "大學南路" in record.get("addr")


def test_planning_fields(record) -> None:
    assert FloorNormalizer().normalize(record.get("floor")) == "20F/B3"
    assert record.get("units") == 314
    assert record.get("buildings") == 2
    assert record.get("public_ratio") == "35.8%"


def test_materials_present(record) -> None:
    materials = record.get("materials")
    assert "櫻花" in materials
    assert "TOTO" in materials
