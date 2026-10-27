"""Lazy, per-thread loader for the Indra OCR converter.

OCRmyPDF parallelises over pages (threads or processes), so every worker gets its own
single-threaded converter instead of sharing one across threads.
"""

from __future__ import annotations

import os
import threading

_local = threading.local()


def _env_flag(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def get_converter():
    """Return this thread's ``indra_ocr.Converter``, loading the models on first use.

    ``INDRA_OCR_MODEL_DIR`` selects a local model folder (otherwise the models are
    downloaded from Hugging Face once and cached); ``INDRA_OCR_MATH=1`` turns on LaTeX
    recognition for math lines.
    """
    conv = getattr(_local, "converter", None)
    if conv is None:
        import indra_ocr

        conv = indra_ocr.load(
            path=os.environ.get("INDRA_OCR_MODEL_DIR") or None,
            threads=1,
            mode="ocr",
            image_ocr=False,
            math=_env_flag("INDRA_OCR_MATH"),
        )
        _local.converter = conv
    return conv
