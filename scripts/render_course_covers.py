#!/usr/bin/env python3
"""Overlay gold Nastaliq course titles on the shared library blank template.

Same background for every course; only the centered title changes.
Does not overwrite the four original ChatGPT covers unless --include-existing --force.

Usage:
  .venv/bin/python scripts/render_course_covers.py
  .venv/bin/python scripts/render_course_covers.py --only qalb_mashrub,asrar_ruzeh_namaz
"""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "website/apps/web/public/images/courses"
TEMPLATE = OUT_DIR / "_templates" / "library_blank.png"
FONT_PATH = Path("/System/Library/Fonts/NotoNastaliq.ttc")
TARGET_SIZE = (1536, 1024)

# Titles aligned with Eitaa channel names (cover-friendly spelling).
COURSE_TITLES: dict[str, str] = {
    "al_mawt_bihar": "کتاب الموت",
    "asrar_ruzeh_namaz": "اسرار روزه و نماز",
    "darunmayeh_ramadan": "درون مایه ماه مبارک رمضان",
    "ehras_awzat": "احراز و عوذات",
    "ensan_kamel": "انسان کامل",
    "kashkul_noor": "کشکول نور",
    "leghaallah": "لقاء الله",
    "manazel_saerein": "منازل السائرین",
    "maqamat_imam_zaman": "مقامات امام زمان",
    "maqamat_zahra": "مقامات حضرت زهرا",
    "marefat_nafs": "دروس معرفت نفس",
    "masael_ebadi": "مسائل عبادی سیاسی اجتماعی",
    "nahj_al_wilayah": "نهج الولایة",
    "nameha_barnameha": "نامه‌ها برنامه‌ها",
    "porsesh_pasokh": "پرسش و پاسخ",
    "qalb_aghlad": "قلب اغلف",
    "qalb_athem": "قلب آثم",
    "qalb_khashe": "قلب خاشع",
    "qalb_layyen": "قلب لیّن",
    "qalb_makhtum": "قلب مختوم",
    "qalb_maknun": "قلب مکنون",
    "qalb_maluf": "قلب مألوف",
    "qalb_manzel": "قلب منزل",
    "qalb_maqful": "قلب مقفول",
    "qalb_marub": "قلب مرعوب",
    "qalb_mashrub": "قلب مشروب",
    "qalb_matbu": "قلب مطبوع",
    "qalb_mokhbet": "قلب مخبت",
    "qalb_momen": "قلب مؤمن",
    "qalb_momtahan": "قلب ممتحن",
    "qalb_monafeq": "قلب منافق",
    "qalb_monghamer": "قلب منغمر",
    "qalb_monharef": "قلب منحرف",
    "qalb_monib": "قلب منیب",
    "qalb_morib": "قلب مریب",
    "qalb_motmaen": "قلب مطمئن",
    "qalb_qasi": "قلب قسی",
    "qalb_salim": "قلب سلیم",
    "sad_kalameh": "صد کلمه در معرفت نفس",
    "sermaknoon": "سرّ مکنون",
    "seyr_bahr_olum": "سیر و سلوک سید بحرالعلوم",
    "seyr_tabatabai": "سیر و سلوک علامه طباطبایی",
    "sukhtan": "موضوع سوختن",
    "ziyarat_jameh": "زیارت جامعه کبیره",
}

SKIP_EXISTING = {"marefat_nafs", "ehras_awzat", "sermaknoon", "leghaallah"}

GOLD = (232, 188, 96, 255)
GOLD_SHADOW = (18, 10, 4, 170)


def load_font(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_PATH), size=size, index=0)


def ink_bbox(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont) -> tuple[int, int, int, int]:
    """Return (l, t, r, b) of ink for text drawn at (0, 0). Nastaliq has large offsets."""
    return draw.textbbox((0, 0), text, font=font)


def wrap_title(title: str, font: ImageFont.ImageFont, draw: ImageDraw.ImageDraw, max_w: int) -> list[str]:
    l, t, r, b = ink_bbox(draw, title, font)
    if (r - l) <= max_w:
        return [title]
    words = title.split()
    if len(words) <= 1:
        return [title]
    best: list[str] | None = None
    best_score = 1e18
    for i in range(1, len(words)):
        a = " ".join(words[:i])
        btxt = " ".join(words[i:])
        wa = ink_bbox(draw, a, font)[2] - ink_bbox(draw, a, font)[0]
        wb = ink_bbox(draw, btxt, font)[2] - ink_bbox(draw, btxt, font)[0]
        if wa > max_w or wb > max_w:
            continue
        score = abs(wa - wb)
        if score < best_score:
            best_score = score
            best = [a, btxt]
    return best or [title]


def fit_font(title: str, draw: ImageDraw.ImageDraw, max_w: int, max_h: int) -> tuple[ImageFont.FreeTypeFont, list[str]]:
    for size in range(120, 52, -2):
        font = load_font(size)
        lines = wrap_title(title, font, draw, max_w)
        heights = []
        widths = []
        ok = True
        for ln in lines:
            l, t, r, b = ink_bbox(draw, ln, font)
            widths.append(r - l)
            heights.append(b - t)
            if (r - l) > max_w:
                ok = False
        gap = int(size * 0.28)
        total_h = sum(heights) + gap * (len(lines) - 1)
        if ok and total_h <= max_h:
            return font, lines
    font = load_font(52)
    return font, wrap_title(title, font, draw, max_w)


def render_line(text: str, font: ImageFont.ImageFont, pad: int = 28) -> Image.Image:
    """Rasterize one line with full glyph ink inside the image (fixes Nastaliq clipping)."""
    probe = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    l, t, r, b = ink_bbox(probe, text, font)
    w, h = r - l, b - t
    img = Image.new("RGBA", (w + pad * 2, h + pad * 2), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # Shift by (-l, -t) so ink starts at (pad, pad)
    xy = (pad - l, pad - t)
    draw.text((xy[0] + 3, xy[1] + 4), text, font=font, fill=GOLD_SHADOW)
    draw.text(xy, text, font=font, fill=GOLD)
    return img


def stack_lines(lines: list[Image.Image], gap: int) -> Image.Image:
    width = max(im.width for im in lines)
    height = sum(im.height for im in lines) + gap * (len(lines) - 1)
    out = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    y = 0
    for im in lines:
        x = (width - im.width) // 2
        out.alpha_composite(im, (x, y))
        y += im.height + gap
    return out


def render_cover(title: str, base: Image.Image) -> Image.Image:
    canvas = base.convert("RGBA")
    w, h = canvas.size
    max_w = int(w * 0.54)
    max_h = int(h * 0.34)
    probe = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    font, lines = fit_font(title, probe, max_w, max_h)
    gap = int(font.size * 0.22)
    block = stack_lines([render_line(ln, font) for ln in lines], gap=gap)

    glow = block.filter(ImageFilter.GaussianBlur(radius=8))
    # Warm soft halo
    gpx = glow.load()
    for yy in range(glow.height):
        for xx in range(glow.width):
            r, g, b, a = gpx[xx, yy]
            if a:
                gpx[xx, yy] = (210, 160, 70, min(100, a // 2))

    # Sit above the gold flourish (~lower third of panel)
    cx = (w - block.width) // 2
    cy = int(h * 0.40) - block.height // 2
    canvas.alpha_composite(glow, (cx, cy))
    canvas.alpha_composite(block, (cx, cy))
    return canvas.convert("RGB")


def verify_cover(path: Path, min_gold_span: int = 70) -> str | None:
    """Return error string if title gold band looks clipped / missing."""
    import numpy as np

    im = np.array(Image.open(path))
    h, w = im.shape[:2]
    gold = (im[:, :, 0] > 150) & (im[:, :, 1] > 90) & (im[:, :, 0] > im[:, :, 2] + 30)
    # Ignore bottom flourish region
    gold = gold[: int(h * 0.72), int(w * 0.22) : int(w * 0.78)]
    rows = np.where(gold.sum(axis=1) > 25)[0]
    if len(rows) < 5:
        return "almost no gold title pixels"
    span = int(rows[-1] - rows[0] + 1)
    if span < min_gold_span:
        return f"gold span too thin ({span}px) — likely clipped"
    # Large internal gap suggests a cut through the letters
    gaps = [int(rows[i] - rows[i - 1]) for i in range(1, len(rows)) if rows[i] - rows[i - 1] > 8]
    if gaps and max(gaps) > 40:
        return f"internal gap in title ({max(gaps)}px)"
    return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--only", default="")
    ap.add_argument("--include-existing", action="store_true")
    args = ap.parse_args()

    if not TEMPLATE.is_file():
        raise SystemExit(f"Missing template: {TEMPLATE}")
    if not FONT_PATH.is_file():
        raise SystemExit(f"Missing font: {FONT_PATH}")

    base = Image.open(TEMPLATE).convert("RGB")
    if base.size != TARGET_SIZE:
        base = base.resize(TARGET_SIZE, Image.Resampling.LANCZOS)

    only = {s.strip() for s in args.only.split(",") if s.strip()}
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    done = 0
    skipped = 0
    errors: list[str] = []
    for slug, title in sorted(COURSE_TITLES.items()):
        if only and slug not in only:
            continue
        out = OUT_DIR / f"{slug}.png"
        if slug in SKIP_EXISTING and not (args.force and args.include_existing):
            skipped += 1
            print(f"skip existing {slug}")
            continue
        if out.exists() and not args.force and slug in SKIP_EXISTING:
            skipped += 1
            continue

        img = render_cover(title, base.copy())
        img.save(out, format="PNG", optimize=True)
        err = verify_cover(out)
        if err:
            errors.append(f"{slug}: {err}")
            print(f"BAD {slug} → {title} ({err})")
        else:
            print(f"OK {slug} → {title} ({out.stat().st_size:,} bytes)")
        done += 1

    print(f"\nRendered {done}, skipped {skipped}")
    if errors:
        print(f"VERIFY FAILED ({len(errors)}):")
        for e in errors:
            print(" ", e)
        raise SystemExit(1)
    print("Verify: all rendered covers look complete")


if __name__ == "__main__":
    main()
