"""Render SPECIMEN passport pages (original design, no national insignia) at 300 DPI TD3 size."""
import math
import random
from datetime import date
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H = 1476, 1039  # 125 x 88 mm @ 300 DPI
FONTS = Path(__file__).parent / "fonts"
SANS = ["/System/Library/Fonts/Supplemental/Arial.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "DejaVuSans.ttf"]
SANS_BOLD = ["/System/Library/Fonts/Supplemental/Arial Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "DejaVuSans-Bold.ttf"]


def _font(candidates, size):
    for c in candidates:
        try:
            return ImageFont.truetype(str(c), size)
        except OSError:
            continue
    return ImageFont.load_default(size)


def _fmt(iso: str) -> str:
    return date.fromisoformat(iso).strftime("%d/%m/%Y")


def _background(r: random.Random) -> Image.Image:
    img = Image.new("RGB", (W, H), (236, 240, 232))
    d = ImageDraw.Draw(img)
    phase = r.uniform(0, 6.28)
    for k in range(0, H, 14):  # procedural wave pattern
        pts = [(x, k + 6 * math.sin(x / 55 + phase + k / 90)) for x in range(0, W + 20, 20)]
        d.line(pts, fill=(214, 224, 210), width=2)
    return img


def _watermark(img: Image.Image, text="SPECIMEN", mrz_top=None):
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    t = Image.new("RGBA", (1400, 260), (0, 0, 0, 0))
    ImageDraw.Draw(t).text((700, 130), text, font=_font(SANS_BOLD, 210), fill=(200, 30, 30, 55), anchor="mm")
    t = t.rotate(18, expand=True)
    layer.alpha_composite(t, ((W - t.width) // 2, ((mrz_top or H) - t.height) // 2))
    if mrz_top:  # keep the MRZ zone clean for OCR
        ImageDraw.Draw(layer).rectangle([0, mrz_top, W, H], fill=(0, 0, 0, 0))
    img.paste(layer, (0, 0), layer)


def _field(d, x, y, label, value, size=34):
    d.text((x, y), label, font=_font(SANS, 20), fill=(70, 80, 90))
    d.text((x, y + 24), value, font=_font(SANS_BOLD, size), fill=(20, 20, 30))


def data_page(p: dict, path: Path, seed: int):
    r = random.Random(seed)
    img = _background(r)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 70], fill=(48, 78, 96))
    d.text((40, 35), "PASSPORT", font=_font(SANS_BOLD, 40), fill="white", anchor="lm")
    d.text((W - 40, 35), "SPECIMEN - NOT A VALID TRAVEL DOCUMENT", font=_font(SANS_BOLD, 24), fill=(255, 210, 120), anchor="rm")

    # placeholder photo
    tone = r.choice([(150, 112, 90), (176, 135, 105), (125, 92, 72), (190, 150, 120)])
    bg = r.choice([(225, 230, 238), (238, 238, 238), (220, 232, 240)])
    px, py, pw, ph = 50, 110, 360, 460
    d.rectangle([px, py, px + pw, py + ph], fill=bg, outline=(120, 120, 120), width=2)
    cx = px + pw // 2
    d.ellipse([cx - 85, py + 70, cx + 85, py + 280], fill=tone)
    d.chord([px + 30, py + 290, px + pw - 30, py + ph + 200], 180, 360, fill=tone)

    x1, x2, x3 = 450, 760, 1080
    _field(d, x1, 100, "Type", p["type"])
    _field(d, x2, 100, "Country Code", p["country_code"])
    _field(d, x3, 100, "Passport No.", p["passport_no"], 40)
    _field(d, x1, 180, "Surname", p["surname"])
    _field(d, x1, 260, "Given Name(s)", p["given_names"])
    _field(d, x1, 340, "Nationality", p["nationality"])
    _field(d, x2, 340, "Sex", p["sex"])
    _field(d, x3, 340, "Date of Birth", _fmt(p["date_of_birth"]))
    _field(d, x1, 420, "Place of Birth", p["place_of_birth"])
    _field(d, x1, 500, "Place of Issue", p["place_of_issue"])
    _field(d, x2, 580, "Date of Issue", _fmt(p["date_of_issue"]))
    _field(d, x3, 580, "Date of Expiry", _fmt(p["date_of_expiry"]))

    # signature scribble
    sig = [(60 + i * 8, 640 + 18 * math.sin(i / 2.3 + r.random()) + r.randint(-6, 6)) for i in range(40)]
    d.line(sig, fill=(30, 40, 110), width=3)
    d.text((60, 690), "Holder's Signature", font=_font(SANS, 18), fill=(70, 80, 90))

    mrz_top = 820
    d.rectangle([0, mrz_top, W, H], fill=(246, 246, 240))
    size = 60
    while (ocrb := _font([FONTS / "OCRB.otf"], size)).getlength("<" * 44) > W - 80:
        size -= 1
    d.text((40, 860), p["mrz"]["line1"], font=ocrb, fill="black")
    d.text((40, 940), p["mrz"]["line2"], font=ocrb, fill="black")
    _watermark(img, mrz_top=mrz_top)
    img.save(path, dpi=(300, 300))


def address_page(p: dict, path: Path, seed: int):
    r = random.Random(seed + 1)
    img = _background(r)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 70], fill=(48, 78, 96))
    d.text((40, 35), "PARTICULARS", font=_font(SANS_BOLD, 36), fill="white", anchor="lm")
    d.text((W - 40, 35), p["passport_no"], font=_font(SANS_BOLD, 40), fill=(255, 210, 120), anchor="rm")
    a = p["address"]
    _field(d, 60, 110, "Name of Father / Legal Guardian", p["father_name"])
    _field(d, 60, 190, "Name of Mother", p["mother_name"])
    _field(d, 60, 270, "Name of Spouse", p["spouse_name"] or "-")
    d.text((60, 350), "Address", font=_font(SANS, 20), fill=(70, 80, 90))
    for i, line in enumerate([a["line1"], a["line2"], f"{a['city']}, {a['state']}", f"PIN: {a['pincode']}"]):
        d.text((60, 374 + i * 44), line.upper(), font=_font(SANS_BOLD, 34), fill=(20, 20, 30))
    old = p["old_passport"]
    _field(d, 60, 570, "Old Passport No. with Date and Place of Issue",
           f"{old['number']}  {_fmt(old['date_of_issue'])}  {old['place_of_issue']}" if old else "-")
    _field(d, 60, 650, "File No.", p["file_no"])
    _watermark(img)
    img.save(path, dpi=(300, 300))
