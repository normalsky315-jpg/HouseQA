"""驗證樂居社區網址並回填 sleju＋實價登錄價格。

輸入一份「案名 → 樂居社區網址候選」的 JSON 對照，逐案：
1. 用 LejuFetcher 抓社區頁（過 Cloudflare、含快取）
2. 核對頁面案名（容忍建商前綴，如「永信澄光」對「澄光」）與行政區
3. 通過才寫入：sleju、avgPrice（一年成交均價）、minPrice/maxPrice
   （歷史最低/最高價）、count（已銷售戶數）

使用方式：
  python scripts/enrich_from_leju.py --map candidates.json --district 仁武
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def norm(s: str) -> str:
    s = re.sub(r"[【】\[\]()（）『』「」\s．.‧・·•●˙@\-‧|｜/／&＆＋+]", "", s or "")
    for k, v in {"Ⅰ": "1", "Ⅱ": "2", "Ⅲ": "3", "II": "2", "NO": "", "No": "", "no": ""}.items():
        s = s.replace(k, v)
    return s.lower()


def name_ok(ours: str, theirs: str) -> bool:
    a, b = norm(ours), norm(theirs)
    if not a or not b:
        return False
    return a in b or b in a


def num(s: str) -> float | None:
    m = re.search(r"([\d.]+)", s or "")
    return float(m.group(1)) if m else None


def main() -> None:
    parser = argparse.ArgumentParser(description="樂居社區網址驗證與價格回填")
    parser.add_argument("--map", required=True, help="案名→樂居網址 JSON")
    parser.add_argument("--district", required=True)
    parser.add_argument("--data", action="append", default=[],
                        help="data.json 路徑（可多個）")
    args = parser.parse_args()
    data_paths = args.data or [
        r"C:\Users\mrsky\Documents\GITHUB\KHHouse\data.json",
        str(Path(__file__).resolve().parents[1] / "data" / "data.json"),
    ]

    from app.config import Config
    from app.fetchers.cache import HtmlCache
    from app.fetchers.leju import LejuFetcher
    from app.parsers.parser_leju import ParserLeju

    cfg = Config.load("config.yaml")
    fetcher = LejuFetcher(cfg.fetch, HtmlCache("cache", days=7))
    parser_leju = ParserLeju()

    cand = json.loads(Path(args.map).read_text(encoding="utf-8"))
    verified: dict[str, dict] = {}
    for name, url in cand.items():
        try:
            html = fetcher.fetch(url)
            rec = parser_leju.parse(html, url=url)
        except Exception as exc:  # noqa: BLE001
            print(f"⚠ {name}：抓取失敗（{exc}）")
            continue
        leju_name = rec.fields.get("name", "")
        in_district = f"{args.district}區" in html
        if not name_ok(name, leju_name) or not in_district:
            print(f"✗ {name}：不符（樂居名「{leju_name}」，{args.district}區={in_district}）→ 不寫入")
            continue
        raw = rec.raw
        sold = raw.get("已銷售戶數", "")
        count = None
        m = re.match(r"\s*(\d+)", sold)
        if m:
            count = int(m.group(1))
        # 一年成交均價可能是「待定」（預售）；備援用全期間的平均成交均價
        avg = num(raw.get("一年成交均價", "")) or num(raw.get("平均成交均價", ""))
        verified[name] = {
            "sleju": url,
            "leju_name": leju_name,
            "avgPrice": avg,
            "minPrice": num(raw.get("歷史最低價", "")),
            "maxPrice": num(raw.get("歷史最高價", "")),
            "count": count,
        }
        print(f"✓ {name}（樂居：{leju_name}）均價 {verified[name]['avgPrice']}，"
              f"區間 {verified[name]['minPrice']}~{verified[name]['maxPrice']}，實登 {count} 筆")

    for path in data_paths:
        db = json.loads(Path(path).read_text(encoding="utf-8"))
        touched = 0
        for p in db["projects"]:
            v = verified.get(p.get("name", ""))
            if not v or p.get("district") != args.district:
                continue
            p["sleju"] = v["sleju"]
            for key in ("avgPrice", "minPrice", "maxPrice", "count"):
                if v[key] is not None:
                    p[key] = v[key]
            touched += 1
        Path(path).write_text(json.dumps(db, ensure_ascii=False, indent=1) + "\n",
                              encoding="utf-8", newline="\n")
        print(f"寫入 {touched} 案 → {path}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
