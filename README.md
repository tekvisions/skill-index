# The Skill Index

A living, daily-updated directory of **Claude Code & AI-agent skills** — skills, subagents,
slash-commands, hooks, and curated collections — ranked by **momentum** (stars, push-recency,
and how fast a repo is rising) computed from live GitHub signals.

Live: https://skill-index.vercel.app

## How it works (self-updating)

A daily GitHub Action runs the pipeline and redeploys:

1. `build_data.py` — searches GitHub across several skill-ecosystem queries, dedupes, filters
   to real skills (precision over recall), categorizes, scores momentum → `data.json` + SEO
   surfaces (`sitemap.xml`, `rss.xml`, `robots.txt`, `llms.txt`).
2. `gen_details.py` — one SEO'd landing page per skill (`p/<slug>/`) with `SoftwareSourceCode`
   JSON-LD + breadcrumb.
3. `gen_og.py` — renders the Open Graph card.
4. `deploy.py` — ships the static site to Vercel via the REST API (no CLI).

Static HTML/CSS/JS — no build step, no framework. Editorial almanac aesthetic
(Fraunces + JetBrains Mono, warm paper / deep ink themes).

## Run locally

```bash
GITHUB_TOKEN=... python3 build_data.py
python3 gen_details.py && python3 gen_og.py
python3 -m http.server 8080   # open http://localhost:8080
```

## Deploy

```bash
VERCEL_TOKEN=... python3 deploy.py
```
