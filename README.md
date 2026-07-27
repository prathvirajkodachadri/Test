# Book Reader

A static, dependency-free website for reading a book online. No build step, no
framework, no npm install — open `index.html` and it works.

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
      title: "Chapter title",
      part:  "Part One",     // optional — consecutive chapters sharing a
                             // label are grouped in the contents and drawer
      body: [
        "A plain string becomes a paragraph.",
        "<blockquote>Raw HTML is passed through untouched.</blockquote>",
        "<h3>A subheading</h3>",
        "<p class=\"break\">* * *</p>"
      ]
    }
    // ...more chapters
  ]
};
```

The table of contents, chapter drawer, prev/next links, chapter numbering and
reading-time estimates are all generated from this data — you never edit HTML.

Supported `body` blocks: any string starting with `<p>`, `<h1>`–`<h6>`,
`<blockquote>`, `<ul>`, `<ol>`, `<figure>`, `<img>`, `<hr>`, `<div>`,
`<section>` or `<pre>` is used verbatim. Anything else is wrapped in `<p>`.

## Features

- **Cover page** with generated book-spine artwork (or your own cover image)
- **Table of contents** with parts, chapter numbers and per-chapter reading times
- **Slide-out chapter drawer** available from every page
- **Prev / next chapter cards** at the foot of each chapter
- **Keyboard navigation** — `←` / `→` between chapters, `Esc` closes the drawer
- **Reading progress bar** in the header
- **Deep-linkable URLs** — `#/`, `#/contents`, `#/ch/3`
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
content/book.js         ← your book goes here
```

## Deploying

Any static host will do. For GitHub Pages: push this repository and enable
Pages for the branch root — no workflow or build configuration needed.
