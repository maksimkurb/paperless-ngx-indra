"""Run inside the built image: Paperless's own OCR parser must use the Indra engine.

Needs only what the image already contains (plus the plugin); makes a one-page PDF from
an image with Pillow.
"""

import os
import sys
import tempfile
from pathlib import Path

import django
from PIL import Image, ImageDraw, ImageFont

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "paperless.settings")
os.environ.setdefault("PAPERLESS_SECRET_KEY", "smoke")
sys.path.insert(0, "/usr/src/paperless/src")
django.setup()

import ocrmypdf
import pikepdf

work = Path(tempfile.mkdtemp())
img = Image.new("L", (1654, 600), 255)
font = ImageFont.load_default(size=60)
ImageDraw.Draw(img).text((100, 200), "Smoke test invoice 4711", font=font, fill=0)
src = work / "in.pdf"
img.save(src, "PDF", resolution=200)

out = work / "out.pdf"
ocrmypdf.ocr(src, out, plugins=["ocrmypdf_indra"], output_type="pdf", force_ocr=True)
with pikepdf.open(out) as pdf:
    creator = str(pdf.docinfo.get("/Creator", "")) + str(pdf.docinfo.get("/Producer", ""))
    xmp = pdf.open_metadata()
    tag = str(xmp.get("pdf:Producer", "")) + creator
text = os.popen(f"pdftotext {out} -").read()
print("creator:", tag)
print("text:", text.strip())
assert "Indra" in tag, "Indra engine was not used"
assert "4711" in text, "text layer is missing the recognised words"
