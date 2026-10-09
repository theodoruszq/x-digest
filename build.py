#!/usr/bin/env python3
"""Build the X Digest static site (one page per day).

Reads  <src>/YYYY-MM-DD.md   (default: ./content)
Writes <out>/index.html, <out>/YYYY-MM-DD.html, <out>/assets/*   (default: ./docs)

Usage:  python3 build.py [--src DIR] [--out DIR]
See README.md for the markdown format.
"""
from __future__ import annotations

import argparse
import datetime as dt
import html
import re
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path

HERE = Path(__file__).resolve().parent
HOME_URL = "https://theodoruszq.github.io/"
SITE_URL = "https://x-digest.theodoruszq.win/"  # canonical; also served at theodoruszq.github.io/x-digest/
CNAME = "x-digest.theodoruszq.win"
SITE_NAME = "X Digest"

CJK = r"\u3400-\u9fff\uf900-\ufaff\u3000-\u303f\uff00-\uffef"
FILE_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})\.md$")
ITEM_RE = re.compile(
    r"^\*\*(?:(?P<num>\d+)\.\s+)?(?P<headline>.+?)\*\*\s*·\s*"
    r"\[(?P<linktext>[^\]]+)\]\((?P<url>[^)\s]+)\)"
    r"(?:\s*·\s*♥\s*(?P<likes>[^·]+?))?"
    r"(?:\s*·\s*(?P<created>.+?))?\s*$"
)
SUMMARY_RE = re.compile(r"^(?:summary|tl;?dr)\s*:\s*(.*)$", re.I)
EXPLICIT_GLOSS_RE = re.compile(r"\[\[([^\[\]|]+)\|([^\[\]]+)\]\]")
LEGACY_GLOSS_RE = re.compile(r"\s?\(([^()]*[" + CJK + r"][^()]*)\)")
POS_RE = re.compile(r"^((?:[a-z]{1,5}\.)(?:\s*/\s*[a-z]{1,5}\.)*|idiom|phrase|phr\.)\s+(.+)$")


# --------------------------------------------------------------------------- parsing
@dataclass
class Item:
    headline: str
    url: str
    likes: str = ""
    created: dt.datetime | None = None  # UTC, from the X API created_at
    quote: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def handle(self) -> str:
        m = re.search(r"(?:x|twitter)\.com/([^/]+)/status", self.url)
        return m.group(1) if m else ""


@dataclass
class Day:
    date: dt.date
    items: list[Item]
    summary: list[str] = field(default_factory=list)  # bullet points

    @property
    def slug(self) -> str:
        return self.date.isoformat()

    @property
    def date_long(self) -> str:
        d = self.date
        return f"{d.strftime('%A')}, {d.strftime('%B')} {d.day}, {d.year}"

    @property
    def date_short(self) -> str:
        return f"{self.date.strftime('%b')} {self.date.day}"


STOPWORDS = {"The", "A", "An", "This", "That", "These", "Those", "In", "On", "At", "By", "With",
             "For", "And", "Or", "Of", "To", "From", "Using", "BREAKING:", "I", "We", "It"}


def _legacy_phrase_start(before: str) -> int:
    """Return index in `before` where the glossed phrase starts (legacy inline format).

    Rules: a phrase in straight/curly quotes right before the parenthesis wins;
    otherwise a run of Capitalized words (e.g. "Multi-Agent Orchestration", stopping at
    articles/prepositions and sentence boundaries); otherwise the single preceding word
    (e.g. "crawlers", "TL;DR", "state-of-the-art"). Lowercase multi-word phrases such as
    "rolling out" cannot be inferred -- use the explicit [[phrase|gloss]] form for those.
    """
    m = re.search(r"[\"“‘]([^\"“”‘’]{1,60})[\"”’]$", before)
    if m:
        return m.start(1)
    m = re.search(r"[^\s(\[]+$", before)
    if not m:
        return len(before)
    start = m.start()
    if re.match(r"[A-Z0-9]", m.group(0)):
        while True:
            pre = before[:start].rstrip()
            if not pre or pre[-1] in ".:!?;,…—(":
                break  # sentence / clause boundary
            prev = re.search(r"(?:^|(?<=\s))([A-Z][\w\-–'’.&]*)\s+$", before[:start])
            if not prev or prev.group(1) in STOPWORDS:
                break
            start = prev.start(1)
    return start


def normalize_legacy_glosses(text: str) -> str:
    """Convert `word (pos. 中文)` into `[[word|pos. 中文]]`, leaving [[…]] markup untouched."""
    out, pos = [], 0
    parts = re.split(r"(\[\[[^\]]*\]\])", text)
    for part in parts:
        if part.startswith("[["):
            out.append(part)
            continue
        buf = ""
        last = 0
        for m in LEGACY_GLOSS_RE.finditer(part):
            before = buf + part[last:m.start()]
            if re.search(r"[" + CJK + r"]\s*$", before):  # Chinese original text, not a gloss
                buf = before + m.group(0)
                last = m.end()
                continue
            start = _legacy_phrase_start(before)
            phrase = before[start:].strip()
            if not phrase:
                buf = before + m.group(0)
            else:
                buf = before[:start] + f"[[{phrase}|{m.group(1).strip()}]]"
            last = m.end()
        out.append(buf + part[last:])
    return "".join(out)


ISO_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}:?\d{2})$")


def parse_created(token: str, fname: str, lineno: int) -> dt.datetime | None:
    """Last header token: ISO 8601 created_at (e.g. 2026-10-08T18:05:00Z). Legacy "35h ago" is ignored."""
    token = token.strip()
    if not token:
        return None
    if ISO_RE.match(token):
        return dt.datetime.fromisoformat(token.replace("Z", "+00:00")).astimezone(dt.timezone.utc)
    if not re.fullmatch(r"\d+\s*[smhd]\w*\s+ago", token):
        print(f"warning: {fname}:{lineno}: unrecognised timestamp ignored: {token!r}", file=sys.stderr)
    return None


def parse_day(path: Path) -> Day:
    date = dt.date.fromisoformat(FILE_RE.match(path.name).group(1))
    items: list[Item] = []
    seen: set[str] = set()
    summary: list[str] = []
    skipping = False
    for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or (line.startswith("<!--") and line.endswith("-->")):
            continue
        m = ITEM_RE.match(line)
        if m:
            key = re.sub(r"[?#].*$", "", m.group("url")).rstrip("/").lower()
            skipping = key in seen
            if skipping:
                print(f"warning: {path.name}:{lineno}: duplicate post skipped: {m.group('url')}", file=sys.stderr)
                continue
            seen.add(key)
            items.append(Item(
                headline=normalize_legacy_glosses(m.group("headline").strip()),
                url=m.group("url"),
                likes=(m.group("likes") or "").strip(),
                created=parse_created(m.group("created") or "", path.name, lineno),
            ))
            continue
        if skipping:
            continue
        sm = SUMMARY_RE.match(line)
        if sm:
            if sm.group(1).strip():  # legacy one-line summary: split on ";" into bullets
                summary.extend(x.strip().rstrip(".") for x in sm.group(1).split(";") if x.strip())
            continue
        if not items:
            if not line.startswith("#"):
                summary.append(re.sub(r"^[-*•]\s+", "", line).rstrip("."))
            continue
        if line.startswith(">"):
            items[-1].quote.append(normalize_legacy_glosses(line.lstrip(">").strip()))
        elif line.startswith("💡"):
            items[-1].notes.append(line[len("💡"):].strip())
        else:
            print(f"warning: {path.name}:{lineno}: unrecognised line ignored: {line[:60]!r}", file=sys.stderr)
    if not items:
        print(f"warning: {path.name}: no items found", file=sys.stderr)
    return Day(date=date, items=items, summary=summary)


# --------------------------------------------------------------------------- rendering
esc = lambda s: html.escape(s, quote=True)


def plain(text: str) -> str:
    """Strip gloss markup, keeping only the English phrase."""
    return EXPLICIT_GLOSS_RE.sub(lambda m: m.group(1), text)


def plural(n: int, word: str) -> str:
    return f"{n} {word}" + ("" if n == 1 else "s")


def split_gloss(g: str) -> tuple[str, str]:
    m = POS_RE.match(g.strip())
    return (m.group(1), m.group(2).strip()) if m else ("", g.strip())


def render_inline(text: str) -> str:
    out, last = [], 0
    for m in EXPLICIT_GLOSS_RE.finditer(text):
        out.append(esc(text[last:m.start()]))
        pos, zh = split_gloss(m.group(2))
        pos_html = f'<i>{esc(pos)}</i> ' if pos else ""
        out.append(f'<span class="g">{esc(m.group(1).strip())}</span>'
                   f'<span class="g-zh zh-only" lang="zh-Hans">{pos_html}{esc(zh)}</span>')
        last = m.end()
    out.append(esc(text[last:]))
    return "".join(out)


EXT_ICON = ('<svg class="ext" viewBox="0 0 12 12" width="11" height="11" aria-hidden="true" focusable="false">'
            '<path d="M5 2.25H3.5A1.75 1.75 0 0 0 1.75 4v4.5c0 .97.78 1.75 1.75 1.75H8A1.75 1.75 0 0 0 9.75 8.5V7" '
            'fill="none" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"/>'
            '<path d="M7 1.75h3.25V5M10.1 1.9 5.75 6.25" fill="none" stroke="currentColor" stroke-width="1.3" '
            'stroke-linecap="round" stroke-linejoin="round"/></svg>')

BOOT = ("<script>(function(){var d=document.documentElement;d.classList.add('js');try{var t=localStorage.getItem('xdigest.theme');"
        "if(t)d.dataset.theme=t;if(localStorage.getItem('xdigest.zh')==='1')d.classList.add('show-zh');}catch(e){}})();</script>")


def page(title: str, description: str, canonical: str, body: str, kind: str = "index") -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="light dark">
  <meta name="theme-color" content="#ffffff" media="(prefers-color-scheme: light)">
  <meta name="theme-color" content="#141414" media="(prefers-color-scheme: dark)">
  <title>{esc(title)}</title>
  <meta name="description" content="{esc(description)}">
  <link rel="canonical" href="{esc(canonical)}">
  <link rel="icon" href="assets/favicon-32x32.png" type="image/png">
  <meta property="og:type" content="website">
  <meta property="og:title" content="{esc(title)}">
  <meta property="og:description" content="{esc(description)}">
  <meta property="og:url" content="{esc(canonical)}">
  <link rel="preload" href="assets/fonts/lato-regular.woff2" as="font" type="font/woff2" crossorigin>
  <link rel="stylesheet" href="assets/style.css">
  {BOOT}
  <script src="assets/digest.js" defer></script>
</head>
<body class="page-{kind}">
  <a class="skip-link" href="#main">Skip to content</a>
  <div class="toolbar"><a class="tool" href="{HOME_URL}">About</a><span class="tool-sep" aria-hidden="true">/</span><button type="button" class="tool" data-toggle-theme><span data-theme-label>Dark</span></button></div>
  <div class="site-shell">
    <main id="main">
{body}
      <div class="row">
        <div class="rail"></div>
        <footer class="col site-footer">
          <p>Posts quoted from <a href="https://x.com">X</a>, updated twice a day.</p>
        </footer>
      </div>
    </main>
  </div>
</body>
</html>
"""


def render_item(n: int, item: Item) -> str:
    quote = "".join(f"<p>{render_inline(q)}</p>" for q in item.quote)
    notes = "".join(f'<p class="note zh-only" lang="zh-Hans"><span aria-hidden="true">💡</span> {esc(t)}</p>'
                    for t in item.notes)
    meta = []
    if item.handle:
        meta.append(f'<a class="handle" href="https://x.com/{esc(item.handle)}">@{esc(item.handle)}</a>')
    if item.likes:
        meta.append(f'<span class="likes"><span class="heart" aria-hidden="true">♥</span>'
                    f'<span class="sr-only">Likes:</span> {esc(item.likes)}</span>')
    meta.append(f'<a class="orig" href="{esc(item.url)}" rel="noopener">Original{EXT_ICON}</a>')
    if item.created:
        c = item.created
        iso = c.strftime("%Y-%m-%dT%H:%M:%SZ")
        meta.append(f'<time class="ts" datetime="{iso}" title="{c.strftime("%Y-%m-%d %H:%M")} UTC">'
                    f'{c.strftime("%b")} {c.day}, {c.strftime("%H:%M")} UTC</time>')
    sep = '<span class="dot" aria-hidden="true">·</span>'
    quote_html = f'<blockquote class="quote" cite="{esc(item.url)}">{quote}</blockquote>' if quote else ""
    return f"""        <article class="item" id="p{n}">
          <div class="item-num" aria-hidden="true">{n}</div>
          <div class="item-body">
            <h2 class="item-title"><a href="{esc(item.url)}" rel="noopener">{render_inline(item.headline)}</a></h2>
            <p class="item-meta">{sep.join(meta)}</p>
            {quote_html}{notes}
          </div>
        </article>"""


def render_day(day: Day, older: Day | None, newer: Day | None) -> str:
    items = "\n".join(render_item(i, it) for i, it in enumerate(day.items, 1))
    has_zh = any(EXPLICIT_GLOSS_RE.search(it.headline + " ".join(it.quote)) or it.notes for it in day.items)
    toggle = ('<button type="button" class="zh-switch" role="switch" aria-checked="false" data-toggle-zh '
              'aria-label="Chinese glosses and notes" title="Chinese glosses &amp; notes">'
              '<span class="zh-switch-label" lang="zh-Hans" aria-hidden="true">中文</span>'
              '<span class="zh-switch-track" aria-hidden="true"><span class="zh-switch-knob"></span></span></button>') if has_zh else ""

    def nav(d: Day | None, rel: str) -> str:
        if not d:
            return f'<span class="pager-{rel}"></span>'
        kicker = "← Previous day" if rel == "prev" else "Next day →"
        return (f'<a class="pager-{rel}" rel="{rel}" href="{d.slug}.html"><span class="pager-kicker">{kicker}</span>'
                f'<span class="pager-title">{esc(d.date_long)}</span></a>')

    lede = render_summary(day.summary, "lede")
    mk = day.date.strftime("%Y-%m")
    body = f"""      <div class="row">
      <div class="rail"><a class="month-label" href="./#m{mk}" title="All days in {mk}">{mk}</a></div>
      <article class="col post day-page">
        <header class="post-header">
          <a class="back-link" href="./">← All days</a>
          <h1>{esc(day.date_long)}</h1>
          {lede}
          <div class="post-tools"><p class="entry-meta">{plural(len(day.items), "post")}</p>{toggle}</div>
        </header>
        <div class="items">
{items}
        </div>
        <nav class="pager" aria-label="Day navigation">
          {nav(older, "prev")}
          {nav(newer, "next")}
        </nav>
      </article>
      </div>"""
    return page(f"{day.date_long} · {SITE_NAME}", "; ".join(day_summary(day)) + ".",
                f"{SITE_URL}{day.slug}.html", body, kind="day")


def day_summary(day: Day) -> list[str]:
    return day.summary or [plain(i.headline) for i in day.items[:3]]


def render_summary(points: list[str], cls: str) -> str:
    if not points:
        return ""
    return f'<ul class="summary-list {cls}">' + "".join(f"<li>{esc(p)}</li>" for p in points) + "</ul>"


def render_entry(d: Day) -> str:
    return f"""        <article class="day-entry">
          <div class="entry-heading">
            <h2><a href="{d.slug}.html">{esc(d.date_long)}</a></h2>
            <p class="entry-meta">{plural(len(d.items), "post")}</p>
          </div>
          {render_summary(day_summary(d), "day-summary")}
        </article>"""


def render_index(days: list[Day]) -> str:
    months: dict[str, list[Day]] = {}
    for d in days:  # newest first
        months.setdefault(d.date.strftime("%Y-%m"), []).append(d)
    sections = "\n".join(f"""      <section class="row month" id="m{mk}" aria-labelledby="ml{mk}">
        <div class="rail"><h2 class="month-label" id="ml{mk}"><a href="#m{mk}">{mk}</a></h2></div>
        <div class="col days">
{chr(10).join(render_entry(d) for d in ds)}
        </div>
      </section>""" for mk, ds in months.items())
    body = f"""      <div class="row">
        <div class="rail"></div>
        <header class="col archive-header">
          <h1>X Digest</h1>
          <p>The day’s most useful posts on X, collected twice a day and quoted from the source.</p>
        </header>
      </div>
{sections}"""
    return page(f"{SITE_NAME} · Digital Reality", "A daily digest of the most useful posts on X.", SITE_URL, body)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src", default=str(HERE / "content"), type=Path)
    ap.add_argument("--out", default=str(HERE / "docs"), type=Path)
    args = ap.parse_args()

    files = sorted(p for p in args.src.iterdir() if FILE_RE.match(p.name))
    if not files:
        sys.exit(f"no YYYY-MM-DD.md files in {args.src}")
    days = sorted((parse_day(p) for p in files), key=lambda d: d.date)
    out: Path = args.out
    out.mkdir(parents=True, exist_ok=True)
    for old in out.glob("*.html"):  # drop pages for days that no longer exist
        old.unlink()
    (out / "assets").mkdir(exist_ok=True)
    for name in ("style.css", "digest.js", "favicon-32x32.png"):
        shutil.copyfile(HERE / "src" / name, out / "assets" / name)
    shutil.copytree(HERE / "src" / "fonts", out / "assets" / "fonts", dirs_exist_ok=True)
    (out / ".nojekyll").write_text("")
    (out / "CNAME").write_text(CNAME)
    for i, d in enumerate(days):
        older = days[i - 1] if i > 0 else None
        newer = days[i + 1] if i + 1 < len(days) else None
        (out / f"{d.slug}.html").write_text(render_day(d, older, newer), encoding="utf-8")
        print(f"built {d.slug}.html  ({plural(len(d.items), 'post')})")
    (out / "index.html").write_text(render_index(list(reversed(days))), encoding="utf-8")
    print(f"built index.html  ({plural(len(days), 'day')}) -> {out}")


if __name__ == "__main__":
    main()
