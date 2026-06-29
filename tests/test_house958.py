"""house958 解析器與名稱比對測試。"""

from __future__ import annotations

from app.normalize.floor import FloorNormalizer
from app.parsers.parser_house958 import ParserHouse958
from app.sources import House958Index

_SAMPLE = """
<html><head><title>茂德【高大之森】</title></head><body>
<div>
◎個案名稱 : 茂德【高大之森】
◎基地位置 : 楠海路&大學三十一街
◎基地面積 : 1345.5坪(@66.07萬/坪)
◎樓層規劃 : 15F/B4
◎推出住家 : 358戶
◎投資興建 : 茂德建設(@36萬)
◎公設比例 : 35.8%
◎住家規劃 : 2~3房
</div></body></html>
"""


def test_house958_parses_labels() -> None:
    rec = ParserHouse958().parse(_SAMPLE, url="http://house958.com/H1a27.html")
    assert rec.source == "house958"
    assert "高大之森" in rec.get("name")
    assert rec.get("dev") == "茂德建設(@36萬)"
    assert rec.get("units") == "358戶"
    assert rec.get("public_ratio") == "35.8%"
    assert FloorNormalizer().normalize(rec.get("floor")) == "15F/B4"


class _FakeFetcher:
    """回傳固定索引頁 HTML 的假抓取器。"""

    def __init__(self, html: str) -> None:
        self._html = html

    def fetch(self, url: str, force_download: bool = False) -> str:  # noqa: ARG002
        return self._html


_INDEX = """
<html><body>
<a href="H1a27.html">【高大之森】</a>
<a href="H1a37.html">【一靚】</a>
<a href="H1a10.html">【馥御】</a>
</body></html>
"""


def test_index_name_matching() -> None:
    index = House958Index(_FakeFetcher(_INDEX), "http://house958.com/", ["H1.html"])
    # 精確比對
    assert index.match("高大之森") == "http://house958.com/H1a27.html"
    # 核心名稱包含於建案名稱（建商前綴）
    assert index.match("遠雄一靚") == "http://house958.com/H1a37.html"
    assert index.match("崑庭馥御") == "http://house958.com/H1a10.html"
    # 分期案不可誤配到一期（名稱多出數字）
    assert index.match("高大之森2・高大之上") is None
