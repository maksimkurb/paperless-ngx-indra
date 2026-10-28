from types import SimpleNamespace as NS

import pytest

pipeline = pytest.importorskip("indra_ocr.pipeline")

from ocrmypdf_indra import model


@pytest.fixture
def constants(monkeypatch):
    for name in ("ADAPTIVE_MIN_H", "ADAPTIVE_TARGET_H", "ADAPTIVE_MAX_SIDE"):
        monkeypatch.setattr(pipeline, name, getattr(pipeline, name))


def fake_converter():
    return NS(ocr=NS(lms={1: ("lm", 0.5, 1.5, 0.9)}))


def test_defaults_detect_at_line_height_16_without_the_language_model(monkeypatch, constants):
    monkeypatch.delenv("INDRA_LINE_HEIGHT", raising=False)
    monkeypatch.delenv("INDRA_OCR_LM", raising=False)
    conv = fake_converter()
    model._tune(conv)
    assert pipeline.ADAPTIVE_TARGET_H == 16
    assert pipeline.ADAPTIVE_MIN_H == float("inf")
    assert conv.ocr.lms[1] == ("lm", 0.5, 1.5, 0.0)


def test_indra_defaults_can_be_restored(monkeypatch, constants):
    monkeypatch.setenv("INDRA_LINE_HEIGHT", "0")
    monkeypatch.setenv("INDRA_OCR_LM", "1")
    before = pipeline.ADAPTIVE_MIN_H
    conv = fake_converter()
    model._tune(conv)
    assert pipeline.ADAPTIVE_MIN_H == before
    assert conv.ocr.lms[1][3] == 0.9
