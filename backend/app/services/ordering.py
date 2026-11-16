from ..domain import STEP


def position_between(prev, nxt):
    """Integer position strictly between two neighbours, or None if the gap is exhausted
    (caller must renumber the siblings)."""
    if prev is None and nxt is None:
        return STEP
    if prev is None:
        return nxt - STEP
    if nxt is None:
        return prev + STEP
    mid = (prev + nxt) // 2
    return mid if prev < mid < nxt else None
