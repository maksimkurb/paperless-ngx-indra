"""Split lines at fill-in underlines and read each part on its own.

On forms a printed label is followed by a long underline with handwriting on it
(``Потребитель ______``). Indra recognises the line as a whole, and the handwriting
spoils the reading of the printed label next to it. Cutting the line where a long
underline starts and ends, and reading the parts separately, keeps them apart.

``INDRA_SPLIT_FIELDS=0`` switches this off.
"""

from __future__ import annotations

import os
from collections.abc import Callable

import numpy as np

# an underline must be at least this many line heights long (short ones underline words)
_MIN_UNDERLINE = 2.5
_MAX_THICKNESS = 0.25  # of the line height
_PAD = 6


def enabled() -> bool:
    return os.environ.get("INDRA_SPLIT_FIELDS", "1").strip().lower() not in ("0", "off", "false")


def find_underlines(gray: np.ndarray, box: list[float]) -> list[tuple[int, int]]:
    """Return (start, end) x positions, in image pixels, of long underlines in ``box``."""
    import cv2

    x0, y0, x1, y1 = (round(v) for v in box)
    crop = gray[max(y0, 0) : y1, max(x0, 0) : x1]
    height = y1 - y0
    if crop.size == 0 or height < 8 or crop.shape[1] < 3 * height:
        return []
    ink = cv2.adaptiveThreshold(
        crop, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY_INV, 31, 15
    )
    min_len = max(int(height * _MIN_UNDERLINE), 40)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (min_len, 1))
    horizontal = cv2.morphologyEx(ink, cv2.MORPH_OPEN, kernel)
    count, _, stats, _ = cv2.connectedComponentsWithStats(horizontal)
    found = []
    for i in range(1, count):
        left, _, width, thick, _ = stats[i]
        if width >= min_len and thick <= max(height * _MAX_THICKNESS, 3):
            found.append((max(x0, 0) + int(left), max(x0, 0) + int(left + width)))
    return sorted(found)


def _print_intervals(
    box: list[float], underlines: list[tuple[int, int]]
) -> list[tuple[float, float]]:
    """The stretches of ``box`` outside the underlines: printed labels."""
    x0, y0, x1, y1 = box
    min_width = (y1 - y0) * 1.5
    out = []
    pos = x0
    for start, end in underlines:
        if start - pos >= min_width:
            out.append((pos, float(start)))
        pos = max(pos, float(end))
    if x1 - pos >= min_width:
        out.append((pos, x1))
    return out


def read_segments(
    gray: np.ndarray,
    lines: list,
    recognise: Callable[[np.ndarray], list],
) -> list:
    """Re-read the printed labels of lines that carry fill-in underlines.

    A line is kept as one line. Words that sit left of an underline (or right of the last
    one) are replaced by a separate reading of that stretch; the words over an underline
    (the handwriting) keep their original reading, because short crops read handwriting
    worse than the full line does.
    """
    for line in lines:
        words = line.text.split()
        if not words:
            continue
        underlines = find_underlines(gray, line.box)
        intervals = _print_intervals(line.box, underlines) if underlines else []
        if not intervals:
            continue
        x0, y0, x1, y1 = line.box
        total = sum(len(w) for w in words) + len(words) - 1
        unit = (x1 - x0) / total
        centers, pos = [], 0
        for w in words:
            centers.append(x0 + (pos + len(w) / 2) * unit)
            pos += len(w) + 1
        replacement: dict[int, str] = {}
        for a, b in intervals:
            members = [i for i, c in enumerate(centers) if a <= c < b]
            ya, yb = max(int(y0) - _PAD, 0), min(int(y1) + _PAD, gray.shape[0])
            xa, xb = max(int(a) - _PAD, 0), min(int(b) + _PAD, gray.shape[1])
            crop = gray[ya:yb, xa:xb]
            if not members or crop.size == 0:
                continue
            padded = np.pad(crop, _PAD * 4, constant_values=255)
            text = " ".join(r.text.strip() for r in recognise(padded) if r.text.strip())
            if text:
                replacement[members[0]] = text
                for i in members[1:]:
                    replacement[i] = ""
        if replacement:
            line.text = " ".join(
                t for t in (replacement.get(i, w) for i, w in enumerate(words)) if t
            )
    return lines
