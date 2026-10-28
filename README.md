# paperless-ngx-indra

An [OCRmyPDF](https://ocrmypdf.readthedocs.io/) engine plugin that runs
[Indra OCR](https://github.com/datalab-to/indra) instead of Tesseract, plus a
[paperless-ngx](https://docs.paperless-ngx.com/) image with the plugin installed.

Paperless-ngx builds its searchable PDFs with OCRmyPDF. This plugin swaps only the
recognition engine, so Paperless keeps its OCR modes (`skip`, `redo`, `force`, `auto`), PDF/A
output, rotation/deskew handling and fallbacks.

## Install into the stock paperless-ngx image (recommended)

No custom image is needed. Paperless runs every script in `/custom-cont-init.d` as root just
before it starts; [`init/10-indra.sh`](init/10-indra.sh) installs the pinned plugin version
with `uv`, the same way the image installs its own packages.

```yaml
services:
  webserver:
    image: ghcr.io/paperless-ngx/paperless-ngx:latest
    volumes:
      - ./init:/custom-cont-init.d:ro       # folder owned by root, mode a=rx
      - indra:/usr/src/paperless/indra      # uv cache + model cache
    environment:
      PAPERLESS_OCR_USER_ARGS: '{"plugins": ["ocrmypdf_indra"]}'
      PAPERLESS_OCR_LANGUAGE: rus+eng+kaz
      HF_HOME: /usr/src/paperless/indra/hf
volumes:
  indra:
```

Download `init/10-indra.sh` from this repository (use the file from the release tag you want).

### Works offline

The script pins the plugin version (`INDRA_PLUGIN_VERSION`, set in the script) and:

1. does nothing if that version is already installed (plain container restarts);
2. otherwise installs from uv's cache (`--offline`), which the `indra` volume keeps after the
   first online start, so even a recreated container starts without network;
3. otherwise downloads the wheel from the GitHub release;
4. if there is no network and nothing cached, it exits with an error explaining what to do.

The init script also downloads the model (~76 MB) into `HF_HOME` once at container start (before
the Celery workers exist, so they don't all fetch it at the same time). It is used from the
cache afterwards without network, and a failed download only logs a warning; the Indra version, and therefore the model revision, is pinned by
the plugin. To avoid the network entirely, put the wheel next to the script and set
`INDRA_PLUGIN_SPEC=/wheels/ocrmypdf_indra-<version>-py3-none-any.whl`, and pre-populate the
`indra` volume (or set `INDRA_OCR_MODEL_DIR` to a folder that already contains the models).

| Variable | Default | |
|---|---|---|
| `INDRA_PLUGIN_VERSION` | pinned in the script | Plugin version to keep installed. |
| `INDRA_PLUGIN_SPEC` | the GitHub release wheel | Wheel path or URL. |
| `INDRA_CACHE_DIR` | `/usr/src/paperless/indra/uv` | uv cache for offline reinstalls. |
| `INDRA_OCR_MODEL_DIR` | unset | A folder that already holds the models. Setting it disables downloading. |
| `INDRA_SPLIT_FIELDS` | on | `0` turns off re-reading the printed labels in front of fill-in underlines (see below). |
| `INDRA_SCRIPT_FIX` | `auto` | Turns Latin look-alike letters into Cyrillic on mostly-Cyrillic pages. `cyrillic` forces it, `off` disables it. |
| `INDRA_OCR_MATH` | off | `1` writes math lines as LaTeX (slower). |
| `PAPERLESS_OCR_LANGUAGE` | | Accepted but not used for recognition: Indra classifies the script of each line itself. |

To go back to Tesseract, remove the `plugins` entry from `PAPERLESS_OCR_USER_ARGS`.

The plugin is deliberately **not** registered through an entry point, so installing it does
nothing until a run names it in `plugins`. Outside Paperless:
`ocrmypdf --plugin ocrmypdf_indra in.pdf out.pdf`.

## Optional: prebuilt image

`docker/Dockerfile` and the manually triggered `image.yml` workflow build an image with the
plugin baked in (`ghcr.io/maksimkurb/paperless-ngx-indra:<paperless-version>`). It sets
`PAPERLESS_OCR_USER_ARGS` for you and keeps its caches in a volume at `/usr/src/paperless/indra`.
A daily workflow checks that the plugin still installs and works in the newest stock image.

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
- Forms: when a line has a long fill-in underline (`Потребитель ______` with handwriting on it), the
  printed label is read again on its own, because the handwriting next to it spoils its reading.
  The handwriting keeps its original reading. This helps most labels but can occasionally drop a
  word that is itself underlined.
- Only the default (fpdf2) PDF renderer is supported, which is what Paperless uses.
- Vertical CJK pages are read, but the text layer is laid out horizontally.
- Languages: Latin, Cyrillic (Russian, **Kazakh** and others), Greek, CJK, Arabic-script, Hebrew,
  Indic, Thai and more. See Indra's README for per-language quality. Handwriting, degraded scans
  and complex tables are known weak spots.

## Licence

The plugin code is Apache-2.0. **Indra's model weights are not**: they use a modified OpenRAIL-M
licence (free for personal use, research and startups under $20M funding/revenue; may not be used
to compete with Datalab's API). Because of that the published image does **not** contain the
weights; they are downloaded on first use into a cache volume. Build privately with `--build-arg BAKE_MODELS=1` to
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
