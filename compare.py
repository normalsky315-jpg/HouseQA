"""HouseQA 進入點。

僅作為薄薄的入口層，實際邏輯位於 :mod:`app.cli`，符合「compare.py 只當入口」
的設計要求。

用法：
    python compare.py            # 比對全部建案
    python compare.py --help     # 查看所有參數
"""

from __future__ import annotations

import sys

from app.cli import main

if __name__ == "__main__":
    sys.exit(main())
