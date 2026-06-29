"""樂居解析器測試（以最小化的 dt/dd 樣本）。"""

from __future__ import annotations

from app.parsers.parser_leju import ParserLeju

_SAMPLE = """
<html><head><title>【鳳凰萃】高雄市楠梓區，開價40~42萬坪起 - 樂居</title></head>
<body><dl>
<dt>地址：</dt><dd>大學二十六街399號</dd>
<dt>總戶數：</dt><dd>201 戶</dd>
<dt>總樓高：</dt><dd>15 樓</dd>
<dt>公設比：</dt><dd>36％</dd>
<dt>基地面積：</dt><dd>641 坪</dd>
<dt>車位數量：</dt><dd>137</dd>
<dt>建設公司：</dt><dd>隆大營建事業</dd>
<dt>坪數資料</dt><dd>2 房 24~33 坪 3 房 40~42 坪</dd>
</dl></body></html>
"""


def test_leju_parses_pairs() -> None:
    rec = ParserLeju().parse(_SAMPLE, url="https://www.leju.com.tw/community/X")
    assert rec.source == "leju"
    assert "鳳凰萃" in rec.get("name")
    assert rec.get("addr") == "大學二十六街399號"
    assert rec.get("units") == "201 戶"
    assert rec.get("public_ratio") == "36%"  # 全形％經 NFKC 正規化為半形
    assert rec.get("dev") == "隆大營建事業"
    assert rec.get("parking") == "137"
    # 樂居僅有地上樓層，不映射到比對用 floor
    assert rec.get("floor") is None


def test_leju_layout_normalizes_against_house_format() -> None:
    from app.compare.fields import normalize_layout

    rec = ParserLeju().parse(_SAMPLE)
    house = "二房(24~29坪)、三房(40~42坪)、2+1房(31~32坪)"
    assert normalize_layout(rec.get("layout")) == normalize_layout(house) == "2房3房"
