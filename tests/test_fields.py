from types import SimpleNamespace as NS

import numpy as np
import pytest

pytest.importorskip("cv2")

from ocrmypdf_indra import fields


def form_line():
    """A 400x60 page: printed-looking blob on the left, a long underline from x=120."""
    gray = np.full((60, 400), 255, np.uint8)
    gray[15:45, 10:100] = 0  # stands in for the printed label
    gray[50:52, 120:390] = 0  # the underline
    gray[20:48, 200:230] = 0  # "handwriting" on the underline
    return gray


def test_find_underlines_returns_the_long_line_only():
    found = fields.find_underlines(form_line(), [0, 0, 400, 60])
    assert len(found) == 1
    start, end = found[0]
    assert 118 <= start <= 122 and 388 <= end <= 392


def test_short_underlines_under_words_are_ignored():
    gray = np.full((60, 400), 255, np.uint8)
    gray[50:52, 10:60] = 0
    assert fields.find_underlines(gray, [0, 0, 400, 60]) == []


def test_printed_label_is_reread_and_handwriting_kept():
    line = NS(box=[0, 0, 400, 60], text="ab XXXXXXXXXXXXXXXXXXXXXXX", conf=0.9)
    seen = []

    def recognise(crop):
        seen.append(crop.shape)
        return [NS(text="Потребитель")]

    fields.read_segments(form_line(), [line], recognise)
    assert line.text == "Потребитель XXXXXXXXXXXXXXXXXXXXXXX"
    assert len(seen) == 1


def test_lines_without_underline_are_untouched():
    gray = np.full((60, 400), 255, np.uint8)
    line = NS(box=[0, 0, 400, 60], text="plain text", conf=0.9)
    fields.read_segments(gray, [line], lambda crop: [NS(text="nope")])
    assert line.text == "plain text"
