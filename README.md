# ನನ್ನೊಳಗಿನ ದೇವರು — Book Reader

A static, dependency-free website for reading a book online. No build step, no
framework, no npm install — open `index.html` and it works.

The text is *ನನ್ನೊಳಗಿನ ದೇವರು* ("The God Within Me") by ಪೃಥ್ವಿರಾಜ್ ಕೊಡಚಾದ್ರಿ —
a preface, fourteen numbered chapters, and an afterword, in Kannada.

## Quick start

```bash
# any static server works
python3 -m http.server 8000
# then visit http://localhost:8000
```

Opening `index.html` directly from the filesystem works too.

## Publishing your own book

Everything lives in **one file**: [`content/book.js`](content/book.js).

```js
window.BOOK = {
  meta: {
    title:    "Your Title",
    subtitle: "An optional subtitle",
    author:   "Your Name",
    year:     2026,
    blurb:    "A short description shown on the cover page.",
    cover:    ""            // optional path to a cover image, e.g. "assets/cover.jpg"
  },

  chapters: [
    {
      type:  "preface",      // optional: "preface", "chapter" (default), or "afterword"
      label: "Preface",      // optional label shown above the title
      title: "ಮುನ್ನುಡಿ",
      body: [ /* ... */ ]
    },
    {
      title: "Chapter title",
      part:  "Part One",     // optional — consecutive chapters sharing a
                             // label are grouped in the contents and drawer
      image: "assets/img/chapters/ch1.jpg", // optional chapter-end picture
      body: [
        "A plain string becomes a paragraph.",
        "<blockquote>Raw HTML is passed through untouched.</blockquote>",
        "<h3>A subheading</h3>",
        "<p class=\"break\">* * *</p>"
      ]
    }
    // ...more sections
  ]
};
```

The table of contents, contents drawer, prev/next links, chapter numbering and
reading-time estimates are all generated from this data — you never edit HTML.
Sections marked `type: "preface"` or `type: "afterword"` are included in the
reading order but are not counted as numbered chapters.

Supported `body` blocks: any string starting with `<p>`, `<h1>`–`<h6>`,
`<blockquote>`, `<ul>`, `<ol>`, `<figure>`, `<img>`, `<hr>`, `<div>`,
`<section>` or `<pre>` is used verbatim. Anything else is wrapped in `<p>`.

## Features

- **Cover page** with generated book-spine artwork (or your own cover image)
- **Table of contents** with Preface, fourteen chapter numbers, Afterword, and reading times
- **Slide-out contents drawer** available from every page
- **Prev / next reading cards** at the foot of each section
- **Keyboard navigation** — `←` / `→` through Preface, chapters, and Afterword; `Esc` closes the drawer
- **Reading progress bar** in the header
- **Deep-linkable URLs** — `#/`, `#/contents`, `#/preface`, `#/ch/3`, `#/afterword`
- **Responsive** down to small phones, with a **print stylesheet** for PDF export
- Accessible: skip link, ARIA current states, focus-visible controls, honours
  `prefers-reduced-motion`

## Typography

Body text is set in EB Garamond at a ~34rem measure (roughly 65–70 characters
per line), with Inter for interface chrome. Fonts load from Google Fonts and
fall back to Georgia / system sans if unavailable. Adjust the palette, measure
and type scale via the CSS custom properties at the top of
[`assets/css/style.css`](assets/css/style.css).

## Project layout

```
index.html              page shell — header, drawer, footer
assets/css/style.css    all styling (design tokens at the top)
assets/js/app.js        hash router + view rendering
content/book.js         ← your book sections go here
assets/img/chapters/    fourteen chapter-end illustrations
tools/extract_pdf.py    PDF → page/line JSON (see "Regenerating" below)
tools/build_book.py     page/line JSON → content/book.js
```

## Regenerating the text from the source PDF

`content/book.js` is checked in, so nothing below is needed to run the site —
it only matters if you want to re-derive the text from the original PDF.

```bash
pip install pymupdf fonttools
python3 tools/extract_pdf.py Nannolagina_Devaru.pdf pages.json
python3 tools/build_book.py pages.json chapters.json   # writes content/book.js
```

The source PDF was exported from Word with the Tunga font subset-embedded and
a **broken ToUnicode map**: copying text out of it yields mojibake such as
`ಪಿಶ್ೊ` instead of `ಪ್ರಶ್ನೆ`. `extract_pdf.py` ignores that map and instead
reads each rendered glyph id, reverses the font's own GSUB ligature /
substitution tables to recover the base glyphs, maps those through the `cmap`,
and finally restores logical Kannada order (pre-base vowel signs, reph, vattu
and akhand conjuncts). It also detects the two-column body layout so the text
is read down one column at a time.

## Deploying

Any static host will do. For GitHub Pages: push this repository and enable
Pages for the branch root — no workflow or build configuration needed.

## Chapter-end pictures

There are fourteen chapter-end pictures in `assets/img/chapters/` — one for
each numbered chapter. The main page cover image is separate (`assets/img/mainpage.jpg`).

Each chapter can show an illustration after its last paragraph. In
`content/book.js`, add to any chapter object:

```js
{
  title: "The House on Ember Street",
  image: "assets/img/chapters/ch1.jpg",  // shown at the end of the chapter
  caption: "The house on Ember Street, waiting.", // optional
  alt: "An old house at dusk",                    // optional
  body: [ /* ... */ ]
}
```

Drop your own files into `assets/img/chapters/` and point `image` at them.
Chapters without an `image` simply render as before.

### Mid-chapter pictures

To place a picture *between* paragraphs rather than at the end, add a
`<figure class="inline-figure">` block directly to the chapter's `body` array
at the position you want it — `<figure>` blocks are passed through verbatim:

```js
body: [
  "<p>…the paragraph before the picture…</p>",
  "<figure class=\"inline-figure\"><img src=\"assets/img/chapters/ch1-brain.jpg\" alt=\"…\" loading=\"lazy\" decoding=\"async\"><figcaption class=\"inline-figcaption\">Optional caption.</figcaption></figure>",
  "<p>…the paragraph after…</p>"
]
```
