# X Digest

A daily digest of the most useful posts on X, published at <https://theodoruszq.github.io/x-digest/>.
Styled to match <https://theodoruszq.github.io/> (Lato from the user site's `/fonts/`, same sidebar grid and colours).

```
content/YYYY-MM-DD.md   one source file per day
src/                    style.css, digest.js (copied to docs/assets on build)
build.py                content/ → docs/ (pure Python 3.9+, no dependencies)
docs/                   built site — GitHub Pages serves main:/docs
publish.sh              sync day files from $X_DIGEST_SRC, rebuild, commit, push
screenshots.py          optional Playwright screenshots
```

## Workflow (twice a day)
1. Append the new posts to today's file (`YYYY-MM-DD.md`, created on the first run of the day) and refresh the
   `Summary:` line so it covers the whole day. Keep ~15 best posts max; don't pad.
2. `./publish.sh` — copies `/workspace/x-digest/YYYY-MM-DD.md` (override with `X_DIGEST_SRC`) into `content/`,
   runs `build.py`, commits and pushes. Pages redeploys in about a minute.

Local preview: `python3 build.py && (cd docs && python3 -m http.server 8765)`.

## Day file format

```markdown
Summary: Anthropic cuts Haiku cost 75%; Google ships Gemini work agent; AI Big 10 hit 42% of US market cap.

<!-- update 2026-10-09 PM -->
**Anthropic launches Claude Haiku 5.5, ~75% cheaper** · [Original](https://x.com/claudeai/status/2107894039626277339) · ♥ 44k · 35h ago
> Introducing Claude Haiku 5.5: … it costs around 75% less to run than Claude Haiku 4.5.

**GPT-6 and Intelligent UI roll out to all ChatGPT users** · [Original](https://x.com/OpenAI/status/2107894997538525580) · ♥ 22k
> GPT-6 and Intelligent UI, now [[rolling out|v. 逐步推出]] in ChatGPT for everyone …
💡 Optional Chinese note.
```

- `Summary:` — 1–2 sentences, plain English, terse headline style ("X cuts…; Y ships…"). Shown on the home page
  and at the top of the day page. (Any plain text before the first post also counts as summary.)
- Post header: `**Headline** · [Original](url) · ♥ likes · age`. A leading `N. ` in the headline is allowed and
  ignored — posts are numbered in file order, so new posts can simply be appended. Likes and age are optional.
- `>` lines: the original text (English first; Chinese originals are fine). Trim to the informative part with `…`,
  without changing meaning. Several `>` lines = several paragraphs.
- Glosses: `[[phrase|pos. 中文]]` (pos optional, e.g. `[[$20B short|比预期少 200 亿美元]]`); works in headlines too.
  Legacy `word (pos. 中文)` is still parsed (attaches to the previous word, quoted phrase, or Capitalized run;
  ignored after Chinese text).
- `💡 …` lines: Chinese notes for the post above.
- Glosses and 💡 notes are hidden by default; readers toggle them with one "Show Chinese glosses & notes" button
  (remembered in localStorage).
- `<!-- … -->` lines and `#` headings are ignored. Duplicate post URLs within a day are skipped with a warning.
