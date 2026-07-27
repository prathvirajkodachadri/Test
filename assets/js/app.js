/* ============================================================
   Book reader — hash-router application
   Routes:  #/            cover
            #/contents    table of contents
            #/ch/<n>      chapter n (1-based)
   ============================================================ */

(function () {
  "use strict";

  var BOOK = window.BOOK;
  if (!BOOK || !Array.isArray(BOOK.chapters) || !BOOK.chapters.length) {
    document.getElementById("main").innerHTML =
      '<div class="wrap"><div class="page-head"><h2>No book content found</h2>' +
      '<p class="muted">Add your chapters in <code>content/book.js</code>.</p></div></div>';
    return;
  }

  var meta = BOOK.meta || {};
  var chapters = BOOK.chapters;

  var main = document.getElementById("main");
  var drawer = document.getElementById("drawer");
  var scrim = document.getElementById("drawer-scrim");
  var drawerList = document.getElementById("drawer-list");
  var progressBar = document.getElementById("progress-bar");

  var WPM = 230; // for reading-time estimates

  /* ---------------- helpers ---------------- */

  function esc(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  // A body entry that already looks like HTML is passed through;
  // anything else becomes a paragraph.
  function blockToHTML(block) {
    var t = String(block).trim();
    return /^<(p|h[1-6]|blockquote|ul|ol|figure|img|hr|div|section|pre)[\s>]/i.test(t)
      ? t
      : "<p>" + t + "</p>";
  }

  function chapterHTML(ch) {
    return (ch.body || []).map(blockToHTML).join("\n");
  }

  // Counts words in any script: runs of non-space, non-punctuation characters.
  // (A Latin-only \w pattern would report 0 for Kannada, Devanagari, CJK, …)
  function wordCount(ch) {
    var text = (ch.body || []).join(" ").replace(/<[^>]*>/g, " ");
    var m = text.match(/[^\s!-/:-@[-`{-~\u2010-\u2027\u2030-\u205e]+/g);
    return m ? m.length : 0;
  }

  function readingTime(ch) {
    return Math.max(1, Math.round(wordCount(ch) / WPM));
  }

  function totalTime() {
    var w = chapters.reduce(function (a, c) { return a + wordCount(c); }, 0);
    return Math.max(1, Math.round(w / WPM));
  }

  // Group chapters by their optional `part` label, preserving order.
  function grouped() {
    var out = [];
    chapters.forEach(function (ch, i) {
      var label = ch.part || "";
      var last = out[out.length - 1];
      if (!last || last.label !== label) out.push({ label: label, items: [] });
      out[out.length - 1].items.push({ ch: ch, index: i });
    });
    return out;
  }

  function currentRoute() {
    var h = location.hash.replace(/^#/, "");
    if (!h || h === "/" ) return { name: "cover" };
    if (h === "/contents") return { name: "contents" };
    var m = h.match(/^\/ch\/(\d+)$/);
    if (m) {
      var n = parseInt(m[1], 10);
      if (n >= 1 && n <= chapters.length) return { name: "chapter", n: n };
    }
    return { name: "cover" };
  }

  /* ---------------- chrome ---------------- */

  function initChrome() {
    document.getElementById("brand-title").textContent = meta.title || "Untitled";
    document.getElementById("brand-author").textContent = meta.author || "";
    document.getElementById("footer-line").textContent =
      (meta.title || "Untitled") + " — " + (meta.author || "Unknown") +
      (meta.year ? " · " + meta.year : "");

    var mq = document.querySelector('meta[name="description"]');
    if (mq) mq.setAttribute("content", meta.blurb || meta.title || "");

    buildDrawer();
  }

  function buildDrawer() {
    var html = "";
    grouped().forEach(function (g) {
      if (g.label) html += '<div class="drawer-part">' + esc(g.label) + "</div>";
      g.items.forEach(function (it) {
        html +=
          '<a class="drawer-item" href="#/ch/' + (it.index + 1) + '" data-link data-ch="' + (it.index + 1) + '">' +
            '<span class="num">' + (it.index + 1) + "</span>" +
            "<span>" + esc(it.ch.title) + "</span>" +
          "</a>";
      });
    });
    drawerList.innerHTML = html;
  }

  function openDrawer() {
    drawer.hidden = false;
    scrim.hidden = false;
    document.getElementById("toc-toggle").setAttribute("aria-expanded", "true");
    document.body.style.overflow = "hidden";
  }

  function closeDrawer() {
    drawer.hidden = true;
    scrim.hidden = true;
    document.getElementById("toc-toggle").setAttribute("aria-expanded", "false");
    document.body.style.overflow = "";
  }

  /* ---------------- views ---------------- */

  function viewCover() {
    // The original text cover (used as the left-hand page of the spread,
    // and as the whole cover when no image is set).
    var textCard =
      '<div class="cover-card">' +
        '<div class="cover-plate">' +
          '<p class="cp-title">' + esc(meta.title || "Untitled") + "</p>" +
          '<div class="cp-rule"></div>' +
          '<p class="cp-author">' + esc(meta.author || "") + "</p>" +
        "</div>" +
        "<h1>" + esc(meta.title || "Untitled") + "</h1>" +
        (meta.subtitle ? '<p class="subtitle">' + esc(meta.subtitle) + "</p>" : "") +
        '<p class="byline">' + esc(meta.author || "") + "</p>" +
        (meta.blurb ? '<p class="blurb">' + esc(meta.blurb) + "</p>" : "") +
        '<div class="cta-row">' +
          '<a class="btn btn-primary" href="#/ch/1" data-link>Start reading</a>' +
          '<a class="btn" href="#/contents" data-link>Table of contents</a>' +
        "</div>" +
        '<p class="byline" style="margin-top:2.2rem">' +
          chapters.length + " chapters · about " + totalTime() + " min" +
        "</p>" +
      "</div>";

    // When a cover image is set, render an open-book spread:
    //   left page  = the original text cover
    //   right page = the uploaded image
    if (meta.cover) {
      return (
        '<section class="cover"><div class="spread">' +
          '<div class="page page-text">' + textCard + "</div>" +
          '<div class="page page-image">' +
            '<img src="' + esc(meta.cover) + '" alt="Cover of ' + esc(meta.title) +
              '" onerror="this.onerror=null;this.src=\'assets/img/cover-placeholder.svg\'">' +
          "</div>" +
        "</div></section>"
      );
    }

    return '<section class="cover">' + textCard + "</section>";
  }

  function viewContents() {
    var html =
      '<div class="page-head"><p class="eyebrow">' + esc(meta.author || "") + "</p>" +
      "<h2>Table of Contents</h2></div>" +
      '<div class="toc">';

    grouped().forEach(function (g) {
      if (g.label) html += '<div class="toc-part">' + esc(g.label) + "</div>";
      g.items.forEach(function (it) {
        html +=
          '<a class="toc-entry" href="#/ch/' + (it.index + 1) + '" data-link>' +
            '<span class="n">' + String(it.index + 1).padStart(2, "0") + "</span>" +
            '<span class="t">' + esc(it.ch.title) + "</span>" +
            '<span class="len">' + readingTime(it.ch) + " min</span>" +
          "</a>";
      });
    });

    return html + "</div>";
  }

  // End-of-chapter illustration. Set `image` (and optional `caption`,
  // `alt`) on a chapter in content/book.js to show a picture at the end.
  function chapterImageHTML(ch, n) {
    var img = ch.image;
    if (!img) return "";
    var alt = ch.alt || ("Illustration for chapter " + n + ": " + (ch.title || ""));
    var cap = ch.caption
      ? '<figcaption class="chapter-figcaption">' + esc(ch.caption) + "</figcaption>"
      : "";
    return (
      '<figure class="chapter-figure">' +
        '<img src="' + esc(img) + '" alt="' + esc(alt) + '" loading="lazy" decoding="async">' +
        cap +
      "</figure>"
    );
  }

  function viewChapter(n) {
    var i = n - 1;
    var ch = chapters[i];
    var prev = chapters[i - 1];
    var next = chapters[i + 1];

    var html =
      '<article class="chapter"><div class="reader">' +
        (ch.part ? '<p class="chapter-part">' + esc(ch.part) + "</p>" : "") +
        '<p class="chapter-num">Chapter ' + n + " of " + chapters.length + "</p>" +
        "<h2>" + esc(ch.title) + "</h2>" +
        '<div class="chapter-rule"></div>' +
        '<div class="prose">' + chapterHTML(ch) + "</div>" +
        chapterImageHTML(ch, n) +
      "</div></article>" +
      '<nav class="chapter-nav" aria-label="Chapter navigation">';

    html += prev
      ? '<a class="navcard prev" href="#/ch/' + (n - 1) + '" data-link>' +
          '<span class="dir">← Previous</span><span class="name">' + esc(prev.title) + "</span></a>"
      : '<a class="navcard prev is-empty" href="#/" data-link aria-hidden="true" tabindex="-1"><span class="dir">.</span><span class="name">.</span></a>';

    html += next
      ? '<a class="navcard next" href="#/ch/' + (n + 1) + '" data-link>' +
          '<span class="dir">Next →</span><span class="name">' + esc(next.title) + "</span></a>"
      : '<a class="navcard next" href="#/contents" data-link>' +
          '<span class="dir">The end</span><span class="name">Back to contents</span></a>';

    return html + "</nav>";
  }

  /* ---------------- router ---------------- */

  var lastRoute = "";

  function render() {
    var route = currentRoute();
    var key = location.hash;

    if (route.name === "cover") {
      main.innerHTML = viewCover();
      document.title = (meta.title || "Untitled") + (meta.author ? " — " + meta.author : "");
    } else if (route.name === "contents") {
      main.innerHTML = viewContents();
      document.title = "Contents — " + (meta.title || "Untitled");
    } else {
      main.innerHTML = viewChapter(route.n);
      document.title =
        chapters[route.n - 1].title + " — " + (meta.title || "Untitled");
    }

    // Highlight active nav items
    document.querySelectorAll(".tb-btn[href]").forEach(function (a) {
      a.removeAttribute("aria-current");
      var h = a.getAttribute("href");
      if ((h === "#/" && route.name === "cover") ||
          (h === "#/contents" && route.name === "contents")) {
        a.setAttribute("aria-current", "page");
      }
    });
    drawerList.querySelectorAll(".drawer-item").forEach(function (a) {
      if (route.name === "chapter" && +a.dataset.ch === route.n) {
        a.setAttribute("aria-current", "page");
      } else {
        a.removeAttribute("aria-current");
      }
    });

    closeDrawer();
    if (key !== lastRoute) window.scrollTo(0, 0);
    lastRoute = key;
    updateProgress();
  }

  /* ---------------- reading progress ---------------- */

  function updateProgress() {
    var doc = document.documentElement;
    var scrollable = doc.scrollHeight - window.innerHeight;
    var pct = scrollable > 8 ? (window.scrollY / scrollable) * 100 : 0;
    progressBar.style.width = Math.min(100, Math.max(0, pct)) + "%";
  }

  /* ---------------- events ---------------- */

  window.addEventListener("hashchange", render);
  window.addEventListener("scroll", updateProgress, { passive: true });
  window.addEventListener("resize", updateProgress);

  document.getElementById("toc-toggle").addEventListener("click", function () {
    drawer.hidden ? openDrawer() : closeDrawer();
  });
  document.getElementById("drawer-close").addEventListener("click", closeDrawer);
  scrim.addEventListener("click", closeDrawer);

  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") closeDrawer();

    // Ignore arrow keys while typing
    var tag = (e.target.tagName || "").toLowerCase();
    if (tag === "input" || tag === "textarea" || e.metaKey || e.ctrlKey || e.altKey) return;

    var r = currentRoute();
    if (r.name !== "chapter") return;
    if (e.key === "ArrowRight" && r.n < chapters.length) location.hash = "#/ch/" + (r.n + 1);
    if (e.key === "ArrowLeft" && r.n > 1) location.hash = "#/ch/" + (r.n - 1);
  });

  /* ---------------- boot ---------------- */

  function addFloatingTOCButton() {
    const fab = document.createElement('a');
    fab.id = 'fab-toc';
    fab.href = '#';
    fab.innerHTML = `<svg viewBox="0 0 24 24"><path d="M4 6h16M4 12h16M4 18h16"/></svg> TOC`;
    fab.addEventListener('click', e => {
      e.preventDefault();
      openDrawer();
    });
    document.body.appendChild(fab);
  }

  initChrome();
  addFloatingTOCButton();
  render();
})();
