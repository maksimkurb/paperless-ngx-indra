"""Real model + OCRmyPDF. Run with ``pytest -m integration``."""

import shutil
import subprocess
from pathlib import Path

import ocrmypdf
import pytest
from PIL import Image, ImageDraw, ImageFont

pytestmark = pytest.mark.integration

FONT = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
TEXTS = {
    "en": [
        "Invoice number 2024-0173",
        "The quick brown fox jumps over the lazy dog",
        "Total amount due: 1250.00 EUR",
    ],
    "ru": ["Счёт на оплату номер 15", "Итого к оплате: 4500 рублей"],
    "kk": ["Құжат нөмірі 42 берілді", "Алматы қаласы, Қазақстан"],
}


def _page(lines):
    im = Image.new("L", (1654, 2339), 255)
    d = ImageDraw.Draw(im)
    font = ImageFont.truetype(FONT, 44)
    for i, t in enumerate(lines):
        d.text((150, 200 + i * 90), t, font=font, fill=0)
    return im


def _ocr(tmp_path: Path, im: Image.Image, **kw) -> str:
    src, out = tmp_path / "in.png", tmp_path / "out.pdf"
    im.save(src, dpi=(200, 200))
    ocrmypdf.ocr(src, out, plugins=["ocrmypdf_indra"], output_type="pdf", image_dpi=200, **kw)
    return subprocess.run(
        ["pdftotext", str(out), "-"], capture_output=True, text=True, check=True
    ).stdout


@pytest.fixture(autouse=True)
def _tools():
    if not shutil.which("pdftotext"):
        pytest.skip("pdftotext not installed")


@pytest.mark.parametrize("lang", TEXTS)
def test_text_layer_contains_recognised_words(tmp_path, lang):
    text = _ocr(tmp_path, _page(TEXTS[lang]))
    for line in TEXTS[lang]:
        for word in line.split():
            assert word in text, (word, text)


@pytest.mark.parametrize("angle", [90, 180, 270])
def test_rotated_pages_are_turned_upright(tmp_path, angle):
    text = _ocr(
        tmp_path, _page(TEXTS["en"]).rotate(angle, expand=True, fillcolor=255), rotate_pages=True
    )
    assert "Invoice number 2024-0173" in text


def test_skewed_page(tmp_path):
    text = _ocr(tmp_path, _page(TEXTS["en"]).rotate(4, fillcolor=255))
    assert "Invoice number 2024-0173" in text


def test_creator_tag(tmp_path):
    import pikepdf

    _ocr(tmp_path, _page(TEXTS["en"]))
    with pikepdf.open(tmp_path / "out.pdf") as pdf:
        meta = str(pdf.docinfo) + str(pdf.open_metadata())
    assert "Indra OCR" in meta
