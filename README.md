# X Digest

A daily digest of the most useful posts on X, published at <https://x-digest.theodoruszq.win/>
(custom domain; `build.py` writes `docs/CNAME` on every build) and <https://theodoruszq.github.io/x-digest/>.
All internal links and assets are relative, so the site works at a domain root or under `/x-digest/`.
Styled to match <https://theodoruszq.github.io/> (Lato woff2 vendored from its `/fonts/` into `src/fonts/`, same 960px frame and colours).
The left column is a month archive (`2026-10`, sticky beside that month's days; a header on mobile); a small About link (theodoruszq.github.io) sits top-right next to the theme toggle.

```
content/YYYY-MM-DD.md   one source file per day
src/                    style.css, digest.js, favicon, fonts/ (copied to docs/assets on build)
build.py                content/ → docs/ (pure Python 3.9+, no dependencies)
docs/                   built site — GitHub Pages serves main:/docs
publish.sh              sync day files from $X_DIGEST_SRC, rebuild, commit, push
screenshots.py          optional Playwright screenshots
```

## Workflow (twice a day)
1. Append the new posts to today's file (`YYYY-MM-DD.md`, created on the first run of the day) and refresh the
   `Summary:` line so it covers the whole day. Keep ~15 best posts max; don't pad.
2. `./publish.sh` — copies `/workspace/x-digest/YYYY-MM-DD.md` (override with `X_DIGEST_SRC`) into `content/`,
   runs `build.py`, commits if anything changed, and pushes whenever local `main` differs from GitHub. Pages redeploys in about a minute.

Local preview: `python3 build.py && (cd docs && python3 -m http.server 8765)`.

## Day file format

```markdown
Summary: Anthropic cuts Haiku cost 75%; Google ships Gemini work agent; AI Big 10 hit 42% of US market cap.

<!-- update 2026-10-09 PM -->
**Anthropic launches Claude Haiku 5.5, ~75% cheaper** · [Original](https://x.com/claudeai/status/2107894039626277339) · ♥ 44k · 2026-10-07T18:01:16Z
> Introducing Claude Haiku 5.5: … it costs around 75% less to run than Claude Haiku 4.5.

**GPT-6 and Intelligent UI roll out to all ChatGPT users** · [Original](https://x.com/OpenAI/status/2107894997538525580) · ♥ 22k · 2026-10-07T18:05:04Z
> GPT-6 and Intelligent UI, now [[rolling out|v. 逐步推出]] in ChatGPT for everyone …
💡 Optional Chinese note.
```

- `Summary:` — 1–2 sentences, plain English, terse headline style ("X cuts…; Y ships…"). Shown on the home page
  and at the top of the day page. (Any plain text before the first post also counts as summary.)
- Post header: `**Headline** · [Original](url) · ♥ likes · created_at`. A leading `N. ` in the headline is allowed and
  ignored — posts are numbered in file order, so new posts can simply be appended. Likes and created_at are optional.
- `created_at`: the post's exact creation time in ISO 8601 UTC, straight from the X API (`get_posts_by_ids` with
  `post.fields=created_at`), e.g. `2026-10-08T18:05:00Z` (fractional seconds / `+00:00` offsets also accepted).
  The page shows it in the viewer's local time zone via `Intl` ("Oct 9, 03:01"; full date + zone on hover),
  inside `<time datetime>`; without JavaScript it reads "Oct 8, 18:05 UTC". Old relative ages ("35h ago") are
  accepted but not shown.
- `>` lines: the original text (English first; Chinese originals are fine). Trim to the informative part with `…`,
  without changing meaning. Several `>` lines = several paragraphs.
- Glosses: `[[phrase|pos. 中文]]` (pos optional, e.g. `[[$20B short|比预期少 200 亿美元]]`); works in headlines too.
  Legacy `word (pos. 中文)` is still parsed (attaches to the previous word, quoted phrase, or Capitalized run;
  ignored after Chinese text).
- `💡 …` lines: Chinese notes for the post above.
- Glosses and 💡 notes are hidden by default; readers toggle them with one "Show Chinese glosses & notes" button
  (remembered in localStorage).
- `<!-- … -->` lines and `#` headings are ignored. Duplicate post URLs within a day are skipped with a warning.
