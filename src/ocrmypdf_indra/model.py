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


def _tune(conv) -> None:
    """Settings that read printed documents better than Indra's defaults.

    ``INDRA_LINE_HEIGHT`` (default 16, ``0`` keeps Indra's behaviour): the detector runs
    again at the page size where the median text line is this many pixels tall. Indra only
    does that for very small text (under 9 px at its 1024 px input), which leaves normal
    scans at a size where lines next to handwriting or stamps are missed.

    ``INDRA_OCR_LM=1`` keeps Indra's language model. It is tuned on handwriting and on
    printed forms it replaced correct words more often than it fixed them, so it is off
    by default.
    """
    from indra_ocr import pipeline

    height = float(os.environ.get("INDRA_LINE_HEIGHT", "16") or 0)
    if height > 0:
        pipeline.ADAPTIVE_MIN_H = float("inf")
        pipeline.ADAPTIVE_TARGET_H = height
        pipeline.ADAPTIVE_MAX_SIDE = 4096
    if not _env_flag("INDRA_OCR_LM"):
        ocr = conv.ocr
        ocr.lms = {k: (lm, alpha, beta, 0.0) for k, (lm, alpha, beta, _) in ocr.lms.items()}


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
        _tune(conv)
        _local.converter = conv
    return conv
