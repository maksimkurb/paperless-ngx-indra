# paperless-ngx-indra

An [OCRmyPDF](https://ocrmypdf.readthedocs.io/) engine plugin that runs
[Indra OCR](https://github.com/datalab-to/indra) instead of Tesseract, plus a
[paperless-ngx](https://docs.paperless-ngx.com/) image with the plugin installed.

Paperless-ngx builds its searchable PDFs with OCRmyPDF. This plugin swaps only the
recognition engine, so Paperless keeps its OCR modes (`skip`, `redo`, `force`, `auto`), PDF/A
output, rotation/deskew handling and fallbacks.

## Use the image

```yaml
services:
  webserver:
    image: ghcr.io/maksimkurb/paperless-ngx-indra:latest   # or :<paperless-version>
    volumes:
      - indra-models:/usr/src/paperless/indra-models        # model cache (see below)
    environment:
      PAPERLESS_OCR_LANGUAGE: rus+eng+kaz
volumes:
  indra-models:
```

The image sets `PAPERLESS_OCR_USER_ARGS='{"plugins": ["ocrmypdf_indra"]}'`. To go back to
Tesseract, override that variable (for example set it to `{}`).

Tags: `<paperless-version>`, `<paperless-version>-indra<plugin-version>`, and `latest`.

## Install into your own image

```dockerfile
RUN uv pip install --system ocrmypdf-indra   # or a path / git URL
ENV PAPERLESS_OCR_USER_ARGS='{"plugins": ["ocrmypdf_indra"]}'
```

The plugin is deliberately **not** registered through an entry point, so installing it does
nothing until a run names it in `plugins`. Outside Paperless: `ocrmypdf --plugin ocrmypdf_indra in.pdf out.pdf`.

## Configuration

| Variable | Default | |
|---|---|---|
| `INDRA_OCR_MODEL_DIR` | image: `/usr/src/paperless/indra-models` | Folder with the Indra models. Empty folder = downloaded from Hugging Face on first use (~76 MB). |
| `INDRA_OCR_MATH` | off | `1` writes math lines as LaTeX (slower). |
| `PAPERLESS_OCR_LANGUAGE` | | Accepted but not used for recognition: Indra classifies the script of each line itself. |

Make the model folder a volume so the weights are downloaded once. The container user must be
able to write to it; the image creates it owned by `paperless`.

## How it works / limitations

- Uses OCRmyPDF's `generate_ocr()` API (OCRmyPDF 17.12.x, the range Paperless pins).
- Indra recognises lines, not words. Each line is split into words with the line box shared out
  in proportion to character counts, so text selection in the viewer is approximate within a line.
- Orientation: Indra's own detector replaces Tesseract's OSD for rotation. Deskew: Indra straightens pages
  internally and maps boxes back, so OCRmyPDF's deskew angle is reported as 0.
- Sideways or upside-down pages need page rotation enabled (`PAPERLESS_OCR_ROTATE_PAGES=true`,
  Paperless's default): OCRmyPDF then turns the page upright before recognition. With rotation
  off, OCRmyPDF drops the text layer of a sideways page. Indra's orientation model can miss a
  quarter turn on nearly empty pages.
- Only the default (fpdf2) PDF renderer is supported, which is what Paperless uses.
- Vertical CJK pages are read, but the text layer is laid out horizontally.
- Languages: Latin, Cyrillic (Russian, **Kazakh** and others), Greek, CJK, Arabic-script, Hebrew,
  Indic, Thai and more. See Indra's README for per-language quality. Handwriting, degraded scans
  and complex tables are known weak spots.

## Licence

The plugin code is Apache-2.0. **Indra's model weights are not**: they use a modified OpenRAIL-M
licence (free for personal use, research and startups under $20M funding/revenue; may not be used
to compete with Datalab's API). Because of that the published image does **not** contain the
weights; they are downloaded on first use. Build privately with `--build-arg BAKE_MODELS=1` to
embed them. Read the [weights licence](https://huggingface.co/datalab-to/indra-ocr/blob/main/LICENSE)
before using this commercially.

## Confirm that Indra ran

```
docker compose exec webserver python3 -c "import pikepdf,sys;print(pikepdf.open(sys.argv[1]).docinfo)" /path/to/archive.pdf
```

The producer/creator mentions `Indra OCR <version>`.

## Development

```
pip install -e ".[dev]"
pytest                     # unit tests (mocked Indra)
pytest -m integration      # real model; needs tesseract, ghostscript, qpdf, poppler
ruff check . && ruff format --check . && mypy src
```

`bench/` has a CER/WER harness comparing Tesseract and Indra on your own scans.
