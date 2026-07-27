"""Recover correct Kannada Unicode text from the Tunga-embedded PDF.

The PDF (MS Word 2013 export) has a broken ToUnicode CMap: conjuncts and
reordered vowel signs decode to wrong codepoints. The embedded font, however,
still carries a valid `cmap` and full GSUB tables, so we can map each rendered
glyph id back to the base glyphs it was composed from, then to Unicode.
"""
import io
import json
import re
import sys
import unicodedata

import fitz
from fontTools.ttLib import TTFont


def fill_linear_gaps(uni):
    """Tunga lays the Kannada block out contiguously in glyph order.

    Subset fonts only keep a `cmap` for the codepoints actually used, so glyphs
    such as the vowel sign U+0CBF can be missing even though they are drawn.
    Where two known anchors are separated by an equal number of glyph ids and
    codepoints the run is linear, so the interior entries can be filled in.
    """
    kn = sorted((g, c) for g, c in uni.items() if 0x0C80 <= c <= 0x0CFF)
    for (g1, c1), (g2, c2) in zip(kn, kn[1:]):
        if g2 - g1 == c2 - c1 and 1 < g2 - g1 <= 6:
            for k in range(1, g2 - g1):
                uni.setdefault(g1 + k, c1 + k)
    return uni


def build_tables(font_bytes):
    t = TTFont(io.BytesIO(font_bytes), fontNumber=0, lazy=False)
    order = t.getGlyphOrder()
    gid = {gn: i for i, gn in enumerate(order)}
    uni = {}
    for cp, gn in t.getBestCmap().items():
        uni.setdefault(gid[gn], cp)

    rev_lig, rev_sing, rev_mult = {}, {}, {}
    below = set()
    if "GSUB" in t:
        g = t["GSUB"].table

        # glyphs produced by the `blwf` feature are below-base (vattu) forms;
        # anything else that renders as consonant+virama is a reph.
        blwf_lookups = set()
        for fr in g.FeatureList.FeatureRecord:
            if fr.FeatureTag == "blwf":
                blwf_lookups.update(fr.Feature.LookupListIndex)
        for li in blwf_lookups:
            lk = g.LookupList.Lookup[li]
            for st in lk.SubTable:
                if lk.LookupType == 1 and hasattr(st, "mapping"):
                    below.update(gid[v] for v in st.mapping.values())
                elif lk.LookupType == 4 and hasattr(st, "ligatures"):
                    for first, ls in st.ligatures.items():
                        for lg in ls:
                            below.add(gid[lg.LigGlyph])

        for lk in g.LookupList.Lookup:
            for st in lk.SubTable:
                if lk.LookupType == 4 and hasattr(st, "ligatures"):
                    for first, ls in st.ligatures.items():
                        for lg in ls:
                            comps = tuple([gid[first]] + [gid[c] for c in lg.Component])
                            rev_lig.setdefault(gid[lg.LigGlyph], comps)
                elif lk.LookupType == 1 and hasattr(st, "mapping"):
                    for a, b in st.mapping.items():
                        rev_sing.setdefault(gid[b], gid[a])
                elif lk.LookupType == 2 and hasattr(st, "mapping"):
                    for a, seq in st.mapping.items():
                        rev_mult.setdefault(gid[a], tuple(gid[s] for s in seq))
    fill_linear_gaps(uni)
    return uni, rev_lig, rev_sing, rev_mult, below


def decompose(g, uni, rev_lig, rev_sing, rev_mult, depth=0):
    """Expand a glyph id into a list of base glyph ids that have Unicode."""
    if depth > 12:
        return [g]
    if g in uni:
        return [g]
    if g in rev_lig:
        out = []
        for c in rev_lig[g]:
            out.extend(decompose(c, uni, rev_lig, rev_sing, rev_mult, depth + 1))
        return out
    if g in rev_mult:
        out = []
        for c in rev_mult[g]:
            out.extend(decompose(c, uni, rev_lig, rev_sing, rev_mult, depth + 1))
        return out
    if g in rev_sing:
        return decompose(rev_sing[g], uni, rev_lig, rev_sing, rev_mult, depth + 1)
    return [g]


# ---------------------------------------------------------------- reordering
# Glyph decomposition yields *visual* order. Kannada logical order differs in
# two ways that must be repaired:
#   1. the vowel sign U+0CBF (and e/ai signs) are drawn before their consonant
#   2. a below-base consonant (vattu) is drawn after the base + its vowel sign,
#      but logically belongs immediately after the base as  virama + consonant
CONS_LO, CONS_HI = 0x0C95, 0x0CB9
VIRAMA = 0x0CCD
NUKTA = 0x0CBC
MATRAS = set(range(0x0CBE, 0x0CD7)) - {VIRAMA}
ANUSVARA = {0x0C82, 0x0C83}
RA = 0x0CB0
REPH = -1        # sentinel: reph drawn after the cluster, logically leads it
VATTU_BASE = -2  # sentinel range: VATTU_BASE - cp encodes a below-base form


def vattu(cp):
    return VATTU_BASE - cp


def is_vattu(x):
    return x <= VATTU_BASE


def is_cons(cp):
    return CONS_LO <= cp <= CONS_HI


def post_clean(text):
    """Repair the few conjuncts the shaper reorders beyond glyph decomposition."""
    # ka + ssa (ksha): rendered as ka, ssa-with-virama -> ka virama ssa
    text = re.sub(r"ಕಷ್([\u0CBE-\u0CD6])", r"ಕ್ಷ\1", text)
    text = re.sub(r"ಕಷ್(?![\u0C95-\u0CB9])", "ಕ್ಷ", text)
    # sa + ka + vocalic-r (samskruta): the vocalic sign lands after the virama
    text = re.sub("([\u0C95-\u0CB9])\u0CCD\u0CC3", "\u0CCD\\1\u0CC3", text)
    # a doubled virama is never valid
    text = re.sub(r"\u0CCD{2,}", "\u0CCD", text)
    return text


def fix_order(cps):
    """Convert a visually ordered codepoint run into logical Kannada order."""
    out = []
    i = 0
    n = len(cps)
    while i < n:
        cp = cps[i]
        if cp == REPH:
            # stray reph with no following base - emit literally
            out.extend([RA, VIRAMA])
            i += 1
            continue
        if is_vattu(cp):
            # vattu with no preceding base
            out.extend([VIRAMA, VATTU_BASE - cp])
            i += 1
            continue
        if is_cons(cp):
            base = cp
            i += 1
            matras = []
            marks = []
            vattus = []
            reph = False
            # gather everything attached to this base
            while i < n:
                c = cps[i]
                if c == REPH:
                    reph = True
                    i += 1
                elif is_vattu(c):
                    # below-base consonant: logically virama + consonant
                    vattus.extend([VIRAMA, VATTU_BASE - c])
                    i += 1
                elif c in MATRAS or c == NUKTA:
                    matras.append(c)
                    i += 1
                elif c in ANUSVARA:
                    marks.append(c)
                    i += 1
                elif c == VIRAMA:
                    # true halant ending the cluster
                    vattus.append(VIRAMA)
                    i += 1
                    break
                else:
                    break
            if reph:
                out.extend([RA, VIRAMA])
            out.append(base)
            out.extend(vattus)
            out.extend(matras)
            out.extend(marks)
            continue
        out.append(cp)
        i += 1
    return out


def page_text(page, cache):
    lines = []
    for span in page.get_texttrace():
        font = span.get("font", "")
        chars = span.get("chars", ())
        buf = []
        for ch in chars:
            ucs, gid_ = ch[0], ch[1]
            if gid_ is None or gid_ < 0:
                continue
            tabs = cache.get(font)
            if tabs is None:
                if ucs > 0:
                    buf.append(ucs)
                continue
            uni, rl, rs, rm, below = tabs
            if gid_ in uni:
                buf.append(uni[gid_])
                continue
            parts = decompose(gid_, uni, rl, rs, rm)
            cps = [uni[p] for p in parts if p in uni]
            # ra + virama that is NOT a below-base form is a reph: it renders
            # after the cluster but logically precedes the base consonant.
            if len(cps) == 2 and cps[1] == VIRAMA and is_cons(cps[0]):
                if gid_ in below:
                    buf.append(vattu(cps[0]))       # below-base form
                elif cps[0] == RA:
                    buf.append(REPH)                # reph
                else:
                    buf.extend(cps)                 # explicit halant
            elif (
                len(cps) >= 3
                and cps[-1] == VIRAMA
                and all(is_cons(c) for c in cps[:-1])
            ):
                # akhand conjunct (ja+nya -> ja virama nya): the shaper moved
                # the virama to the end, so re-interleave it between bases.
                merged_cluster = [cps[0]]
                for c in cps[1:-1]:
                    merged_cluster.extend([VIRAMA, c])
                buf.extend(merged_cluster)
            else:
                buf.extend(cps)
        text = post_clean("".join(chr(c) for c in fix_order(buf)))
        lines.append((text, span["bbox"], font, span.get("size")))
    return lines


def main(pdf_path, out_path):
    doc = fitz.open(pdf_path)

    # The same logical font is embedded several times as different subsets
    # (ABCDEE+Tunga, ABCEEE+Tunga, ...). They share one glyph order, so merge
    # every subset of a given base family into a single lookup table.
    merged = {}
    seen_xrefs = set()
    for page in doc:
        for f in page.get_fonts(full=True):
            xref, name = f[0], f[3]
            if xref in seen_xrefs:
                continue
            seen_xrefs.add(xref)
            try:
                data = doc.extract_font(xref)[3]
                if not data:
                    continue
                uni, rl, rs, rm, below = build_tables(data)
            except Exception as e:
                print("font fail", name, e, file=sys.stderr)
                continue
            short = name.split("+")[-1]
            acc = merged.setdefault(short, ({}, {}, {}, {}, set()))
            for dst, src in zip(acc, (uni, rl, rs, rm)):
                for k, v in src.items():
                    dst.setdefault(k, v)
            acc[4].update(below)
    cache = merged

    pages = []
    for pno in range(doc.page_count):
        page = doc[pno]
        spans = page_text(page, cache)
        width = page.rect.width

        # Most body pages are typeset in two columns. Detect a real gutter by
        # looking for a wide vertical band of the page that no span touches;
        # single-column pages (title, preface) have no such band.
        covered = bytearray(int(width) + 2)
        for _t, bbox, _f, _s in spans:
            if bbox[2] - bbox[0] <= 1:
                continue
            for x in range(max(0, int(bbox[0])), min(len(covered) - 1, int(bbox[2]))):
                covered[x] = 1
        gutter = None
        run_start = None
        for x in range(int(width * 0.25), int(width * 0.75)):
            if not covered[x]:
                if run_start is None:
                    run_start = x
            else:
                if run_start is not None and x - run_start >= 18:
                    gutter = (run_start + x) / 2
                run_start = None
        two_col = gutter is not None
        if two_col:
            left = [s for s in spans if s[1][0] < gutter]
            right = [s for s in spans if s[1][0] >= gutter]
            two_col = len(left) > 3 and len(right) > 3

        def rows_of(items):
            rows = {}
            for text, bbox, font, size in items:
                if not text.strip():
                    continue
                rows.setdefault(round(bbox[1], 1), []).append(
                    (bbox[0], bbox[2], text, font, size)
                )
            out = []
            for y in sorted(rows):
                parts = sorted(rows[y])
                # Word 2013 splits a visual line into several spans; re-insert
                # the space that the span boundary swallowed.
                joined = ""
                prev_end = None
                for x0, x1, text, _f, _s in parts:
                    if (
                        joined
                        and not joined.endswith((" ", "(", "\u201c", "-", "\u2014"))
                        and not text.startswith((" ", ")", ",", ".", "\u201d", ":", ";", "?", "!"))
                        and prev_end is not None
                        and x0 - prev_end > 0.8
                    ):
                        joined += " "
                    joined += text
                    prev_end = x1
                out.append({
                    "y": y,
                    "x": round(parts[0][0], 1),
                    "x_end": round(max(p[1] for p in parts), 1),
                    "text": joined,
                    "bold": any("Bold" in (p[3] or "") for p in parts),
                    "size": round(max((p[4] or 0) for p in parts), 1),
                })
            return out

        if two_col:
            out_lines = rows_of(left) + rows_of(right)
        else:
            out_lines = rows_of(spans)
        pages.append({"page": pno + 1, "lines": out_lines, "columns": 2 if two_col else 1})

    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(pages, fh, ensure_ascii=False, indent=1)
    print("wrote", out_path, "pages", len(pages))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
