"""簡易計時工具。"""

from __future__ import annotations

import time
from types import TracebackType


class Timer:
    """量測一段程式碼耗時的 context manager。

    Example:
        >>> with Timer() as t:
        ...     do_work()
        >>> print(t.elapsed)
    """

    def __init__(self) -> None:
        self._start: float = 0.0
        self._end: float = 0.0

    def __enter__(self) -> Timer:
        self._start = time.perf_counter()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self._end = time.perf_counter()

    @property
    def elapsed(self) -> float:
        """已耗費的秒數。"""
        end = self._end or time.perf_counter()
        return end - self._start
