"""正規化器單元測試。"""

from __future__ import annotations

from app.compare.fields import normalize_handover, normalize_layout, normalize_permit
from app.normalize.address import AddressNormalizer
from app.normalize.area import AreaNormalizer
from app.normalize.brand import BrandNormalizer
from app.normalize.floor import FloorNormalizer


def test_brand_synonyms_unify() -> None:
    brand = BrandNormalizer()
    assert brand.normalize("TOTO衛浴") == "TOTO"
    assert brand.normalize("toto") == "TOTO"
    assert brand.normalize("國際牌") == "Panasonic"
    assert brand.normalize("和成") == "HCG"


def test_brand_contains() -> None:
    brand = BrandNormalizer()
    materials = "櫻花廚具；衛浴：TOTO、Hansgrohe、Panasonic"
    assert brand.contains_brand(materials, "TOTO衛浴")
    assert brand.contains_brand(materials, "櫻花廚具")
    assert not brand.contains_brand(materials, "INAX")


def test_address_strips_admin_and_paren() -> None:
    addr = AddressNormalizer()
    assert addr.normalize("高雄市楠梓區大學南路") == "大學南路"
    assert addr.normalize("大學南路（藍田西段12等地號）") == "大學南路"


def test_floor_canonical_form() -> None:
    floor = FloorNormalizer()
    assert floor.normalize("地上20層，地下3層") == "20F/B3"
    assert floor.normalize("20F/B3") == "20F/B3"
    assert floor.normalize("多期多棟") == ""  # 非單一樓層 → 視為無法比對


def test_area_extracts_number() -> None:
    area = AreaNormalizer()
    assert area.normalize("基地1253.51坪") == 1253.51
    assert area.normalize(1253.51) == 1253.51
    assert area.normalize("無資料") is None


def test_layout_room_tokens() -> None:
    house = "2棟20層；2房(20~27坪)／3房(33~34坪)；全平面309位"
    source = "二房(20~27坪)、三房(33~34坪)"
    assert normalize_layout(house) == normalize_layout(source) == "2房3房"


def test_handover_and_permit() -> None:
    assert normalize_handover("2028下半年") == normalize_handover("2028年下半年")
    assert normalize_permit("114高市工建00763號") == normalize_permit(
        "(114)高市工建築字第00763號"
    )
