"""抓取 591 新建案「行政區清單」（BFF API），產出建案清單 JSON。

用途：擴張新行政區時，先用本腳本撈出該區所有「在線」建案（名稱、591 網址、
價格、坪數、房型、標籤、地址），作為建立 data.json 的底稿。

資料來源為 591 的 bff-newhouse API（list-search）。因該 API 擋非瀏覽器流量，
故透過 Playwright 在頁面情境內呼叫。``status == 2`` 為在線建案、``3`` 為下架。

高雄市 regionid=17，九個重點行政區的 sectionid 對照：
  楠梓 251、仁武 254、左營 253、鼓山 247、三民 250、
  新興 243、前金 244、苓雅 245、鳳山 268

使用方式：
  python scripts/fetch_591_district.py 楠梓 仁武
  python scripts/fetch_591_district.py --all-status --out reports/tier1_591.json 楠梓 仁武
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REGION_KHH = 17
SECTION_IDS = {
    "楠梓": 251,
    "仁武": 254,
    "左營": 253,
    "鼓山": 247,
    "三民": 250,
    "新興": 243,
    "前金": 244,
    "苓雅": 245,
    "鳳山": 268,
}

STATUS_ONLINE = 2

# sale_status 觀察值：1=預推/待定居多、2=銷售中、3=完銷（供參考，非官方文件）
SALE_STATUS_LABEL = {0: "未知", 1: "預推", 2: "銷售中", 3: "完銷"}


def _pick(it: dict) -> dict:
    """從 API 單筆項目挑出建檔需要的欄位。"""
    return {
        "hid": it.get("hid"),
        "url": f"https://newhouse.591.com.tw/{it.get('hid')}",
        "name": it.get("build_name", ""),
        "district": (it.get("section") or "").removesuffix("區"),
        "addr": it.get("addr_number", ""),
        "address": it.get("address", ""),
        "price": it.get("price", ""),
        "price_unit": it.get("price_unit", ""),
        "pending": it.get("pending"),
        "area": it.get("area", ""),
        "room": it.get("room", ""),
        "purpose": it.get("purpose_str", ""),
        "tags": it.get("tag", []),
        "status": it.get("status"),
        "sale_status": it.get("sale_status"),
        "sale_status_label": SALE_STATUS_LABEL.get(it.get("sale_status"), "未知"),
        "updatetime": it.get("updatetime", ""),
    }


def fetch_district(page, district: str, online_only: bool = True) -> list[dict]:
    """抓取單一行政區的建案清單（自動翻完所有 API 分頁）。"""
    sid = SECTION_IDS[district]
    items: dict[int, dict] = {}
    page_no = 1
    total_page = 1
    online_total = None
    while page_no <= total_page:
        data = page.evaluate(
            "url => fetch(url).then(r => r.json())",
            f"https://bff-newhouse.591.com.tw/v1/list-search?page={page_no}"
            f"&device=pc&regionid={REGION_KHH}&sectionid={sid}",
        )["data"]
        total_page = data.get("total_page", 1)
        online_total = data.get("online_total")
        for it in data.get("items", []):
            hid = it.get("hid")
            if not hid or not it.get("build_name"):
                continue  # 廣告或推薦雜項
            if online_only and it.get("status") != STATUS_ONLINE:
                continue
            items[hid] = _pick(it)
        page_no += 1
        page.wait_for_timeout(800)
    print(f"  {district}：在線 {online_total} 筆，取得 {len(items)} 筆")
    return list(items.values())


def main() -> None:
    parser = argparse.ArgumentParser(description="抓取 591 行政區建案清單")
    parser.add_argument("districts", nargs="+", choices=sorted(SECTION_IDS))
    parser.add_argument("--out", default="reports/591_district_list.json")
    parser.add_argument(
        "--all-status", action="store_true", help="含已下架建案（預設僅在線）"
    )
    args = parser.parse_args()

    from playwright.sync_api import sync_playwright

    result: dict[str, list[dict]] = {}
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1400, "height": 900})
        # 先載入一次列表頁，取得呼叫 API 所需的頁面情境（cookie 等）
        page.goto(f"https://newhouse.591.com.tw/list?regionid={REGION_KHH}", timeout=60000)
        page.wait_for_timeout(5000)
        for district in args.districts:
            print(f"抓取 {district}區 …")
            result[district] = fetch_district(page, district, online_only=not args.all_status)
        browser.close()

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"已輸出：{out}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
