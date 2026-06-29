# 使用官方 Playwright Python 映像（已內建 Chromium 與系統相依套件）。
FROM mcr.microsoft.com/playwright/python:v1.49.0-jammy

WORKDIR /app

# 先裝相依套件以善用 Docker 快取層
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 複製專案
COPY . .

# 預設執行完整比對
ENTRYPOINT ["python", "compare.py"]
CMD ["--all"]
