"""Text helpers: accent/case folding with offset mapping, slugs."""
import re
import unicodedata


def fold_with_map(s: str):
    """Return (folded, index_map): folded text without accents/case, and for each
    folded char the index of the original char it came from."""
    out, idx = [], []
    for i, ch in enumerate(s):
        for c in unicodedata.normalize("NFKD", ch):
            if unicodedata.combining(c):
                continue
            for f in c.casefold():
                out.append(f)
                idx.append(i)
    return "".join(out), idx


def fold(s: str) -> str:
    return fold_with_map(s)[0]


def slugify(s: str, default: str = "untitled") -> str:
    s = fold(s or "")
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return (s or default)[:80]
