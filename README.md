# HouseQA

> Real Estate Data Quality Assurance System

HouseQA 是一套**自動化 QA 系統**，用來驗證 NKUinfos 的建案資料（`data/data.json`）與 [591 新建案](https://newhouse.591.com.tw/) 官網是否一致。

```
data.json ──► 逐筆讀取 ──► 依 s591 抓取 591 ──► 解析 ──► 正規化 ──► 逐欄比對 ──► HTML / Excel / JSON 報表
```

## 特色

- **多來源交叉比對**：同時與多個來源（591、house958…）比對，**只要任一來源吻合即判 PASS**，報告分欄顯示每個來源的值，避免被單一來源誤判。
- **外掛式架構（Plugin）**：Fetcher / Parser / Normalizer / Reporter / Source 皆可獨立擴充。新增資料來源（樂居、建商官網、Google Maps、實價登錄……）**不需修改 Compare Engine**。
- **Compare Engine 與來源解耦**：引擎只認得中立的 `SourceRecord`，任何來源產出此模型即可納入比對。
- **比對規則可設定**：`config.yaml` 中可為每個欄位指定 `exact` / `contains` / `contains_all` / `tolerance`（含誤差容忍度），門檻不寫死於程式。
- **正規化引擎**：品牌字典（`TOTO衛浴`→`TOTO`）、地址（去縣市區）、樓層（`地上20層,地下3層`→`20F/B3`）、面積、格局、建照等。
- **容錯解析**：591 解析器以「標籤文字」為錨點而非固定 CSS selector，對 591 改版具相當容錯能力。
- **快取 / 重試 / 逾時 / Logging**：HTML 依 URL hash 快取（預設 7 天），下載失敗自動重試，全程寫入 `logs/houseqa.log`。
- **完整測試**：`pytest` 涵蓋正規化、規則、解析器、比對引擎。

## 安裝

需要 Python 3.13+。

```bash
pip install -r requirements.txt
playwright install chromium      # 首次使用需安裝瀏覽器核心
```

## 使用

```bash
python compare.py                  # 比對全部建案，輸出預設報表（html + excel）
python compare.py --all            # 同上
python compare.py --project 139790 # 只比對指定建案編號
python compare.py --update         # 忽略快取強制重新下載（等同 --force-download）
python compare.py --report html    # 指定報表格式（可重複：--report html --report excel）
python compare.py --report json
python compare.py --cache-only     # 只用快取、不連線（離線即可產生報表）
python compare.py --cache-clear    # 清除所有快取後結束
python compare.py --data github    # data.json 來源（github / local / URL / 路徑）
python compare.py --data local
python compare.py --help           # 查看完整參數
```

### data.json 來源

預設從 NKUinfos 的 GitHub 倉庫**即時抓取最新資料**：
`https://raw.githubusercontent.com/normalsky315-jpg/NKUinfos/main/data.json`

抓取失敗（離線、GitHub 暫時無法存取）時，會**自動退回本地 `data/data.json`**。
可在 `config.yaml` 的 `data:` 區段調整 owner / repo / branch，或用 `--data` 覆寫：
`--data github`（線上）、`--data local`（本地）、`--data <URL>`、`--data <檔案路徑>`。

報表輸出於 `reports/`：

- `report.html` — 每個建案一個區塊，逐欄顯示 HouseQA 值、591 值與 PASS（綠）／WARNING（黃）／FAIL（紅）。
- `report.xlsx` — 每列一個建案、每欄一個欄位，儲存格依狀態著色，附數值與說明註解。
- `report.json` — 結構化結果，供後續程式化處理。

## 比對來源

目前支援的來源（於 `config.yaml` 的 `sources:` 啟用／停用）：

| 來源 | 網站 | 每案網址如何決定 |
|---|---|---|
| `591` | 591 新建案 | data.json 的 `s591` |
| `house958` | house958.com（2026高雄推案分析） | 自動以建案名稱比對索引頁；可在 data.json 用 `s958` 手動覆寫 |
| `leju` | 樂居 leju.com.tw | data.json 的 `sleju`（社區網址為亂碼 ID，需手動指定） |

新增來源（例如建商官網）只要在 `app/sources.py` 加一個 `SourceAdapter`，並在 `config.yaml` 的 `sources:` 加上名稱即可——比對引擎與報表都不需更動。

## 比對的欄位

名稱、建商、基地位置、樓層、棟數、戶數、車位、格局、基地面積、公設比、建蔽率、建照、交屋時間、貸款成數、廚具、衛浴、建材。

## 專案結構

```
HouseQA/
├── compare.py                # 入口（僅呼叫 app.cli）
├── config.yaml               # 所有執行期設定與比對規則
├── data/data.json            # NKUinfos 匯出的建案資料
├── app/
│   ├── cli.py                # 命令列介面
│   ├── pipeline.py           # 主流程編排（串接各來源與報表）
│   ├── sources.py            # 來源轉接器：591 / house958（含名稱自動比對）
│   ├── config.py             # 設定載入
│   ├── models/               # Project / SourceRecord / DiffResult 資料模型
│   ├── io/                   # data.json 載入（本地／GitHub）與映射
│   ├── fetchers/             # base / cache / site591 / house958 / leju
│   ├── parsers/              # base / parser591 / parser_house958 / parser_leju
│   ├── normalize/            # brand / address / area / floor / text
│   ├── compare/              # rules（可設定）/ fields（欄位註冊）/ engine（解耦）
│   ├── reports/              # html / excel / json reporter
│   └── utils/                # logger / timer
├── tests/                    # pytest 測試
├── cache/  logs/  reports/   # 執行期產物
└── requirements.txt
```

## 如何擴充

新增一個資料來源（例如「樂居」）只需，且**完全不動 Compare Engine**：

1. 在 `app/fetchers/` 新增 `LejuFetcher(Fetcher)`，實作 `can_handle` 與 `fetch`。
2. 在 `app/parsers/` 新增 `ParserLeju(Parser)`，把 HTML 解析成 `SourceRecord`（沿用 `app/compare/fields.py` 的標準欄位 key）。
3. 在 `app/sources.py` 的 `build_source_adapters` 加一個 `SourceAdapter`（含 URL 對應方式）。
4. 在 `config.yaml` 的 `sources:` 加上 `leju`。

新增比對規則型別：在 `app/compare/rules.py` 新增 `Rule` 子類別並 `RuleFactory.register(...)`，即可於 `config.yaml` 使用。

## 規劃中的資料來源

591（已完成）、house958（已完成）、樂居（已完成）、建商官網、Google Maps、政府公開資料、建照／使照、實價登錄、NKUinfos Admin API、AI 自動分析。

## 開發與品質

```bash
pip install -e ".[dev,ai]"   # 安裝開發相依（ruff / mypy / pytest / pre-commit）
pre-commit install            # 啟用提交前自動檢查（可選）

ruff check app tests          # 程式風格檢查
mypy app                      # 型別檢查
pytest                        # 單元測試
```

或一次跑完：`make check`（lint + typecheck + test）。

- **CI**：`.github/workflows/ci.yml`——push / PR 到 `main`、`dev` 時自動跑 ruff + mypy + pytest。
- **型別**：全專案通過 `mypy`（嚴格度適中）。
- **容器化**：`Dockerfile` 以官方 Playwright 映像為基底，`docker build -t houseqa . && docker run --rm houseqa --all`。
- **環境變數**：見 `.env.example`（未來 AI 分析用的 API key 等）。

## License

MIT
