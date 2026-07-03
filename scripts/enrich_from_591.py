"""用 591 詳情頁補齊 data.json 建案欄位（建材、建照、交屋、貸款）。

政策：
- kit / bath / other：以 591「建材說明」為準（使用者指定 591 為建材參考來源），
  既有值為空才整批寫入；已有值則跳過不覆蓋。
- permit / handover / loan / status：只在目前為空時填入。
- 其他欄位（dev / floor / addr…）不動，留給 QA 比對。

使用方式：
  python scripts/enrich_from_591.py --district 仁武
  python scripts/enrich_from_591.py --district 仁武 --data path\to\data.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

_KIT_KW = ("廚", "三機", "烘碗", "瓦斯爐", "排油煙")
_BATH_KW = ("衛浴", "馬桶", "龍頭", "免治", "面盆", "浴缸", "淋浴", "暖風")


def split_materials(text: str) -> tuple[list[str], list[str], list[str]]:
    """把 591 建材說明文字拆成 kit / bath / other 三籃。"""
    kit: list[str] = []
    bath: list[str] = []
    other: list[str] = []
    for tok in re.split(r"[、,，;；/。\n]+", text or ""):
        tok = tok.strip()
        if not tok or len(tok) > 24:
            continue
        if any(k in tok for k in _KIT_KW):
            kit.append(tok)
        elif any(k in tok for k in _BATH_KW):
            bath.append(tok)
        else:
            other.append(tok)
    return kit[:6], bath[:6], other[:10]


def main() -> None:
    parser = argparse.ArgumentParser(description="以 591 詳情頁補齊建案欄位")
    parser.add_argument("--district", required=True)
    parser.add_argument("--data", default=r"C:\Users\mrsky\Documents\GITHUB\KHHouse\data.json")
    parser.add_argument("--force", action="store_true", help="忽略快取重抓")
    parser.add_argument("--overwrite", action="store_true",
                        help="建材/狀態以 591 覆蓋既有值（用於自動建檔的底稿）")
    args = parser.parse_args()

    from app.config import Config
    from app.fetchers.cache import HtmlCache
    from app.fetchers.site591 import Site591Fetcher
    from app.parsers.parser591 import Parser591

    config = Config.load("config.yaml")
    fetcher = Site591Fetcher(config.fetch, HtmlCache("cache", days=7))
    p591 = Parser591()

    path = Path(args.data)
    db = json.loads(path.read_text(encoding="utf-8"))
    updated = 0
    for p in db["projects"]:
        if p.get("district") != args.district or not p.get("s591"):
            continue
        if "newhouse.591.com.tw" not in p["s591"]:
            continue
        try:
            html = fetcher.fetch(p["s591"], force_download=args.force)
            rec = p591.parse(html, url=p["s591"])
        except Exception as exc:  # noqa: BLE001 - 單案失敗不中斷
            print(f"⚠ {p['name']}：抓取/解析失敗（{exc}）")
            continue
        f = rec.fields
        changes = []
        materials = f.get("materials", "")
        if materials and (args.overwrite or (not p.get("kit") and not p.get("bath"))):
            kit, bath, other = split_materials(materials)
            if kit:
                p["kit"] = kit
                changes.append(f"kit×{len(kit)}")
            if bath:
                p["bath"] = bath
                changes.append(f"bath×{len(bath)}")
            if other and (args.overwrite or not p.get("other")):
                p["other"] = other
                changes.append(f"other×{len(other)}")
        for src_key, dst_key in [("permit", "permit"), ("handover", "handover"),
                                 ("loan", "loan"), ("status", "status")]:
            val = (f.get(src_key) or "").strip()
            overwrite_ok = args.overwrite and dst_key == "status"
            if val and (overwrite_ok or not (p.get(dst_key) or "").strip()):
                if p.get(dst_key) != val:
                    p[dst_key] = val
                    changes.append(f"{dst_key}={val[:18]}")
        if changes:
            updated += 1
            print(f"✓ {p['name']}：{'、'.join(changes)}")
        else:
            print(f"－ {p['name']}：無可補（591 資料空或欄位已有值）")

    path.write_text(json.dumps(db, ensure_ascii=False, indent=1) + "\n",
                    encoding="utf-8", newline="\n")
    print(f"完成：更新 {updated} 案 → {path}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
