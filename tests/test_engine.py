from types import SimpleNamespace as NS

import ocrmypdf_indra
from ocrmypdf_indra.engine import IndraEngine


def test_hook_selection():
    assert isinstance(ocrmypdf_indra.get_ocr_engine(NS(ocr_engine="auto")), IndraEngine)
    assert isinstance(ocrmypdf_indra.get_ocr_engine(None), IndraEngine)
    assert ocrmypdf_indra.get_ocr_engine(NS(ocr_engine="tesseract")) is None
    assert ocrmypdf_indra.get_ocr_engine(NS(ocr_engine="none")) is None


def test_metadata_and_languages():
    e = IndraEngine()
    assert "Indra OCR" in IndraEngine.creator_tag(NS())
    assert str(e).startswith("Indra OCR")
    langs = IndraEngine.languages(NS())
    assert {"eng", "rus", "kaz", "deu", "chi_sim"} <= langs
    assert IndraEngine.supports_generate_ocr()
