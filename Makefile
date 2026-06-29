# HouseQA 常用指令
# 用法：make <target>（Windows 可改用 README 中對應的 python 指令）

.PHONY: install install-dev playwright test lint typecheck check run report clean

install:          ## 安裝執行期相依套件
	pip install -r requirements.txt

install-dev:      ## 安裝開發相依（ruff/mypy/pytest/pre-commit）
	pip install -e ".[dev,ai]"

playwright:       ## 安裝 Playwright 瀏覽器核心
	playwright install chromium

test:             ## 執行測試
	pytest

lint:             ## 程式風格檢查
	ruff check app tests

typecheck:        ## 型別檢查
	mypy app

check: lint typecheck test  ## 一次跑完 lint + typecheck + test

run:              ## 比對全部建案並產生報表
	python compare.py --all

report:           ## 只用快取重新產生報表（不連網）
	python compare.py --all --cache-only

clean:            ## 清除快取與報表產物
	python compare.py --cache-clear
