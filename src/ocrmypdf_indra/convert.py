"""Convert an Indra ``Page`` into an OCRmyPDF ``OcrElement`` tree.

Indra recognises whole lines, but OCRmyPDF's renderer only draws word elements, so each
line is split into words and the line box is shared out in proportion to the number of
characters in each word.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from ocrmypdf.hocrtransform import BoundingBox, OcrClass, OcrElement

from .scripts import fix_page

_LINE_CLASS = {
    "Page-Header": OcrClass.HEADER,
    "Page-Footer": OcrClass.FOOTER,
    "Caption": OcrClass.CAPTION,
}


def _is_rtl(text: str) -> bool:
    strong = [unicodedata.bidirectional(c) for c in text if c.isalpha()]
    if not strong:
        return False
    return sum(b in ("R", "AL") for b in strong) * 2 > len(strong)


def to_input_frame(box: list[float], quarter_turns: int, upright_wh: tuple[int, int]):
    """Map a box from Indra's upright page back onto the image that was passed in.

    Indra undoes ``quarter_turns`` counter-clockwise turns of the input by rotating the
    page clockwise; this applies the inverse (counter-clockwise turns) to a box.
    """
    x0, y0, x1, y1 = box
    w, h = upright_wh
    for _ in range(quarter_turns % 4):
        # one counter-clockwise quarter turn of a w x h page: (x, y) -> (y, w - x)
        x0, y0, x1, y1 = y0, w - x1, y1, w - x0
        w, h = h, w
    return [x0, y0, x1, y1]


def split_words(text: str, box: list[float], rtl: bool = False) -> list[OcrElement]:
    """Split a line into word elements with boxes proportional to character counts."""
    words = text.split()
    if not words:
        return []
    x0, y0, x1, y1 = box
    # a space counts as one character so the gaps get a fair share of the width
    total = sum(len(w) for w in words) + (len(words) - 1)
    unit = (x1 - x0) / total
    out = []
    pos = 0
    for w in words:
        a = pos * unit
        b = (pos + len(w)) * unit
        pos += len(w) + 1
        left, right = (x1 - b, x1 - a) if rtl else (x0 + a, x0 + b)
        out.append(
            OcrElement(
                ocr_class=OcrClass.WORD,
                text=w,
                bbox=BoundingBox(left=left, top=y0, right=right, bottom=y1),
            )
        )
    return out


def _block_index(box: list[float], blocks: list[dict[str, Any]]) -> int | None:
    cx, cy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
    for i, b in enumerate(blocks):
        bx0, by0, bx1, by1 = b["bbox"]
        if bx0 <= cx <= bx1 and by0 <= cy <= by1:
            return i
    return None


def page_to_tree(
    page,
    size: tuple[int, int],
    dpi: float,
    page_number: int = 0,
) -> tuple[OcrElement, str]:
    """Build the ``ocr_page`` tree for ``size`` = (width, height) of the input image.

    Returns the tree and the plain text (one line per detected line).
    """
    width, height = size
    quarter_turns = (page.rotation // 90) % 4
    # after the quarter turns are undone the page has the swapped size when odd
    upright = (height, width) if quarter_turns % 2 else (width, height)

    root = OcrElement(
        ocr_class=OcrClass.PAGE,
        bbox=BoundingBox(left=0, top=0, right=width, bottom=height),
        dpi=float(dpi),
        page_number=page_number,
    )
    blocks = [b for b in page.blocks if b.get("bbox")]
    area = OcrElement(
        ocr_class=OcrClass.CAREA, bbox=BoundingBox(left=0, top=0, right=width, bottom=height)
    )
    par: OcrElement | None = None
    par_key: object = object()
    texts = []
    cleaned = [re.sub(r"\s+", " ", line.text).strip() for line in page.lines]
    cleaned = fix_page(cleaned)
    for line, text in zip(page.lines, cleaned, strict=True):
        if not text:
            continue
        box = line.box
        if quarter_turns:
            box = to_input_frame(box, quarter_turns, upright)
        x0 = min(max(box[0], 0), width)
        x1 = min(max(box[2], 0), width)
        y0 = min(max(box[1], 0), height)
        y1 = min(max(box[3], 0), height)
        if x1 <= x0 or y1 <= y0:
            continue
        box = [x0, y0, x1, y1]
        idx = _block_index(line.box, blocks)
        label = blocks[idx]["label"] if idx is not None else None
        rtl = _is_rtl(text)
        el = OcrElement(
            ocr_class=_LINE_CLASS.get(label or "", OcrClass.LINE),
            bbox=BoundingBox(*box),
            confidence=float(line.conf),
            direction="rtl" if rtl else "ltr",
            children=split_words(text, box, rtl),
        )
        if par is None or idx != par_key:
            par = OcrElement(ocr_class=OcrClass.PARAGRAPH, bbox=BoundingBox(*box))
            par_key = idx
            area.children.append(par)
        else:
            assert par.bbox is not None
            par.bbox = BoundingBox(
                min(par.bbox.left, x0),
                min(par.bbox.top, y0),
                max(par.bbox.right, x1),
                max(par.bbox.bottom, y1),
            )
        par.children.append(el)
        texts.append(text)
    root.children.append(area)
    return root, "\n".join(texts)
