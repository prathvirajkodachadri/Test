"""Turn the extracted page/line JSON into content/book.js.

Reads pages.json (produced by extract_pdf.py) and emits the `window.BOOK`
structure the reader expects: meta + an array of reading sections whose `body`
is a list of HTML block strings. Sections may be typed as `preface`, `chapter`
(default), or `afterword`; only real chapters are numbered in the reader.
"""
import json
import re
from collections import Counter
import sys

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IMAGE_DIR = ROOT / "assets" / "img" / "chapters"
BOOK_JS = ROOT / "content" / "book.js"

META = {
    "title": "ನನ್ನೊಳಗಿನ ದೇವರು",
    "subtitle": "ಭಯದಿಂದ ಅರಿವಿನೆಡೆಗೆ — ಹದಿನಾಲ್ಕು ಅಧ್ಯಾಯಗಳಲ್ಲಿ",
    "author": "ಪೃಥ್ವಿರಾಜ್ ಕೊಡಚಾದ್ರಿ",
    "year": 2026,
    "blurb": (
        "\"ಸತ್ಯ ಬೇಕಿರುವವರು ಮಾತ್ರ ಓದಿ. ಸುಳ್ಳಲ್ಲಿ ಸುಖ ಕಾಣುತ್ತಿರುವವರು ದಯವಿಟ್ಟು "
        "ಓದಬೇಡಿ.\" ದೇವರನ್ನು ಹುಡುಕಲು ಹಿಮಾಲಯಕ್ಕಲ್ಲ, ಕನ್ನಡಿಯ ಮುಂದೆ ನಿಂತರೆ ಸಾಕು "
        "ಎಂಬ ಕಟುಸತ್ಯವನ್ನು ಮೆದುಳಿನ ವಿಜ್ಞಾನದ ಮೂಲಕ ಶೋಧಿಸುವ ಪುಸ್ತಕ."
    ),
    "cover": "assets/img/mainpage.jpg",
}

AFTERWORD = {
    "type": "afterword",
    "label": "Afterword",
    "title": "ಹಿನ್ನುಡಿ",
    "body": [
        '<p>ಪುಸ್ತಕದ ಮುನ್ನುಡಿಯಲ್ಲಿ ನಾನು ನಿಮಗೊಂದು ಎಚ್ಚರಿಕೆ ನೀಡಿದ್ದೆ—"ಸತ್ಯ ಬೇಕಿರುವವರು ಮಾತ್ರ ಓದಿ" ಎಂದು. ಈಗ ನೀವು ಈ ಕೊನೆಯ ಪುಟವನ್ನು ತಲುಪಿದ್ದೀರಿ ಎಂದರೆ, ನನ್ನಂತೆಯೇ ಸತ್ಯ ಹುಡುಕವ ಹಸಿವಿದ್ದ ಸಹಪಯಣಿಗರು.</p>',
        "<p>ಕಲ್ಪನೆಯ ದೇವರನ್ನು ಕಳೆದುಕೊಂಡು, ವಾಸ್ತವದ ನಮ್ಮೊಳಗಿನ ದೇವರನ್ನು ನಾವು ಕಂಡುಕೊಳ್ಳುವ ಈ ಪಯಣದಲ್ಲಿ ನನ್ನೊಡನೆ ಹೆಜ್ಜೆ ಹಾಕಿದ ನಿಮಗೆ ಅನಂತ ಧನ್ಯವಾದಗಳು.</p>",
        '<p class="signature">ಪ್ರೀತಿಯಿಂದ,<br>ಪೃಥ್ವಿರಾಜ್ ಕೊಡಚಾದ್ರಿ</p>',
    ],
}

# The PDF runs the preface's closing sign-off into the last paragraph. Pull it
# out into its own right-aligned `.signature` block, the same way the afterword
# ends.
SIGNOFF_RE = re.compile(
    r"(\u0caa\u0ccd\u0cb0\u0cbf\u0cd5\u0ca4\u0cbf\u0caf\u0cbf\u0c82\u0ca6[^<]*?)\s*"
    r"(\u0caa\u0cc3\u0ca5\u0ccd\u0cb5\u0cbf\u0cb0\u0cbe\u0c9c\u0ccd\s+\u0c95\u0cca\u0ca1\u0c9a\u0cbe\u0ca6\u0ccd\u0cb0\u0cbf)\s*$"
)


def split_signature(body):
    """Split a trailing "ಪ್ರೀತಿಯಿಂದ ... <name>" sign-off into its own block."""
    if not body:
        return body
    last = body[-1]
    if not (last.startswith("<p>") and last.endswith("</p>")):
        return body
    inner = last[3:-4]
    m = SIGNOFF_RE.search(inner)
    if not m:
        return body
    lead = inner[:m.start()].strip()
    salutation, name = m.group(1).strip().rstrip(","), m.group(2).strip()
    out = body[:-1]
    if lead:
        out.append("<p>" + lead + "</p>")
    out.append('<p class="signature">%s,<br>%s</p>' % (salutation, name))
    return out


KANNADA_DIGITS = "೦೧೨೩೪೫೬೭೮೯"


def kn_int(s):
    out = 0
    for ch in s:
        out = out * 10 + KANNADA_DIGITS.index(ch)
    return out


CH_RE = re.compile(r"^ಅಧ್ಯಾಯ\s*([೦-೯]+)\s*:?\s*$")
# a numbered section heading such as "೩. ಭಯಕ್ಕೆ ಒಂದು ಮುಖ (Giving a Face to Fear)"
SEC_RE = re.compile(r"^([೦-೯]+)\.\s*(\S.*)$")
BULLET_CHARS = "\uf0b7\u2022\u25cf\u00b7"


# Word-final Latin loanwords lose their closing halant in the PDF's glyph
# stream, and a couple of names/conjuncts come out transposed. These are the
# recurring tokens; each was checked against the rendered page.
FIXUPS = {
    "ಪೃಥಿವ್ರಾಜ್": "ಪೃಥ್ವಿರಾಜ್",
    "ಸೂಕ್ಷಮ್ದರ್ಶಕ": "ಸೂಕ್ಷ್ಮದರ್ಶಕ",
    "ಕಾರ್ಟೆಕ್ಸ": "ಕಾರ್ಟೆಕ್ಸ್",
    "ಕಾರ್ಟೆಕ್ಸ್್": "ಕಾರ್ಟೆಕ್ಸ್",
    "ರೀಲ್ಸ ": "ರೀಲ್ಸ್ ",
    "ರಿಸ್ಕ ": "ರಿಸ್ಕ್ ",
    "ಎಫೆಕ್ಟ": "ಎಫೆಕ್ಟ್",
    "ಎಫೆಕ್ಟ್್": "ಎಫೆಕ್ಟ್",
    "ಕರೆಕ್ಟ ": "ಕರೆಕ್ಟ್ ",
    "ಝೆನೋಫೇನ್ಸ": "ಝೆನೋಫೇನ್ಸ್",
    "ಎಸ್ತೆಟಿಕ್ಸ": "ಎಸ್ತೆಟಿಕ್ಸ್",
    "ಪ್ರಮೋಷನ್ ": "ಪ್ರಮೋಷನ್ ",
}


def apply_fixups(text):
    for bad, good in FIXUPS.items():
        text = text.replace(bad, good)
    # never leave a doubled halant behind
    return re.sub("\u0CCD{2,}", "\u0CCD", text)


def clean(text):
    text = text.replace("\uf0b7", "\u2022")
    text = re.sub(r"[ \t\u00a0]+", " ", text)
    return apply_fixups(text.strip())


def is_bullet(line):
    return line.lstrip().startswith(("\u2022", "\u25cf"))


def esc(s):
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def flatten(pages, from_page):
    """All non-empty lines from `from_page` onward as one ordered stream."""
    out = []
    for pg in pages[from_page:]:
        for ln in pg["lines"]:
            t = clean(ln["text"])
            if t:
                out.append({
                    "text": t,
                    "bold": ln["bold"],
                    "size": ln["size"],
                    "x": ln.get("x", 0),
                    "x_end": ln.get("x_end", 0),
                })
    # A first-line indent is the reliable paragraph marker in this layout
    # (column line-ends are ragged, so a short previous line means nothing).
    # Indent must be measured against the line's own column, not the page.
    if out:
        # Column origins are the *most common* left edges, not the smallest:
        # centred headings and stray glyphs sit further left/right than the body.
        counts = Counter(l["x"] for l in out)
        left0 = min(counts, key=lambda x: (-counts[x], x))
        right_candidates = {x: n for x, n in counts.items() if x > left0 + 100}
        right0 = (
            min(right_candidates, key=lambda x: (-right_candidates[x], x))
            if right_candidates
            else None
        )

        def column_origin(x):
            if right0 is not None and x >= right0 - 6:
                return right0
            return left0

        for l in out:
            indent = l["x"] - column_origin(l["x"])
            l["starts_para"] = 6 < indent < 60
    return out


def split_chapters(stream):
    """Split the line stream at each 'ಅಧ್ಯಾಯ N' heading.

    Headings do not always start a page, so we cut on line position rather
    than page boundaries.
    """
    marks = []
    for i, ln in enumerate(stream):
        m = CH_RE.match(ln["text"])
        if m:
            marks.append((i, kn_int(m.group(1))))
    # keep the first occurrence of each chapter number
    seen, cuts = set(), []
    for i, num in marks:
        if num in seen:
            continue
        seen.add(num)
        cuts.append((i, num))
    cuts.sort()

    out = []
    for idx, (start, num) in enumerate(cuts):
        end = cuts[idx + 1][0] if idx + 1 < len(cuts) else len(stream)
        out.append((num, stream[start:end]))
    return out


PARTS = [
    (1, 4, "ಭಾಗ ೧ — ಭಯ ಮತ್ತು ಮೆದುಳು"),
    (5, 7, "ಭಾಗ ೨ — ಕನ್ನಡಿ ಮತ್ತು ಸಮಾಜ"),
    (8, 11, "ಭಾಗ ೩ — ರಸಾಯನ ಮತ್ತು ಧರ್ಮ"),
    (12, 14, "ಭಾಗ ೪ — ಸೌಂದರ್ಯ ಮತ್ತು ಅರಿವು"),
]


def part_for(num):
    for lo, hi, label in PARTS:
        if lo <= num <= hi:
            return label
    return ""


def title_of(lines, num):
    """The chapter title is the bold line(s) right after 'ಅಧ್ಯಾಯ N'."""
    parts = []
    for ln in lines[1:5]:
        t = ln["text"]
        if not ln["bold"] or t.startswith(("\u201c", '"')) or SEC_RE.match(t):
            break
        parts.append(t)
    return " ".join(parts) if parts else f"ಅಧ್ಯಾಯ {num}"


def collect_lines(pages, start, end):
    out = []
    for pg in pages[start:end]:
        for ln in pg["lines"]:
            t = clean(ln["text"])
            if not t:
                continue
            out.append({"text": t, "bold": ln["bold"], "size": ln["size"]})
    return out


def join_paragraph(buf):
    """Join wrapped lines into one paragraph."""
    text = " ".join(buf)
    text = re.sub(r"\s+", " ", text).strip()
    # a stray space before Kannada punctuation / closing marks
    text = re.sub(r"\s+([,.;:!?\)\]\u201d])", r"\1", text)
    text = re.sub(r"([\(\[\u201c])\s+", r"\1", text)
    return text


def build_body(lines, chapter_title):
    """Convert a chapter's lines into an ordered list of HTML block strings."""
    blocks = []
    para = []
    bullets = []

    def flush_para():
        nonlocal para
        if para:
            t = join_paragraph(para)
            if t:
                blocks.append("<p>" + esc(t) + "</p>")
            para = []

    def flush_bullets():
        nonlocal bullets
        if bullets:
            items = "".join("<li>" + esc(join_paragraph([b])) + "</li>" for b in bullets)
            blocks.append("<ul>" + items + "</ul>")
            bullets = []

    i = 0
    n = len(lines)
    skip_head = True
    while i < n:
        ln = lines[i]
        t = ln["text"]

        # drop the running chapter header lines at the very top
        if skip_head:
            if CH_RE.match(t) or t == chapter_title:
                i += 1
                continue
            skip_head = False

        if CH_RE.match(t):
            i += 1
            continue

        # numbered section heading
        m = SEC_RE.match(t)
        if m and ln["bold"] and len(t) < 160:
            flush_para()
            flush_bullets()
            head = t
            i += 1
            # a heading can wrap across a column break, leaving the tail of a
            # parenthesised gloss on the next line
            while i < n and head.count("(") > head.count(")"):
                head = head.rstrip() + " " + lines[i]["text"].strip()
                i += 1
            blocks.append("<h3>" + esc(re.sub(r"\s+", " ", head).strip()) + "</h3>")
            continue

        # bullet item
        if is_bullet(t):
            flush_para()
            body = t.lstrip("".join("\u2022\u25cf")).strip()
            j = i + 1
            while j < n and not is_bullet(lines[j]["text"]) and not SEC_RE.match(lines[j]["text"]):
                nxt = lines[j]["text"]
                if len(nxt) < 3:
                    break
                body += " " + nxt
                j += 1
                if j < n and lines[j]["bold"] != ln["bold"]:
                    break
            bullets.append(body)
            i = j
            continue

        # explicit paragraph break detected from the layout
        if para and ln.get("starts_para"):
            flush_para()

        flush_bullets()

        # a short, fully-bold line that is quoted -> pull-quote
        if ln["bold"] and t.startswith(("\u201c", '"')) and len(t) < 400:
            flush_para()
            quote = [t]
            j = i + 1
            while j < n and lines[j]["bold"] and not SEC_RE.match(lines[j]["text"]):
                quote.append(lines[j]["text"])
                j += 1
                if quote[-1].rstrip().endswith(("\u201d", '"')):
                    break
            blocks.append("<blockquote>" + esc(join_paragraph(quote)) + "</blockquote>")
            i = j
            continue

        para.append(t)
        i += 1

    flush_para()
    flush_bullets()
    return blocks


def main(pages_path, out_path):
    pages = json.load(open(pages_path, encoding="utf-8"))

    # page index 3 is the preface (ಮುನ್ನುಡಿ); chapters follow
    stream = flatten(pages, 3)
    first_ch = next(i for i, ln in enumerate(stream) if CH_RE.match(ln["text"]))

    chapters = []
    intro = stream[:first_ch]
    if intro:
        chapters.append({
            "type": "preface",
            "label": "Preface",
            "title": "ಮುನ್ನುಡಿ",
            "body": split_signature(build_body(intro[1:], "ಮುನ್ನುಡಿ")),
        })

    for num, lines in split_chapters(stream[first_ch:]):
        title = title_of(lines, num)
        # drop the heading + title lines from the body
        drop = 1 + len(title.split(" ")) if False else 1
        body_lines = lines[1:]
        while body_lines and body_lines[0]["bold"] and body_lines[0]["text"] in title:
            body_lines = body_lines[1:]
        chapters.append({
            "title": title,
            "part": part_for(num),
            "body": build_body(body_lines, title),
        })

    # If the PDF stream left the afterword inside the final chapter, trim that
    # inline copy; the reader models it as a separate back-matter section.
    if chapters:
        last = chapters[-1]
        body = last.get("body", [])
        cut = next((i for i, block in enumerate(body) if "ಹಿನ್ನುಡಿ" in block), -1)
        if cut >= 0:
            last["body"] = body[:cut] + ['<p>-ಸಮಾಪ್ತ-</p>']

    # Attach one existing illustration to each of the 14 real chapters. Preface
    # and afterword intentionally do not get chapter pictures.
    imgs = sorted(IMAGE_DIR.glob("ch*.jpg"), key=lambda q: int(re.search(r"\d+", q.name).group()))
    real_chapters = [ch for ch in chapters if ch.get("type", "chapter") == "chapter"]
    for idx, ch in enumerate(real_chapters):
        if idx < len(imgs):
            ch["image"] = "assets/img/chapters/" + imgs[idx].name
            ch["alt"] = ch["title"]

    chapters.append(dict(AFTERWORD))

    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(chapters, fh, ensure_ascii=False, indent=1)

    write_book_js(chapters, META, BOOK_JS)

    print("sections:", len(chapters))
    print("numbered chapters:", len([c for c in chapters if c.get("type", "chapter") == "chapter"]))
    for c in chapters:
        kind = c.get("type", "chapter")
        print(f"  [{kind}] {c['title'][:50]:52} blocks={len(c['body'])}")




def write_book_js(chapters, meta, out_path):
    """Emit content/book.js in the exact shape the reader expects."""
    def js(s):
        return json.dumps(s, ensure_ascii=False)

    lines = []
    lines.append("/*")
    lines.append(" * BOOK CONTENT")
    lines.append(" * ------------")
    lines.append(" * Generated from the source PDF by tools/extract_pdf.py +")
    lines.append(" * tools/build_book.py. Edit those, or this file, to change the text.")
    lines.append(" *")
    lines.append(" *   type / title / part / body  - see README.md for the full schema.")
    lines.append(" */")
    lines.append("")
    lines.append("window.BOOK = {")
    lines.append("  meta: {")
    for k in ("title", "subtitle", "author"):
        lines.append(f"    {k}: {js(meta[k])},")
    lines.append(f"    year: {meta['year']},")
    lines.append(f"    blurb:\n      {js(meta['blurb'])},")
    lines.append(f"    cover: {js(meta.get('cover', ''))}")
    lines.append("  },")
    lines.append("")
    lines.append("  chapters: [")
    for ci, ch in enumerate(chapters):
        lines.append("    {")
        if ch.get("type"):
            lines.append(f"      type: {js(ch['type'])},")
        if ch.get("label"):
            lines.append(f"      label: {js(ch['label'])},")
        lines.append(f"      title: {js(ch['title'])},")
        if ch.get("part"):
            lines.append(f"      part: {js(ch['part'])},")
        if ch.get("image"):
            lines.append(f"      image: {js(ch['image'])},")
        if ch.get("caption"):
            lines.append(f"      caption: {js(ch['caption'])},")
        if ch.get("alt"):
            lines.append(f"      alt: {js(ch['alt'])},")
        lines.append("      body: [")
        for bi, b in enumerate(ch["body"]):
            comma = "," if bi < len(ch["body"]) - 1 else ""
            lines.append(f"        {js(b)}{comma}")
        lines.append("      ]")
        lines.append("    }" + ("," if ci < len(chapters) - 1 else ""))
    lines.append("  ]")
    lines.append("};")
    lines.append("")
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    print("wrote", out_path)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
