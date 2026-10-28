"""Normalise Latin look-alikes inside Cyrillic text.

Indra picks the recogniser per line, so a line that mixes print and handwriting can come
back with Latin letters standing in for Cyrillic ones (``потревитель`` aside, think of
``Aрес`` with a Latin ``A``). On a page that is mostly Cyrillic such words are turned back
into Cyrillic. This only fixes the alphabet; it does not repair misread letters.

``INDRA_SCRIPT_FIX``: ``auto`` (default, decide per page), ``cyrillic`` (always) or ``off``.
"""

from __future__ import annotations

import os
import re

_LATIN_TO_CYRILLIC = dict(
    zip(
        "ABCEHKMOPTXYaceopxy",
        "АВСЕНКМОРТХУасеорху",
        strict=True,
    )
)
_CYR = re.compile(r"[Ѐ-ӿ]")
_LAT = re.compile(r"[A-Za-z]")
_WORD = re.compile(r"[^\W\d_]+", re.UNICODE)  # runs of letters only

# a page counts as Cyrillic when this share of its letters is Cyrillic
_PAGE_SHARE = 0.6
# an all-Latin word is only converted when it is at least this long (keeps "CE", "kW")
_MIN_LATIN_ONLY = 3


def mode() -> str:
    value = os.environ.get("INDRA_SCRIPT_FIX", "auto").strip().lower()
    return value if value in ("auto", "cyrillic", "off") else "auto"


def is_cyrillic_page(texts: list[str]) -> bool:
    cyr = sum(len(_CYR.findall(t)) for t in texts)
    lat = sum(len(_LAT.findall(t)) for t in texts)
    return cyr + lat > 0 and cyr / (cyr + lat) >= _PAGE_SHARE


def _fix_word(word: str) -> str:
    has_cyr = bool(_CYR.search(word))
    latin = _LAT.findall(word)
    if not latin or not all(c in _LATIN_TO_CYRILLIC for c in latin):
        return word
    if not has_cyr and len(word) < _MIN_LATIN_ONLY:
        return word
    return "".join(_LATIN_TO_CYRILLIC.get(c, c) for c in word)


def fix_line(text: str) -> str:
    return _WORD.sub(lambda m: _fix_word(m.group()), text)


def fix_page(texts: list[str]) -> list[str]:
    """Return ``texts`` with look-alike Latin letters replaced when the page is Cyrillic."""
    m = mode()
    if m == "off" or not (m == "cyrillic" or is_cyrillic_page(texts)):
        return texts
    return [fix_line(t) for t in texts]
