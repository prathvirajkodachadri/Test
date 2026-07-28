/* ============================================================
   Book reader — hash-router application
   Routes:  #/            cover
            #/contents    table of contents
            #/preface     preface/front matter
            #/ch/<n>      chapter n (1-based, excludes preface/afterword)
            #/afterword   afterword/back matter
   ============================================================ */

(function () {
  "use strict";

  var BOOK = window.BOOK;
  if (!BOOK || !Array.isArray(BOOK.chapters) || !BOOK.chapters.length) {
    document.getElementById("main").innerHTML =
      '<div class="wrap"><div class="page-head"><h2>No book content found</h2>' +
      '<p class="muted">Add your book sections in <code>content/book.js</code>.</p></div></div>';
    return;
  }

  var meta = BOOK.meta || {};

  // `sections` is the complete reading order. A section can be typed as
  // `preface`, `chapter` (default), or `afterword`. Only real chapters are
  // counted and routed as #/ch/<n>.
  var sections = BOOK.chapters;
  var chapters = sections.filter(isChapter);

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

  function sectionType(section) {
    return String((section && (section.type || section.kind)) || "chapter").toLowerCase();
  }

  function isPreface(section) {
    return sectionType(section) === "preface";
  }

  function isAfterword(section) {
    return sectionType(section) === "afterword";
  }

  function isChapter(section) {
    var type = sectionType(section);
    return type !== "preface" && type !== "afterword" && type !== "frontmatter" && type !== "backmatter";
  }

  function firstIndexOfType(type) {
    for (var i = 0; i < sections.length; i++) {
      if (sectionType(sections[i]) === type) return i;
    }
    return -1;
  }

  function chapterNumberForIndex(sectionIndex) {
    var n = 0;
    for (var i = 0; i <= sectionIndex && i < sections.length; i++) {
      if (isChapter(sections[i])) n++;
    }
    return n;
  }

  function sectionIndexForChapterNumber(chapterNumber) {
    var n = 0;
    for (var i = 0; i < sections.length; i++) {
      if (!isChapter(sections[i])) continue;
      n++;
      if (n === chapterNumber) return i;
    }
    return -1;
  }

  function routeForSectionIndex(sectionIndex) {
    var section = sections[sectionIndex];
    if (!section) return "#/";
    if (isPreface(section)) return "#/preface";
    if (isAfterword(section)) return "#/afterword";
    return "#/ch/" + chapterNumberForIndex(sectionIndex);
  }

  function sectionLabel(section, sectionIndex) {
    if (section.label) return section.label;
    if (isPreface(section)) return "Preface";
    if (isAfterword(section)) return "Afterword";
    return "Chapter " + chapterNumberForIndex(sectionIndex) + " of " + chapters.length;
  }

  function sectionMarker(section, sectionIndex) {
    if (isPreface(section)) return "Preface";
    if (isAfterword(section)) return "Afterword";
    return String(chapterNumberForIndex(sectionIndex)).padStart(2, "0");
  }

  function sectionSummary() {
    return (
      '<span class="sum-line">' +
        chapters.length + " chapter" + (chapters.length === 1 ? "" : "s") +
      "</span>" +
      '<span class="sum-line">About ' + totalTime() + " min Reading Time</span>"
    );
  }

  // A body entry that already looks like HTML is passed through;
  // anything else becomes a paragraph.
  function blockToHTML(block) {
    var t = String(block).trim();
    return /^<(p|h[1-6]|blockquote|ul|ol|figure|img|hr|div|section|pre)[\s>]/i.test(t)
      ? t
      : "<p>" + t + "</p>";
  }

  function sectionHTML(section) {
    return (section.body || []).map(blockToHTML).join("\n");
  }

  // Counts words in any script: runs of non-space, non-punctuation characters.
  // (A Latin-only \w pattern would report 0 for Kannada, Devanagari, CJK, …)
  function wordCount(section) {
    var text = (section.body || []).join(" ").replace(/<[^>]*>/g, " ");
    var m = text.match(/[^\s!-/:-@[-`{-~\u2010-\u2027\u2030-\u205e]+/g);
    return m ? m.length : 0;
  }

  function readingTime(section) {
    return Math.max(1, Math.round(wordCount(section) / WPM));
  }

  function totalTime() {
    var w = sections.reduce(function (a, section) { return a + wordCount(section); }, 0);
    return Math.max(1, Math.round(w / WPM));
  }

  // Group sections by their optional `part` label, preserving order.
  function grouped() {
    var out = [];
    sections.forEach(function (section, i) {
      var label = section.part || "";
      var last = out[out.length - 1];
      if (!last || last.label !== label) out.push({ label: label, items: [] });
      out[out.length - 1].items.push({ section: section, index: i });
    });
    return out;
  }

  function currentRoute() {
    var h = location.hash.replace(/^#/, "");
    if (!h || h === "/" ) return { name: "cover" };
    if (h === "/contents") return { name: "contents" };

    if (h === "/preface") {
      var prefaceIndex = firstIndexOfType("preface");
      if (prefaceIndex >= 0) return { name: "section", index: prefaceIndex };
    }

    if (h === "/afterword") {
      var afterwordIndex = firstIndexOfType("afterword");
      if (afterwordIndex >= 0) return { name: "section", index: afterwordIndex };
    }

    var m = h.match(/^\/ch\/(\d+)$/);
    if (m) {
      var n = parseInt(m[1], 10);
      var sectionIndex = sectionIndexForChapterNumber(n);
      if (sectionIndex >= 0) return { name: "section", index: sectionIndex };
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

    // index.html ships a hand-written SEO/Open Graph description that search
    // engines and social crawlers already read. Only fill one in when the page
    // does not provide it, so a book dropped into this template still gets a
    // description without clobbering an authored one.
    var mq = document.querySelector('meta[name="description"]');
    if (mq && !(mq.getAttribute("content") || "").trim()) {
      mq.setAttribute("content", meta.blurb || meta.title || "");
    }

    buildDrawer();
  }

  function buildDrawer() {
    var html = "";
    grouped().forEach(function (g) {
      if (g.label) html += '<div class="drawer-part">' + esc(g.label) + "</div>";
      g.items.forEach(function (it) {
        var marker = sectionMarker(it.section, it.index);
        var markerClass = isChapter(it.section) ? "num" : "num word";
        html +=
          '<a class="drawer-item" href="' + routeForSectionIndex(it.index) + '" data-link data-section="' + it.index + '">' +
            '<span class="' + markerClass + '">' + esc(marker) + "</span>" +
            "<span>" + esc(it.section.title) + "</span>" +
          "</a>";
      });
    });
    drawerList.innerHTML = html;
    
    // Close drawer when an item is clicked (even if hash doesn't change)
    drawerList.querySelectorAll(".drawer-item").forEach(function (a) {
      a.addEventListener("click", function() {
        // Delay slightly to allow navigation to start
        setTimeout(closeDrawer, 50);
      });
    });
  }

  function openDrawer() {
    drawer.hidden = false;
    scrim.hidden = false;
    var toggle = document.getElementById("toc-toggle");
    toggle.setAttribute("aria-expanded", "true");
    toggle.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M18 6L6 18M6 6l12 12"/></svg><span class="sr-only">Close contents list</span>';
    
    var fab = document.getElementById("fab-toc");
    if (fab) {
      fab.classList.add("active");
      fab.innerHTML = '<svg viewBox="0 0 24 24"><path d="M18 6L6 18M6 6l12 12"/></svg> Close';
    }
    document.body.style.overflow = "hidden";
  }

  function closeDrawer() {
    drawer.hidden = true;
    scrim.hidden = true;
    var toggle = document.getElementById("toc-toggle");
    toggle.setAttribute("aria-expanded", "false");
    toggle.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 6h16M4 12h16M4 18h16"/></svg><span class="sr-only">Open contents list</span>';

    var fab = document.getElementById("fab-toc");
    if (fab) {
      fab.classList.remove("active");
      fab.innerHTML = '<svg viewBox="0 0 24 24"><path d="M4 6h16M4 12h16M4 18h16"/></svg> Contents';
    }
    document.body.style.overflow = "";
  }

  /* ---------------- views ---------------- */

  function viewCover() {
    // The original text cover (used as the left-hand page of the spread,
    // and as the whole cover when no image is set).
    var startHref = routeForSectionIndex(0);
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
          '<a class="btn btn-primary" href="' + startHref + '" data-link>Start reading</a>' +
          '<a class="btn" href="#/contents" data-link>Table of contents</a>' +
        "</div>" +
        '<p class="byline book-summary">' + sectionSummary() + "</p>" +
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
        var marker = sectionMarker(it.section, it.index);
        var markerClass = isChapter(it.section) ? "n" : "n word";
        html +=
          '<a class="toc-entry" href="' + routeForSectionIndex(it.index) + '" data-link>' +
            '<span class="' + markerClass + '">' + esc(marker) + "</span>" +
            '<span class="t">' + esc(it.section.title) + "</span>" +
            '<span class="len">' + readingTime(it.section) + " min</span>" +
          "</a>";
      });
    });

    return html + "</div>";
  }

  // End-of-section illustration. Set `image` (and optional `caption`,
  // `alt`) on a section in content/book.js to show a picture at the end.
  function sectionImageHTML(section, sectionIndex) {
    var img = section.image;
    if (!img) return "";
    var alt = section.alt || ("Illustration for " + sectionLabel(section, sectionIndex) + ": " + (section.title || ""));
    var cap = section.caption
      ? '<figcaption class="chapter-figcaption">' + esc(section.caption) + "</figcaption>"
      : "";
    return (
      '<figure class="chapter-figure">' +
        '<img src="' + esc(img) + '" alt="' + esc(alt) + '" loading="lazy" decoding="async">' +
        cap +
      "</figure>"
    );
  }

  function viewSection(sectionIndex) {
    var section = sections[sectionIndex];
    var prev = sections[sectionIndex - 1];
    var next = sections[sectionIndex + 1];
    var typeClass = "section-" + sectionType(section).replace(/[^a-z0-9_-]+/g, "-");

    var html =
      '<article class="chapter ' + typeClass + '"><div class="reader">' +
        (section.part ? '<p class="chapter-part">' + esc(section.part) + "</p>" : "") +
        '<p class="chapter-num">' + esc(sectionLabel(section, sectionIndex)) + "</p>" +
        "<h2>" + esc(section.title) + "</h2>" +
        '<div class="chapter-rule"></div>' +
        '<div class="prose">' + sectionHTML(section) + "</div>" +
        sectionImageHTML(section, sectionIndex) +
      "</div></article>" +
      '<nav class="chapter-nav" aria-label="Reading navigation">';

    html += prev
      ? '<a class="navcard prev" href="' + routeForSectionIndex(sectionIndex - 1) + '" data-link>' +
          '<span class="dir">← Previous</span><span class="name">' + esc(prev.title) + "</span></a>"
      : '<a class="navcard prev is-empty" href="#/" data-link aria-hidden="true" tabindex="-1"><span class="dir">.</span><span class="name">.</span></a>';

    html += next
      ? '<a class="navcard next" href="' + routeForSectionIndex(sectionIndex + 1) + '" data-link>' +
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
      main.innerHTML = viewSection(route.index);
      document.title =
        sections[route.index].title + " — " + (meta.title || "Untitled");
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
      if (route.name === "section" && +a.dataset.section === route.index) {
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

  /* ---------------- reading progress & FAB visibility ---------------- */

  function updateProgress() {
    var doc = document.documentElement;
    var scrollable = doc.scrollHeight - window.innerHeight;
    var pct = scrollable > 8 ? (window.scrollY / scrollable) * 100 : 0;
    progressBar.style.width = Math.min(100, Math.max(0, pct)) + "%";

    // Show/hide FAB based on scroll and route
    var fab = document.getElementById("fab-toc");
    if (fab) {
      var route = currentRoute();
      var isContentsPage = (route.name === "contents");
      
      if (window.scrollY > 200 && !isContentsPage) {
        fab.style.opacity = "1";
        fab.style.pointerEvents = "auto";
        fab.style.transform = "translateY(0)";
      } else {
        fab.style.opacity = "0";
        fab.style.pointerEvents = "none";
        fab.style.transform = "translateY(20px)";
      }
    }
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
    if (r.name !== "section") return;
    if (e.key === "ArrowRight" && r.index < sections.length - 1) location.hash = routeForSectionIndex(r.index + 1);
    if (e.key === "ArrowLeft" && r.index > 0) location.hash = routeForSectionIndex(r.index - 1);
  });

  /* ---------------- boot ---------------- */

  function addFloatingTOCButton() {
    var fab = document.createElement('a');
    fab.id = 'fab-toc';
    fab.href = '#';
    fab.innerHTML = '<svg viewBox="0 0 24 24"><path d="M4 6h16M4 12h16M4 18h16"/></svg> Contents';
    fab.addEventListener('click', function (e) {
      e.preventDefault();
      drawer.hidden ? openDrawer() : closeDrawer();
    });
    document.body.appendChild(fab);
  }

  initChrome();
  addFloatingTOCButton();
  render();
})();
