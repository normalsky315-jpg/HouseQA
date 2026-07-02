# 交接說明：高雄重點行政區建案網站（給新的 Claude session）

> 把這整份貼給新的 Claude，或叫它先讀這個檔案。以下是零背景也能接手的完整脈絡。

---

## 0. 使用者是誰（很重要）

- **非技術背景**、講中文，請一律用**繁體中文**回覆，步驟要細、白話，不要假設他懂術語。
- 他有一個既有網站 **NKUinfos**（高大特區房產儀表板）和一套 QA 工具 **HouseQA**。
- 安全守則：**絕對不要叫他把 API 金鑰貼到對話框**，要引導他寫進本地 `.env` 檔。

---

## 1. 任務目標

做**第二個網站**：涵蓋高雄市 9 個重點行政區的**建案資訊網站**，定位＝
**「沿用 NKUinfos 的前台呈現 ＋ 用 HouseQA 在背後做資料品質把關(QA)」**。

### 9 個行政區（使用者指定）與分批
| 批次 | 行政區 | 定位 |
|---|---|---|
| Tier 1 | 楠梓、仁武 | 北高雄·橋科帶（NKUinfos 已覆蓋楠梓高大特區）|
| Tier 2 | 左營、鼓山、三民 | 市中心精華 |
| Tier 3 | 新興、前金、苓雅 | 舊核心＋亞洲新灣區 |
| Tier 4 | 鳳山 | 東高雄新市鎮 |

完整規劃在 `高雄重點行政區建案網站_專案規劃.md`（HouseQA 專案根目錄）——**新 session 請先讀那份**。

---

## 2. 既有資產（可直接沿用）

### NKUinfos（前台網站）
- GitHub：`https://github.com/normalsky315-jpg/NKUinfos`
- 架構：**靜態 `data.json` ＋ 前端 HTML/JS 儀表板**，部署在 GitHub Pages。
- 內容：目前聚焦楠梓高大特區，20 筆建案。

### HouseQA（本專案，資料 QA 工具）
- 路徑：`C:\Users\mrsky\Documents\HouseQA`
- 語言：Python 3.13（`pip install -r requirements.txt` + `playwright install chromium`）
- 功能：讀 `data.json` → 抓 591/house958/樂居 → 解析正規化 → **多來源比對** → 產 HTML/Excel/JSON 報表 ＋ **AI 差異分析**。
- 常用指令：
  ```bash
  python compare.py --ai --data local          # 完整跑（含 AI，需金鑰）
  python compare.py --cache-only --data local   # 離線用快取跑（省時省錢）
  python compare.py --report json               # 產結構化報表方便程式讀
  ```
- AI 分析：用 Anthropic Claude（`claude-opus-4-8`），金鑰放 `.env` 的 `ANTHROPIC_API_KEY`，CLI 會自動載入；沒金鑰就優雅略過。

---

## 3. 資料模型 data.json（沿用，建議加 district）

每個建案一筆，主要欄位：

| 欄位 | 意義 |
|---|---|
| `name` / `dev` / `addr` | 名稱 / 建商 / 基地位置 |
| `district` | **行政區（新網站建議新增，多區篩選用）** |
| `permit` / `floor` | 建照 / 樓層（例 `15F/B2`）|
| `units`/`count` / `layout` | 戶數 / 格局（含棟數、車位描述）|
| `avgPrice`/`minPrice`/`maxPrice` | 實價登錄價格 |
| `loan` / `handover` | 貸款成數 / 交屋時間（例 `2026Q4`）|
| `kit` / `bath` | 廚具 / 衛浴品牌 |
| `other` | 特色配備（自寫賣點，**不納入 QA 比對**）|
| `lat` / `lng` | 座標（地圖）|
| `s591` / `sleju` / `s958` | 各來源網址（HouseQA 比對用）|
| `notes` / `analysis` | 補充 / 分析 |

> data.json 用**單一空格縮排**、`ensure_ascii=False`（中文不轉義）。編輯時沿用此格式以免產生無謂 diff。

---

## 4. 核心原則（務必遵守，使用者很在意）

1. **多來源交叉比對**：一個欄位**只要任一來源吻合就 PASS**。FAIL 只代表「所有來源都不一致」，**不代表使用者錯**。
2. **QA 只標記、不自動改**：591 / 各來源**不一定對**，使用者的 `data.json` 常是他手動修正過的正確值。任何改動都要**逐項經他確認**。
3. **FAIL 分三類**：格式差異（其實相同，不用改）／真實出入（要查證才改）／時間類。
4. `other`（特色配備）、價格、analysis **刻意不比對**。

---

## 5. 目前狀態與待辦

- 剛完成：對既有 20 筆跑過 AI 分析（9 FAIL，多數是格式差異）。
- 已改（僅本地 `data/data.json`，已備份 `data/data.json.bak`）：
  - 高大之森 交屋 `2026Q3→2026Q4`、吉隆森淼 交屋 `2026Q4→2027Q3`
  - ⚠️ **尚未同步到 GitHub 的 NKUinfos**——真正生效要去 NKUinfos repo 改同樣兩行。
- 新網站尚未動工。

### 建議第一步（新 session 可直接做）
1. 讀規劃 MD，跟使用者確認要先做哪一區（預設 Tier 1：楠梓、仁武）。
2. 複製 NKUinfos＋HouseQA 成新專案骨架，先跑起來。
3. 開始建該區 `data.json`：從 591 依行政區撈在建/預售建案，逐案填 `district`、`s591`。

---

## 6. 已知地雷

- **樂居 `sleju` 網址是亂碼 ID、無法由名稱推導，只能逐案手動找**（且有 Cloudflare，要用 Playwright headless + 等 6 秒）。這是最花人力的部分。
- **house958** 目前主要涵蓋楠梓，其他區未必有，別當唯一依據。
- **591 解析**：資料在 DOM 的 `li>span+p`（非 `__NUXT__`），HouseQA 用「標籤文字錨點」解析，對改版有容錯。
- 跨區之後建案變多、FAIL 會變多，守住「多來源佐證＋人工決定」原則。

---

## 7. 給新 session 的開場白（使用者可直接複製這段）

> 我要做一個「高雄重點行政區建案資訊網站」，沿用我既有的 NKUinfos（前台）＋ HouseQA（資料 QA）。專案在 `C:\Users\mrsky\Documents\HouseQA`，請先讀 `交接說明_給新Session.md` 和 `高雄重點行政區建案網站_專案規劃.md`，然後幫我從 Tier 1（楠梓、仁武）開始。我不是工程師，請用繁體中文、一步一步帶我。
