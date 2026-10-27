"""CER/WER and speed: Tesseract vs Indra on your own scans.

Layout: <corpus>/<name>.(pdf|png|jpg|tif) next to <name>.txt with the ground truth.
Usage: python bench/bench.py CORPUS_DIR [--tess-lang rus+eng+kaz]
"""

from __future__ import annotations

import argparse
import re
import subprocess
import tempfile
import time
from pathlib import Path

import jiwer
import ocrmypdf


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip().lower()


def run(src: Path, plugins: list[str], lang: str) -> tuple[str, float]:
    with tempfile.TemporaryDirectory() as d:
        out = Path(d) / "o.pdf"
        t0 = time.perf_counter()
        ocrmypdf.ocr(
            src,
            out,
            plugins=plugins,
            language=[lang],
            output_type="pdf",
            force_ocr=True,
            rotate_pages=True,
            progress_bar=False,
        )
        dt = time.perf_counter() - t0
        text = subprocess.run(
            ["pdftotext", str(out), "-"], check=False, capture_output=True, text=True
        ).stdout
    return norm(text), dt


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("corpus", type=Path)
    ap.add_argument("--tess-lang", default="rus+eng")
    a = ap.parse_args()
    rows = []
    for src in sorted(
        p
        for p in a.corpus.iterdir()
        if p.suffix.lower() in {".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff"}
    ):
        gt = src.with_suffix(".txt")
        if not gt.exists():
            continue
        ref = norm(gt.read_text(encoding="utf-8"))
        for name, plugins, lang in [
            ("tesseract", [], a.tess_lang),
            ("indra", ["ocrmypdf_indra"], "eng"),
        ]:
            hyp, dt = run(src, plugins, lang)
            rows.append((src.name, name, jiwer.cer(ref, hyp), jiwer.wer(ref, hyp), dt))
    print("| file | engine | CER | WER | seconds |\n|---|---|---|---|---|")
    for f, e, c, w, t in rows:
        print(f"| {f} | {e} | {c:.3f} | {w:.3f} | {t:.1f} |")
    for e in ("tesseract", "indra"):
        r = [x for x in rows if x[1] == e]
        if r:
            n = len(r)
            print(
                f"\n{e}: mean CER {sum(x[2] for x in r) / n:.3f}, mean WER {sum(x[3] for x in r) / n:.3f}, {sum(x[4] for x in r) / n:.1f}s/doc"
            )


if __name__ == "__main__":
    main()
