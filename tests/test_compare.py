"""比對引擎整合測試。"""

from __future__ import annotations

from app.compare.engine import CompareEngine
from app.config import Config
from app.models.diff_result import Status
from app.models.project import Project
from app.models.source_record import SourceRecord


def _engine() -> CompareEngine:
    return CompareEngine(Config.load().compare)


def test_matching_project_mostly_passes() -> None:
    project = Project(
        name="高大之森2・高大之上",
        dev="中德建設",
        addr="大學南路（藍田西段12等地號）",
        floor="20F/B3",
        units=314,
        layout="2棟20層；2房(20~27坪)／3房(33~34坪)；全平面309位",
        permit="114高市工建00763號",
        handover="2028下半年",
        loan="75%",
        kit=["櫻花廚具"],
        bath=["TOTO衛浴", "Hansgrohe龍頭"],
        notes="公設比35.8%／建蔽率33.66%／基地1253.51坪。",
        s591="https://newhouse.591.com.tw/139790/detail",
    )
    record = SourceRecord(
        source="591",
        url="https://newhouse.591.com.tw/139790/detail",
        fields={
            "name": "高大之森2高大之上",
            "dev": "中德建設股份有限公司",
            "addr": "高雄市楠梓區大學南路",
            "floor": "地上20層，地下3層",
            "units": 314,
            "buildings": 2,
            "parking": "平面式309個",
            "layout": "二房(20~27坪)、三房(33~34坪)",
            "public_ratio": "35.8%",
            "coverage_ratio": "33.66%",
            "base_area": "1253.51坪",
            "permit": "(114)高市工建築字第00763號",
            "handover": "2028年下半年",
            "loan": "75%",
            "materials": "櫻花廚具；衛浴：TOTO、Hansgrohe、Panasonic",
        },
    )

    result = _engine().compare(project, [record])
    by_key = {f.key: f.status for f in result.fields}

    assert by_key["name"] is Status.PASS
    assert by_key["dev"] is Status.PASS
    assert by_key["addr"] is Status.PASS
    assert by_key["floor"] is Status.PASS
    assert by_key["units"] is Status.PASS
    assert by_key["buildings"] is Status.PASS
    assert by_key["layout"] is Status.PASS
    assert by_key["base_area"] is Status.PASS
    assert by_key["public_ratio"] is Status.PASS
    assert by_key["permit"] is Status.PASS
    assert by_key["handover"] is Status.PASS
    assert by_key["kit"] is Status.PASS
    assert by_key["bath"] is Status.PASS


def test_mismatch_flags_fail() -> None:
    project = Project(name="A", units=100, s591="https://newhouse.591.com.tw/1/detail")
    record = SourceRecord(source="591", fields={"name": "A", "units": 500})
    result = _engine().compare(project, [record])
    by_key = {f.key: f.status for f in result.fields}
    assert by_key["units"] is Status.FAIL
    assert result.status is Status.FAIL
