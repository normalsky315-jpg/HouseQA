"""建立行政區「主名單」：以 house958 建案為主，用 591 清單擴充比對。

流程：
1. 抓 house958 分區索引頁 → 該區全部建案（名單主體）
2. 逐案抓 house958 案頁，用 ParserHouse958 解析出正式案名、建商、樓層、
   戶數、格局、工地位置、開價等（索引頁案名偶有筆誤，以案頁為準）
3. 用正規化名稱對上 591 在線清單（fetch_591_district.py 的輸出），補 s591
4. 對上現有 data.json（KHHouse）的案子，標記 on_site 並沿用 sleju/s591
5. 591 有、house958 沒有的案，另列 only591 供人工決定是否納入

使用方式：
  python scripts/build_masterlist.py --p591 reports/tier1_591.json 楠梓 仁武
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

HOUSE958_BASE = "http://house958.com/"

# house958 首頁各分區索引頁對照（2026-07 確認）
H958_INDEX = {
    "楠梓": "H1.html",
    "左營": "H2.html",
    "鼓山": "H3.html",
    "三民": "H4.html",
    "前金": "H5.html",
    "新興": "H6.html",
    "苓雅": "H7.html",
    "鳳山": "H11.html",
    "仁武": "H12.html",
}

_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/137.0 Safari/537.36"
)

_ROMAN = {"Ⅰ": "1", "Ⅱ": "2", "Ⅲ": "3", "Ⅳ": "4", "Ⅴ": "5",
          "II": "2", "III": "3", "IV": "4"}


def norm_name(value: str) -> str:
    """建案名稱正規化：去括號/符號/空白、羅馬數字轉阿拉伯、轉小寫。"""
    s = value.strip()
    for k, v in _ROMAN.items():
        s = s.replace(k, v)
    s = re.sub(r"[【】\[\]()（）『』「」\s．.‧・·•●˙@\-‧|｜/／&＆＋+]", "", s)
    return s.lower()


def names_match(a: str, b: str) -> bool:
    """兩個正規化名稱是否視為同案（相等、包含、或高相似度）。"""
    if not a or not b:
        return False
    if a == b:
        return True
    shorter, longer = sorted((a, b), key=len)
    if len(shorter) >= 2 and shorter in longer:
        return True
    # 模糊比對：容忍一兩字之差（如 興連誠99 vs 興連城99）
    import difflib

    return len(shorter) >= 3 and difflib.SequenceMatcher(None, a, b).ratio() >= 0.75


def display_name(raw_name: str) -> str:
    """案頁名稱轉顯示名：優先取【】內文字（外側通常是建商簡稱）。"""
    m = re.search(r"【(.+?)】", raw_name)
    return (m.group(1) if m else raw_name).strip()


def _get(url: str) -> str:
    import requests

    r = requests.get(url, headers={"User-Agent": _UA}, timeout=30)
    r.raise_for_status()
    r.encoding = r.apparent_encoding or "utf-8"
    return r.text


def fetch_h958_district(district: str) -> list[dict]:
    """抓 house958 單一分區索引頁的建案連結清單。"""
    html = _get(HOUSE958_BASE + H958_INDEX[district])
    items: dict[str, dict] = {}
    for m in re.finditer(r'<a[^>]+href="(H\d+a\d+\.html?)"[^>]*>(.*?)</a>', html, re.S):
        href, inner = m.groups()
        name = re.sub(r"<[^>]+>", "", inner)
        name = re.sub(r"[【】\s]", "", name).strip()
        if not name:
            continue
        items.setdefault(href, {"index_name": name, "s958": HOUSE958_BASE + href})
    return list(items.values())


def enrich_from_case_page(item: dict) -> None:
    """抓 house958 案頁，補正式案名與基本欄位。"""
    from app.parsers.parser_house958 import ParserHouse958

    try:
        html = _get(item["s958"])
        rec = ParserHouse958().parse(html, url=item["s958"])
    except Exception as exc:  # noqa: BLE001 - 單頁失敗不中斷整批
        print(f"    ⚠ 案頁抓取失敗 {item['s958']}：{exc}")
        item["name"] = item["index_name"]
        return
    f, raw = rec.fields, rec.raw
    item["name"] = display_name(f.get("name") or item["index_name"])
    item["dev"] = f.get("dev", "")
    item["floor"] = f.get("floor", "")
    item["units"] = f.get("units", "")
    item["layout"] = f.get("layout", "")
    item["addr"] = raw.get("工地位置", "")
    item["open_price"] = raw.get("住家開價", "")
    item["public_ratio"] = f.get("public_ratio", "")
    item["progress"] = raw.get("工程進度", "")


def main() -> None:
    parser = argparse.ArgumentParser(description="建立行政區建案主名單（house958 為主）")
    parser.add_argument("districts", nargs="+", choices=sorted(H958_INDEX))
    parser.add_argument("--p591", default="reports/tier1_591.json",
                        help="fetch_591_district.py 的輸出檔")
    parser.add_argument("--data", default=r"C:\Users\mrsky\Documents\GITHUB\KHHouse\data.json",
                        help="網站現有 data.json（標記 on_site、沿用 sleju）")
    parser.add_argument("--out", default="reports/masterlist.json")
    args = parser.parse_args()

    p591 = json.loads(Path(args.p591).read_text(encoding="utf-8"))
    site = json.loads(Path(args.data).read_text(encoding="utf-8"))
    site_by_norm = {norm_name(p["name"]): p for p in site.get("projects", [])}

    result: dict[str, dict] = {}
    for district in args.districts:
        print(f"處理 {district}區 …")
        h958 = fetch_h958_district(district)
        for it in h958:
            enrich_from_case_page(it)
            time.sleep(0.4)  # 禮貌性間隔

        s591_items = {norm_name(x["name"]): x for x in p591.get(district, [])}
        used_591 = set()

        master = []
        for it in h958:
            key = norm_name(it["name"])
            hit = None
            for k, v in s591_items.items():
                if names_match(key, k):
                    hit = v
                    used_591.add(k)
                    break
            onsite = None
            for k, v in site_by_norm.items():
                if names_match(key, k):
                    onsite = v
                    break
            entry = {
                "name": it["name"],
                "district": district,
                "dev": it.get("dev", ""),
                "floor": it.get("floor", ""),
                "units": it.get("units", ""),
                "layout": it.get("layout", ""),
                "addr": it.get("addr", ""),
                "open_price": it.get("open_price", ""),
                "public_ratio": it.get("public_ratio", ""),
                "progress": it.get("progress", ""),
                "s958": it["s958"],
                "s591": (onsite or {}).get("s591") or (hit["url"] if hit else ""),
                "sleju": (onsite or {}).get("leju") or (onsite or {}).get("sleju") or "",
                "on_site": bool(onsite),
            }
            if hit:
                entry["_591"] = {
                    "名稱": hit["name"],
                    "價格": (hit["price"] + (hit.get("price_unit") or "")) if hit.get("price") else "",
                    "坪數": hit.get("area", ""),
                    "房型": hit.get("room", ""),
                    "位置": hit.get("addr", ""),
                    "銷售狀態": hit.get("sale_status_label", ""),
                }
            master.append(entry)

        only591 = []
        for k, x in s591_items.items():
            if k in used_591:
                continue
            onsite = None
            for k2, v in site_by_norm.items():
                if names_match(k, k2):
                    onsite = v
                    break
            only591.append({**x, "on_site": bool(onsite)})

        result[district] = {"master": master, "only591": only591}
        matched = sum(1 for x in master if x["s591"])
        onsite_n = sum(1 for x in master if x["on_site"])
        print(f"  {district}：house958 {len(master)} 案（591 對上 {matched}、已在網站 {onsite_n}）；"
              f"591 獨有 {len(only591)} 案")

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"已輸出：{out}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
