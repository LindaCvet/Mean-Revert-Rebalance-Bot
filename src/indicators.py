from __future__ import annotations
from typing import List, Optional
import numpy as np

def ma(values: List[float], n: int) -> List[Optional[float]]:
    arr = np.array(values, dtype=float)
    if len(arr) < n:
        return [None] * len(arr)
    kernel = np.ones(n) / n
    m = np.convolve(arr, kernel, mode="valid")
    pad = [None] * (n - 1)
    return pad + list(m)

def rolling_std(values: List[float], n: int) -> List[Optional[float]]:
    arr = np.array(values, dtype=float)
    out: List[Optional[float]] = []
    for i in range(len(arr)):
        if i + 1 < n:
            out.append(None)
        else:
            window = arr[i + 1 - n : i + 1]
            out.append(float(np.std(window, ddof=0)))
    return out

def last_valid(seq: List[Optional[float]]) -> Optional[float]:
    for x in reversed(seq):
        if x is not None:
            return x
    return None

def pct_change(values: List[float], lookback: int) -> Optional[float]:
    if len(values) <= lookback:
        return None
    curr = values[-1]
    prev = values[-1 - lookback]
    if prev == 0:
        return None
    return 100.0 * (curr / prev - 1.0)

def zscore_last(values: List[float], n: int) -> Optional[float]:
    if len(values) < n:
        return None
    window = values[-n:]
    mu = float(np.mean(window))
    sd = float(np.std(window, ddof=0))
    if sd == 0:
        return 0.0
    return (values[-1] - mu) / sd
