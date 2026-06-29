"""模組式進入點，等同 ``python compare.py``。

用法：
    python -m app.main [參數同 compare.py]
"""

from __future__ import annotations

import sys

from app.cli import main

if __name__ == "__main__":
    sys.exit(main())
