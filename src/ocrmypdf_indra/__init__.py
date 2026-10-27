"""OCRmyPDF plugin that replaces Tesseract with Indra OCR.

Enable with ``ocrmypdf --plugin ocrmypdf_indra`` or, in paperless-ngx,
``PAPERLESS_OCR_USER_ARGS='{"plugins": ["ocrmypdf_indra"]}'``.
"""

from __future__ import annotations

from ocrmypdf import hookimpl

from .engine import IndraEngine

__all__ = ["IndraEngine", "get_ocr_engine"]


@hookimpl
def get_ocr_engine(options):
    # Naming this module in ``plugins`` is the opt-in; it must win over Tesseract unless
    # the caller explicitly chose another engine (e.g. ``--ocr-engine none``).
    engine = getattr(options, "ocr_engine", "auto") if options is not None else "auto"
    if engine in ("auto", "indra"):
        return IndraEngine()
    return None
