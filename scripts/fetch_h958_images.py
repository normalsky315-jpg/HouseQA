"""下載 house958 案頁「相關圖面」到 KHHouse repo，並回填 floorPlans。

house958 是 http 站，GitHub Pages（https）無法直接外連其圖片（混合內容會被
瀏覽器擋），故把圖抓進 repo 用相對路徑引用。

使用方式：
  python scripts/fetch_h958_images.py --district 仁武
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import quote, urljoin

KHHOUSE = Path(r"C:\Users\mrsky\Documents\GITHUB\KHHouse")

_UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/137.0"}


def safe_dirname(name: str) -> str:
    """案名轉資料夾名（去掉檔案系統不允許的字元）。"""
    return re.sub(r'[\\/:*?"<>|]', "_", name)


def case_images(html: str, base_url: str) -> list[str]:
    """取出案頁中的建案圖面網址（house958 的 images/ 路徑）。"""
    urls = []
    for src in re.findall(r'<img[^>]+src="([^"]+)"', html):
        if "images/" not in src:
            continue  # 版面裝飾圖
        urls.append(urljoin(base_url, src))
    return list(dict.fromkeys(urls))


def main() -> None:
    parser = argparse.ArgumentParser(description="下載 house958 圖面進 KHHouse")
    parser.add_argument("--district", required=True)
    parser.add_argument("--subdir", default="", help="img/ 下的子資料夾名（預設用行政區）")
    args = parser.parse_args()

    import requests

    subdir = args.subdir or args.district
    data_path = KHHOUSE / "data.json"
    db = json.loads(data_path.read_text(encoding="utf-8"))

    total_bytes = 0
    for p in db["projects"]:
        if p.get("district") != args.district or not p.get("s958"):
            continue
        if p.get("floorPlans"):
            print(f"－ {p['name']}：floorPlans 已有值，跳過")
            continue
        try:
            r = requests.get(p["s958"], headers=_UA, timeout=30)
            r.raise_for_status()
            r.encoding = r.apparent_encoding or "utf-8"
        except Exception as exc:  # noqa: BLE001
            print(f"⚠ {p['name']}：案頁抓取失敗（{exc}）")
            continue
        urls = case_images(r.text, p["s958"])
        if not urls:
            print(f"－ {p['name']}：案頁無圖")
            continue
        folder = KHHOUSE / "img" / subdir / safe_dirname(p["name"])
        folder.mkdir(parents=True, exist_ok=True)
        rels = []
        for u in urls:
            fname = safe_dirname(u.rsplit("/", 1)[-1])
            dest = folder / fname
            if not dest.exists():
                try:
                    # 中文路徑需 URL 編碼
                    enc = quote(u, safe=":/")
                    ir = requests.get(enc, headers=_UA, timeout=30)
                    ir.raise_for_status()
                    dest.write_bytes(ir.content)
                    time.sleep(0.25)
                except Exception as exc:  # noqa: BLE001
                    print(f"    ⚠ 圖片失敗 {fname}：{exc}")
                    continue
            total_bytes += dest.stat().st_size
            rels.append(f"img/{subdir}/{folder.name}/{fname}")
        p["floorPlans"] = rels
        print(f"✓ {p['name']}：{len(rels)} 張")

    data_path.write_text(json.dumps(db, ensure_ascii=False, indent=1) + "\n",
                         encoding="utf-8", newline="\n")
    print(f"完成，共 {total_bytes/1024/1024:.1f} MB → {data_path}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
