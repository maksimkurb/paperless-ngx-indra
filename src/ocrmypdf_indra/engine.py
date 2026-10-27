"""The OCRmyPDF ``OcrEngine`` backed by Indra OCR."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
from ocrmypdf.hocrtransform import OcrElement
from ocrmypdf.pluginspec import OcrEngine, OrientationConfidence
from PIL import Image

from .convert import page_to_tree
from .model import get_converter

if TYPE_CHECKING:
    from ocrmypdf._options import OcrOptions

# ISO 639-2/T style codes (Tesseract naming) for the scripts Indra reads. Indra picks the
# recogniser per line, so the language is only accepted, never used.
_LANGUAGES = frozenset(
    [
        "afr",
        "aze",
        "bel",
        "bos",
        "bul",
        "cat",
        "ces",
        "cym",
        "dan",
        "deu",
        "ell",
        "eng",
        "epo",
        "est",
        "eus",
        "fin",
        "fra",
        "gle",
        "glg",
        "hrv",
        "hun",
        "ind",
        "isl",
        "ita",
        "lav",
        "lit",
        "mkd",
        "msa",
        "mlt",
        "nld",
        "nor",
        "pol",
        "por",
        "ron",
        "slk",
        "slv",
        "spa",
        "sqi",
        "srp",
        "swa",
        "swe",
        "tgl",
        "tur",
        "ukr",
        "uzb",
        "vie",
        "rus",
        "kaz",
        "kir",
        "tgk",
        "mon",
        "tat",
        "bak",
        "chv",
        "sah",
        "chi_sim",
        "chi_tra",
        "jpn",
        "kor",
        "ara",
        "fas",
        "urd",
        "pus",
        "kur",
        "heb",
        "yid",
        "hin",
        "mar",
        "nep",
        "ben",
        "tam",
        "tel",
        "kan",
        "mal",
        "guj",
        "pan",
        "ori",
        "sin",
        "tha",
        "lao",
        "khm",
        "mya",
        "kat",
        "hye",
        "amh",
    ]
)


def _load_gray(path: Path) -> tuple[np.ndarray, float]:
    with Image.open(path) as img:
        dpi = img.info.get("dpi", (300, 300))
        dpi_x = float(dpi[0] if isinstance(dpi, tuple) else dpi) or 300.0
        return np.asarray(img.convert("L")), dpi_x


class IndraEngine(OcrEngine):
    @staticmethod
    def version() -> str:
        import indra_ocr

        return indra_ocr.__version__

    @staticmethod
    def creator_tag(options: OcrOptions) -> str:
        return f"Indra OCR {IndraEngine.version()}"

    def __str__(self) -> str:
        return f"Indra OCR {self.version()}"

    @staticmethod
    def languages(options: OcrOptions) -> set[str]:
        return set(_LANGUAGES)

    @staticmethod
    def get_orientation(input_file: Path, options: OcrOptions) -> OrientationConfidence:
        from indra_ocr.pipeline import DESKEW_MIN, VERTICAL, estimate_skew, preview, rotate_page

        gray, _ = _load_gray(input_file)
        ocr = get_converter().ocr
        small = preview(gray)
        skew = estimate_skew(small)
        if abs(skew) >= DESKEW_MIN:
            small = rotate_page(small, skew)
        k = ocr.orientation(small)
        if k == VERTICAL or k == 0:
            return OrientationConfidence(angle=0, confidence=0.0)
        # Indra reports how many counter-clockwise quarter turns the content has; OCRmyPDF
        # wants the clockwise rotation the content has (it corrects counter-clockwise).
        return OrientationConfidence(angle=(-90 * k) % 360, confidence=15.0)

    @staticmethod
    def get_deskew(input_file: Path, options: OcrOptions) -> float:
        # Indra straightens each page itself and maps the boxes back onto the original.
        return 0.0

    @staticmethod
    def supports_generate_ocr() -> bool:
        return True

    @staticmethod
    def generate_ocr(
        input_file: Path, options: OcrOptions, page_number: int = 0
    ) -> tuple[OcrElement, str]:
        gray, dpi = _load_gray(input_file)
        page = get_converter().ocr(gray)
        height, width = gray.shape
        return page_to_tree(page, (width, height), dpi, page_number)

    @staticmethod
    def generate_hocr(
        input_file: Path, output_hocr: Path, output_text: Path, options: OcrOptions
    ) -> None:
        raise NotImplementedError("ocrmypdf-indra only supports the generate_ocr() API")

    @staticmethod
    def generate_pdf(
        input_file: Path, output_pdf: Path, output_text: Path, options: OcrOptions
    ) -> None:
        raise NotImplementedError(
            "ocrmypdf-indra only supports the fpdf2 renderer (--pdf-renderer auto/fpdf2)"
        )
