"""品牌正規化。

將同一品牌的各種寫法（``TOTO衛浴``、``TOTO Japan``、``ToTo``）統一成
標準名稱，使建材、廚具、衛浴的比對不受用字差異影響。

品牌字典刻意外置為模組層級常數，未來擴充只需新增條目，
不需修改正規化邏輯，符合開放／封閉原則。
"""

from __future__ import annotations

import re

from app.normalize.text import clean_text

# 標準名稱 -> 同義詞（小寫、去空白後比對）。
BRAND_DICTIONARY: dict[str, list[str]] = {
    "TOTO": ["toto", "toto衛浴", "totojapan"],
    "HCG": ["hcg", "和成", "和成衛浴", "hcg和成"],
    "INAX": ["inax", "inax衛浴"],
    "ROCA": ["roca", "羅卡"],
    "GROHE": ["grohe", "高儀"],
    "Hansgrohe": ["hansgrohe", "漢斯格雅"],
    "Villeroy&Boch": ["villeroy&boch", "villeroyboch", "v&b", "vb"],
    "Panasonic": ["panasonic", "國際牌", "國際"],
    "Bosch": ["bosch", "博世"],
    "櫻花": ["櫻花", "sakura", "櫻花廚具", "櫻花三機"],
    "林內": ["林內", "rinnai"],
    "豪山": ["豪山"],
    "美標": ["美標", "americanstandard"],
    "Miton": ["miton", "義大利miton"],
    "noblessa": ["noblessa", "德國noblessa"],
    "日立": ["日立", "hitachi"],
    "BWT": ["bwt", "德國bwt"],
    "3M": ["3m"],
    "大金": ["大金", "daikin"],
    "Honeywell": ["honeywell"],
}

# 常見後綴詞，比對前移除以提高命中率。
_SUFFIXES = ["衛浴", "廚具", "龍頭", "五金", "系統", "設備", "電梯", "三機", "牌"]

# 反向索引：同義詞 -> 標準名稱。
_LOOKUP: dict[str, str] = {}
for _canonical, _aliases in BRAND_DICTIONARY.items():
    _LOOKUP[_canonical.lower().replace(" ", "")] = _canonical
    for _alias in _aliases:
        _LOOKUP[_alias.lower().replace(" ", "")] = _canonical


class BrandNormalizer:
    """品牌字串正規化器。"""

    def normalize(self, value: str) -> str:
        """將單一品牌字串轉成標準名稱。

        Args:
            value: 原始品牌字串，例如 ``"TOTO衛浴"``。

        Returns:
            標準品牌名稱；無對應時回傳清理後的原字串。
        """
        cleaned = clean_text(value)
        key = cleaned.lower().replace(" ", "")
        if key in _LOOKUP:
            return _LOOKUP[key]

        stripped = key
        for suffix in _SUFFIXES:
            stripped = stripped.replace(suffix.lower(), "")
        if stripped in _LOOKUP:
            return _LOOKUP[stripped]

        # 退而求其次：找出字串中是否包含任一已知品牌關鍵字。
        for alias, canonical in _LOOKUP.items():
            if alias and alias in key:
                return canonical
        return cleaned

    def contains_brand(self, haystack: str, needle: str) -> bool:
        """判斷 ``haystack`` 是否（在品牌語意上）包含 ``needle``。

        先嘗試品牌標準化比對，再退回子字串比對，以涵蓋非品牌建材。

        Args:
            haystack: 來源建材長字串（如 591 的建材說明）。
            needle: 預期出現的單項建材／品牌。

        Returns:
            是否視為包含。
        """
        norm_needle = self.normalize(needle)
        norm_hay = clean_text(haystack)
        # 品牌語意命中
        if norm_needle and norm_needle in BRAND_DICTIONARY:
            for alias in [norm_needle.lower()] + [
                a for a in BRAND_DICTIONARY[norm_needle]
            ]:
                if re.search(re.escape(alias), norm_hay, re.IGNORECASE):
                    return True
        # 一般子字串命中（去後綴）
        core = norm_needle
        for suffix in _SUFFIXES:
            core = core.replace(suffix, "")
        core = core.strip()
        return bool(core) and core.lower() in norm_hay.lower()
