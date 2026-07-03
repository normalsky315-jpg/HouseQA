"""用 house958 案頁的「獨有欄位」豐富 data.json 建案內容。

591／樂居沒有、958 有的資料：公設規劃、管理費用、總銷金額、基地面積、
都計分區、營造公司（施工單位）、車位開價、工程進度。

寫入方式：
- 公設規劃 → amenities["公設"]（清單）
- 其餘 → notes（結構化短句，僅在 notes 尚未包含該資訊時追加）

使用方式：
  python scripts/enrich_from_h958.py --district 仁武 [--data path]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

_UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/137.0"}


def fetch_raw(url: str) -> dict:
    import requests

    from app.parsers.parser_house958 import ParserHouse958

    r = requests.get(url, headers=_UA, timeout=30)
    r.raise_for_status()
    r.encoding = r.apparent_encoding or "utf-8"
    return ParserHouse958().parse(r.text, url=url).raw


def clean(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "")).strip()


def main() -> None:
    parser = argparse.ArgumentParser(description="以 house958 獨有欄位豐富建案內容")
    parser.add_argument("--district", required=True)
    parser.add_argument("--data", default=r"C:\Users\mrsky\Documents\GITHUB\KHHouse\data.json")
    args = parser.parse_args()

    path = Path(args.data)
    db = json.loads(path.read_text(encoding="utf-8"))
    updated = 0
    for p in db["projects"]:
        if p.get("district") != args.district or not p.get("s958"):
            continue
        try:
            raw = fetch_raw(p["s958"])
        except Exception as exc:  # noqa: BLE001 - 單案失敗不中斷
            print(f"⚠ {p['name']}：{exc}")
            continue
        changes = []

        # 公設規劃 → amenities
        facilities = [x for x in re.split(r"[、,，/；;\s]+", clean(raw.get("公設規劃", "")))
                      if x and x not in ("無", "-")]
        if facilities and not (p.get("amenities") or {}).get("公設"):
            p.setdefault("amenities", {})["公設"] = facilities
            changes.append(f"公設×{len(facilities)}")

        # 其他獨有資訊 → notes 追加
        note_bits = []
        mapping = [
            ("管理費用", "管理費 {}"),
            ("總銷金額", "總銷 {}"),
            ("基地面積", "基地 {}"),
            ("都計分區", "都計 {}"),
            ("營造公司", "營造：{}"),
            ("施工單位", "營造：{}"),
            ("車位開價", "車位開價 {}"),
            ("行銷企劃", "企劃：{}"),
        ]
        notes = p.get("notes") or ""
        for key, fmt in mapping:
            val = clean(raw.get(key, ""))
            if val and val not in ("無", "-", "元/位/月", "坪") and val not in notes:
                note_bits.append(fmt.format(val))
        if note_bits:
            p["notes"] = (notes + ("；" if notes else "") + "；".join(note_bits)).strip("；")
            changes.append(f"notes+{len(note_bits)}")

        if changes:
            updated += 1
            print(f"✓ {p['name']}：{'、'.join(changes)}")
        time.sleep(0.3)

    path.write_text(json.dumps(db, ensure_ascii=False, indent=1) + "\n",
                    encoding="utf-8", newline="\n")
    print(f"完成：更新 {updated} 案 → {path}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
