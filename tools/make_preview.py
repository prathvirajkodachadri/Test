#!/usr/bin/env python3
"""
Social preview / favicon generator
==================================

Renders the 1200x630 Open Graph card (`preview.jpg`) plus the favicon set from
the book metadata in `content/book.js`, using the same palette and typefaces as
`assets/css/style.css` (EB Garamond / Inter / Noto Serif Kannada).

Everything it produces is checked into the repository, so running this is only
necessary when the cover, the title or the blurb changes:

    pip install pillow uharfbuzz freetype-py
    python3 tools/make_preview.py

Kannada needs real OpenType shaping (reph, vattu, pre-base vowel signs), which
Pillow cannot do on its own unless it was built against libraqm. To stay
dependency-light the text is shaped with HarfBuzz and the resulting glyphs are
rasterised one at a time with FreeType, then composited onto the canvas. The
whole card is drawn at 2x and downsampled, which gives clean edges without
needing subpixel glyph positioning.

Outputs (all in the repository root, served as-is by GitHub Pages):

    preview.jpg           1200x630  Open Graph / Twitter card
    favicon.ico           16/32/48  classic favicon
    favicon-32x32.png     32x32
    favicon-16x16.png     16x16
    apple-touch-icon.png  180x180
"""

from __future__ import annotations

import os
import re
import sys
import unicodedata

try:
    import freetype
    import uharfbuzz as hb
    from PIL import Image, ImageChops, ImageDraw, ImageFilter
except ImportError as exc:  # pragma: no cover - developer convenience
    sys.exit(
        f"missing dependency: {exc.name}\n"
        "    pip install pillow uharfbuzz freetype-py"
    )

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ---------------------------------------------------------------- palette --
# Mirrors the custom properties at the top of assets/css/style.css.
PAPER = (246, 242, 233)
PAPER_2 = (239, 233, 220)
CARD = (255, 253, 248)
INK = (35, 32, 28)
INK_SOFT = (91, 84, 74)
INK_FAINT = (141, 132, 120)
RULE = (221, 212, 195)
EMBER = (168, 85, 43)

SCALE = 2  # supersampling factor
W, H = 1200, 630

# ------------------------------------------------------------------ fonts --
# Latin faces first, Kannada fallback second - the same ordering the site's
# --serif / --sans stacks use.
FONT_DIRS = [
    os.environ.get("FONT_DIR", "/tmp/fonts"),
    os.path.join(ROOT, "tools", "fonts"),
]


def find_font(*candidates: str) -> str:
    for base in FONT_DIRS:
        for name in candidates:
            path = os.path.join(base, name)
            if os.path.exists(path):
                return path
    raise SystemExit(
        "could not find any of "
        + ", ".join(candidates)
        + f"\n  looked in: {', '.join(FONT_DIRS)}"
        "\n  set FONT_DIR=/path/to/fonts (see the header of this file)"
    )


SERIF_LATIN = find_font("eb-garamond/600SemiBold/EBGaramond_600SemiBold.ttf")
SERIF_LATIN_REG = find_font("eb-garamond/400Regular/EBGaramond_400Regular.ttf")
SERIF_KN_BOLD = find_font("serif/700Bold/NotoSerifKannada_700Bold.ttf")
SERIF_KN_REG = find_font("serif/400Regular/NotoSerifKannada_400Regular.ttf")
SANS_LATIN = find_font("inter/600SemiBold/Inter_600SemiBold.ttf")
SANS_LATIN_REG = find_font("inter/500Medium/Inter_500Medium.ttf")
SANS_KN = find_font("sans/600SemiBold/NotoSansKannada_600SemiBold.ttf")
SANS_KN_REG = find_font("sans/500Medium/NotoSansKannada_500Medium.ttf")


class Face:
    """A HarfBuzz shaper + FreeType rasteriser bound to one font file."""

    _cache: dict[str, "Face"] = {}

    def __new__(cls, path: str):
        if path not in cls._cache:
            self = super().__new__(cls)
            blob = hb.Blob.from_file_path(path)
            self.hb_face = hb.Face(blob)
            self.hb_font = hb.Font(self.hb_face)
            self.upem = self.hb_face.upem
            self.hb_font.scale = (self.upem, self.upem)
            hb.ot_font_set_funcs(self.hb_font)
            self.ft = freetype.Face(path)
            self.path = path
            cls._cache[path] = self
        return cls._cache[path]


KANNADA = re.compile(r"[\u0C80-\u0CFF\u200C\u200D]")
NEUTRAL = re.compile(r"[\s\u2010-\u2027\u2030-\u205E!-/:-@\[-`{-~\u00A0]")


def runs(text: str):
    """Split text into (is_kannada, substring) runs so each run can be shaped
    with a font that actually has the glyphs. Spaces and punctuation stick to
    whichever run precedes them."""
    out: list[list] = []
    for ch in text:
        if NEUTRAL.match(ch):
            kn = out[-1][0] if out else False
        else:
            kn = bool(KANNADA.match(ch)) or unicodedata.combining(ch) > 0
        if out and out[-1][0] == kn:
            out[-1][1] += ch
        else:
            out.append([kn, ch])
    return [(kn, s) for kn, s in out]


def shape(face: Face, text: str, px: float):
    """Return (glyphs, advance_width) where glyphs are (gid, x, y) in pixels."""
    buf = hb.Buffer()
    buf.add_str(text)
    buf.guess_segment_properties()
    hb.shape(face.hb_font, buf)
    k = px / face.upem
    glyphs, pen = [], 0
    for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
        glyphs.append((info.codepoint, (pen + pos.x_offset) * k, -pos.y_offset * k))
        pen += pos.x_advance
    return glyphs, pen * k


def measure(text: str, px: float, latin: str, kannada: str) -> float:
    total = 0.0
    for kn, part in runs(text):
        _, w = shape(Face(kannada if kn else latin), part, px)
        total += w
    return total


def draw_text(
    img: Image.Image,
    xy: tuple[float, float],
    text: str,
    px: float,
    color,
    latin: str,
    kannada: str,
    anchor: str = "ls",
    tracking: float = 0.0,
):
    """Draw shaped text. `anchor` follows Pillow's convention loosely: the
    first letter is horizontal (l/m/r), the second is always the baseline."""
    x, y = xy
    width = measure(text, px, latin, kannada) + tracking * max(0, len(text) - 1)
    if anchor[0] == "m":
        x -= width / 2
    elif anchor[0] == "r":
        x -= width

    layer = Image.new("L", img.size, 0)
    for kn, part in runs(text):
        face = Face(kannada if kn else latin)
        face.ft.set_char_size(int(round(px * 64)))
        glyphs, adv = shape(face, part, px)
        # Tracking is only safe on Latin: adding it between Kannada glyphs
        # would push combining marks (vowel signs, vattu, reph) off their base.
        step = 0.0 if kn else tracking
        extra = 0.0
        for gid, gx, gy in glyphs:
            face.ft.load_glyph(gid, freetype.FT_LOAD_RENDER | freetype.FT_LOAD_TARGET_NORMAL)
            slot = face.ft.glyph
            bmp = slot.bitmap
            if bmp.width and bmp.rows:
                buf = bytes(bytearray(bmp.buffer))
                if bmp.pitch != bmp.width:  # normalise padded rows
                    buf = b"".join(
                        buf[r * bmp.pitch : r * bmp.pitch + bmp.width]
                        for r in range(bmp.rows)
                    )
                g = Image.frombytes("L", (bmp.width, bmp.rows), buf)
                px_x = int(round(x + gx + extra + slot.bitmap_left))
                px_y = int(round(y + gy - slot.bitmap_top))
                box = (px_x, px_y, px_x + bmp.width, px_y + bmp.rows)
                # Lighten-composite so overlapping marks add to, rather than
                # punch holes in, the glyphs already drawn.
                layer.paste(ImageChops.lighter(layer.crop(box), g), (px_x, px_y))
            extra += step
        x += adv + step * len(part)

    img.paste(Image.new("RGB", img.size, color), (0, 0), layer)
    return width


def wrap(text: str, px: float, max_w: float, latin: str, kannada: str) -> list[str]:
    words, lines, cur = text.split(" "), [], ""
    for word in words:
        trial = f"{cur} {word}".strip()
        if cur and measure(trial, px, latin, kannada) > max_w:
            lines.append(cur)
            cur = word
        else:
            cur = trial
    if cur:
        lines.append(cur)
    return lines


# ------------------------------------------------------------- book data ---
def read_meta() -> dict:
    """Pull the `meta` block out of content/book.js without running JS."""
    src = open(os.path.join(ROOT, "content", "book.js"), encoding="utf-8").read()
    block = src[src.index("meta:") : src.index("chapters:")]
    out = {}
    for key in ("title", "subtitle", "author", "blurb", "cover"):
        m = re.search(key + r"\s*:\s*\n?\s*\"((?:[^\"\\]|\\.)*)\"", block)
        if m:
            out[key] = m.group(1).encode().decode("unicode_escape").encode("latin-1").decode("utf-8")
    m = re.search(r"year\s*:\s*(\d{4})", block)
    if m:
        out["year"] = m.group(1)
    # Count numbered chapters only - preface/afterword are in the reading
    # order but are not chapters, the same rule assets/js/app.js applies.
    sections = re.split(r"^\s{4}\{", src[src.index("chapters:"):], flags=re.M)[1:]
    out["chapters"] = str(
        sum(
            1
            for s in sections
            if not re.search(r'type\s*:\s*"(preface|afterword|frontmatter|backmatter)"', s)
        )
    )
    return out


# --------------------------------------------------------------- drawing ---
def rounded_shadow(size, radius, blur, spread=0, opacity=70):
    w, h = size
    pad = blur * 3
    shadow = Image.new("L", (w + pad * 2, h + pad * 2), 0)
    ImageDraw.Draw(shadow).rounded_rectangle(
        (pad - spread, pad - spread, pad + w + spread, pad + h + spread),
        radius=radius,
        fill=opacity,
    )
    return shadow.filter(ImageFilter.GaussianBlur(blur)), pad


def build_preview(meta: dict) -> Image.Image:
    w, h = W * SCALE, H * SCALE
    img = Image.new("RGB", (w, h), PAPER)

    # --- paper: soft diagonal wash from paper -> paper-2 ---------------------
    grad = Image.new("L", (64, 64))
    gd = grad.load()
    for y in range(64):
        for x in range(64):
            gd[x, y] = int(255 * min(1, (x / 64 * 0.55 + y / 64 * 0.65)))
    img.paste(Image.new("RGB", (w, h), PAPER_2), (0, 0), grad.resize((w, h), Image.BICUBIC))

    # ember glow behind the cover, echoing the artwork
    glow = Image.new("L", (w, h), 0)
    ImageDraw.Draw(glow).ellipse(
        (int(w * 0.60), int(-h * 0.25), int(w * 1.25), int(h * 1.05)), fill=46
    )
    img.paste(
        Image.new("RGB", (w, h), EMBER),
        (0, 0),
        glow.filter(ImageFilter.GaussianBlur(90 * SCALE)),
    )

    d = ImageDraw.Draw(img)

    # --- cover card on the right (the site's open-book spread, right page) ---
    cw, ch = 336 * SCALE, 504 * SCALE
    cx, cy = w - 76 * SCALE - cw, (h - ch) // 2
    shadow, pad = rounded_shadow((cw, ch), 6 * SCALE, 16 * SCALE, spread=2 * SCALE, opacity=90)
    img.paste(Image.new("RGB", (w, h), (58, 44, 34)), (0, 0),
              shadow.crop((pad - cx, pad - cy - 6 * SCALE, pad - cx + w, pad - cy - 6 * SCALE + h)))

    cover_path = os.path.join(ROOT, meta.get("cover") or "assets/img/mainpage.jpg")
    cover = Image.open(cover_path).convert("RGB")
    ratio = max(cw / cover.width, ch / cover.height)
    cover = cover.resize(
        (max(cw, int(cover.width * ratio)), max(ch, int(cover.height * ratio))), Image.LANCZOS
    )
    left = (cover.width - cw) // 2
    top = int((cover.height - ch) * 0.34)  # bias up: keeps the title art in frame
    cover = cover.crop((left, top, left + cw, top + ch))

    mask = Image.new("L", (cw, ch), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, cw - 1, ch - 1), radius=6 * SCALE, fill=255)
    img.paste(cover, (cx, cy), mask)
    d.rounded_rectangle(
        (cx, cy, cx + cw - 1, cy + ch - 1), radius=6 * SCALE,
        outline=(255, 253, 248, 60), width=max(1, SCALE),
    )
    # book gutter / spine hint down the inner edge
    d.rectangle((cx, cy, cx + 3 * SCALE, cy + ch), fill=(24, 16, 12))

    # --- text column on the left --------------------------------------------
    x = 76 * SCALE
    text_w = cx - 56 * SCALE - x

    # eyebrow
    y = 132 * SCALE
    draw_text(
        img, (x, y), meta["author"], 20 * SCALE, EMBER,
        SANS_LATIN, SANS_KN, tracking=1.2 * SCALE,
    )

    # title
    y += 68 * SCALE
    title_px = 76 * SCALE
    while measure(meta["title"], title_px, SERIF_LATIN, SERIF_KN_BOLD) > text_w:
        title_px -= 2 * SCALE
    draw_text(img, (x, y), meta["title"], title_px, INK, SERIF_LATIN, SERIF_KN_BOLD)

    # ember rule
    y += 34 * SCALE
    d.rectangle((x, y, x + 88 * SCALE, y + 3 * SCALE), fill=EMBER)

    # subtitle (wrapped)
    y += 46 * SCALE
    sub_px = 27 * SCALE
    for line in wrap(meta["subtitle"], sub_px, text_w, SERIF_LATIN_REG, SERIF_KN_REG)[:2]:
        draw_text(img, (x, y), line, sub_px, INK_SOFT, SERIF_LATIN_REG, SERIF_KN_REG)
        y += 42 * SCALE

    # pull-quote from the preface
    y += 14 * SCALE
    quote = "\u201Cಸತ್ಯ ಬೇಕಿರುವವರು ಮಾತ್ರ ಓದಿ.\u201D"
    draw_text(img, (x, y), quote, 25 * SCALE, EMBER, SERIF_LATIN_REG, SERIF_KN_REG)

    # footer strip: chapters + host
    fy = h - 74 * SCALE
    d.rectangle((x, fy - 40 * SCALE, cx - 56 * SCALE, fy - 40 * SCALE + max(1, SCALE)), fill=RULE)
    foot = f"ಆನ್\u200Cಲೈನ್ ಓದುಗ  ·  {meta['chapters']} chapters  ·  free to read"
    draw_text(img, (x, fy), foot, 19 * SCALE, INK_SOFT, SANS_LATIN_REG, SANS_KN_REG)
    draw_text(
        img, (x, fy + 32 * SCALE), "prathvirajkodachadri.github.io/nannolagina-devaru",
        17 * SCALE, INK_FAINT, SANS_LATIN_REG, SANS_KN_REG, tracking=0.4 * SCALE,
    )

    return img.resize((W, H), Image.LANCZOS)


def build_icon(px: int) -> Image.Image:
    """The header brand-mark from style.css, as an icon: a 26x32 ember book
    with a 160deg gradient, rounded 3/6/6/3 corners, and an inset highlight
    down the spine - sitting on the site's warm paper."""
    s = 8
    n = px * s
    img = Image.new("RGB", (n, n), PAPER)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((0, 0, n - 1, n - 1), radius=int(n * 0.20), fill=PAPER)

    # book body, 26:32 like .brand-mark, centred with breathing room
    bh = int(n * 0.74)
    bw = int(bh * 26 / 32)
    bx, by = (n - bw) // 2, (n - bh) // 2

    # linear-gradient(160deg, ember, #7d3d1f)
    grad = Image.new("L", (bw, bh))
    gp = grad.load()
    for yy in range(bh):
        for xx in range(bw):
            t = (xx / bw) * 0.34 + (yy / bh) * 0.94
            gp[xx, yy] = max(0, min(255, int(t * 255)))
    body = Image.new("RGB", (bw, bh), EMBER)
    body.paste(Image.new("RGB", (bw, bh), (125, 61, 31)), (0, 0), grad)

    mask = Image.new("L", (bw, bh), 0)
    r = max(1, int(bw * 0.10))
    md = ImageDraw.Draw(mask)
    md.rounded_rectangle((0, 0, bw - 1, bh - 1), radius=r * 2, fill=255)
    md.rectangle((0, 0, r * 2, bh - 1), fill=0)
    md.rounded_rectangle((0, 0, r * 3, bh - 1), radius=r, fill=255)

    # inset 3px 0 0 rgba(255,255,255,.35) highlight on the spine
    spine = max(1, int(bw * 0.115))
    body.paste(Image.new("RGB", (spine, bh), (255, 255, 255)),
               (0, 0), Image.new("L", (spine, bh), 90))

    shadow, pad = rounded_shadow((bw, bh), r * 2, int(n * 0.02), opacity=52)
    img.paste(Image.new("RGB", (n, n), (110, 70, 45)), (0, 0),
              shadow.crop((pad - bx, pad - by - int(n * 0.012),
                           pad - bx + n, pad - by - int(n * 0.012) + n)))
    img.paste(body, (bx, by), mask)

    # ನ - the first letter of the title, so the icon still reads as *this*
    # book at 16px rather than as a generic brown rectangle.
    glyph_px = bh * 0.60
    gw = measure("ನ", glyph_px, SERIF_KN_BOLD, SERIF_KN_BOLD)
    draw_text(
        img,
        (bx + spine + (bw - spine) / 2 - gw / 2, by + bh * 0.72),
        "ನ", glyph_px, (255, 247, 238), SERIF_KN_BOLD, SERIF_KN_BOLD,
    )
    return img.resize((px, px), Image.LANCZOS)


def main() -> None:
    meta = read_meta()
    print("book:", meta["title"], "/", meta["author"], "/", meta["chapters"], "chapters")

    out = os.path.join(ROOT, "preview.jpg")
    card = build_preview(meta)
    # WhatsApp only renders a large preview for images it will actually fetch,
    # and it is the strictest of the crawlers about weight - keep it well under
    # 300 KB while staying visually clean.
    for quality in (92, 88, 84, 80, 76, 72):
        card.save(out, "JPEG", quality=quality, optimize=True, progressive=False,
                  subsampling=1)
        if os.path.getsize(out) <= 290_000:
            break
    print(f"preview.jpg  {card.size[0]}x{card.size[1]}  "
          f"{os.path.getsize(out) / 1024:.0f} KB  q={quality}")

    icon = build_icon(256)
    icon.save(os.path.join(ROOT, "favicon.ico"), sizes=[(16, 16), (32, 32), (48, 48)])
    build_icon(32).save(os.path.join(ROOT, "favicon-32x32.png"), optimize=True)
    build_icon(16).save(os.path.join(ROOT, "favicon-16x16.png"), optimize=True)
    build_icon(180).save(os.path.join(ROOT, "apple-touch-icon.png"), optimize=True)
    print("favicon.ico, favicon-32x32.png, favicon-16x16.png, apple-touch-icon.png")


if __name__ == "__main__":
    main()
