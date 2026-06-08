#!/usr/bin/env python3
"""The Skill Index — recompute the living index of Claude Code / AI-agent skills from live
GitHub signals and write data.json + the SEO surfaces (sitemap, rss, robots, llms.txt).

A "skill" here = a repo that packages reusable agent capability: Claude Code skills,
slash-commands, hooks, subagents, plugins, and the curated "awesome" collections of them.
We gather across several GitHub searches, dedupe, FILTER to real skills (precision over
recall — a directory people trust beats a noisy dump), categorize, and score by momentum
(stars, push-recency, rising-newness). Run daily by the GitHub Action; commit + deploy.

Only the GitHub *search* payload is used (stars/pushed_at/created_at/topics/owner/license),
so one run is a handful of API calls — no per-repo fan-out that would trip the rate limit.

Env: GITHUB_TOKEN (required for a usable rate limit).
"""
from __future__ import annotations

import json
import math
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
API = "https://api.github.com"
SITE_URL = "https://skill.kymatalabs.com"
SITE_NAME = "The Skill Index"


def token() -> str:
    return (os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or "").strip()


HEADERS = {"Accept": "application/vnd.github+json", "User-Agent": "skill-index"}
if token():
    HEADERS["Authorization"] = f"Bearer {token()}"

# Search queries that surface the skill ecosystem from different angles (multi-modal sweep).
QUERIES = [
    "topic:claude-code stars:>3",
    "topic:claude-skills stars:>2",
    "topic:agent-skills stars:>2",
    "topic:claude-code-skills stars:>1",
    "claude code skill in:name,description stars:>8",
    "agent skills in:name,description stars:>15",
    "awesome claude skills in:name,description stars:>5",
    "claude code subagents in:name,description stars:>8",
    "claude code hooks in:name,description stars:>8",
    "slash commands claude in:name,description stars:>8",
]

# A repo counts as a skill if it carries one of these signals. Precision filter: a strong
# skill signal in topics, OR a skill phrase in name/description. Tuned to keep curated lists
# and skill packs while dropping generic mega-repos that merely mention "skills".
_SKILL_TOPICS = {"claude-code", "claude-skills", "agent-skills", "claude-code-skills",
                 "claude-plugins", "claude-skill", "agent-skill", "subagents", "slash-commands"}
_SKILL_PHRASES = re.compile(
    r"\b(claude[- ]code|claude skill|agent skill|skill(s)? (pack|library|collection|directory)"
    r"|subagent|slash[- ]command|\.claude|claude plugin|skill marketplace)\b", re.I)
# Hard denylist: repos that match a phrase/topic but are NOT skills.
_DENY = {"snailclimb/javaguide", "danny-avila/librechat", "lobehub/lobehub",
         "kubesphere/kubesphere", "alibaba/zvec", "chatboxai/chatbox", "xixu-me/xget",
         "ikaijua/awesome-aitools", "thinkinaixyz/deepchat", "gosom/google-maps-scraper",
         "htmlstreamofficial/preline"}
# Anti-patterns: a description that marks the repo as a platform/app/library, NOT a skill.
# Applied even to topic-matched repos (a mis-tagged claude-code topic shouldn't smuggle in a
# Kubernetes platform). Keeps precision high — a directory people trust beats a noisy dump.
_ANTI = re.compile(
    r"\b(container platform|vector database|ui (kit|component|components|library)|prebuilt ui"
    r"|ai client|chat client|chatgpt clone|desktop (app|client)|browser extension"
    r"|web scraper|scrape data|kubernetes|acceleration engine|inference engine"
    r"|database|crm|erp)\b", re.I)


def gh(path_or_url: str, *, retries: int = 4):
    url = path_or_url if path_or_url.startswith("http") else f"{API}{path_or_url}"
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            last = e
            if e.code in (403, 429):          # rate limit — back off and retry
                reset = e.headers.get("X-RateLimit-Reset")
                wait = 5 * (attempt + 1)
                if reset:
                    try:
                        wait = max(wait, min(60, int(reset) - int(time.time()) + 2))
                    except ValueError:
                        pass
                print(f"  rate-limited on {url} — sleeping {wait}s", file=sys.stderr)
                time.sleep(wait)
                continue
            if 500 <= e.code < 600:
                time.sleep(3 * (attempt + 1))
                continue
            raise
        except (urllib.error.URLError, TimeoutError) as e:
            last = e
            time.sleep(3 * (attempt + 1))
    if last:
        raise last
    raise RuntimeError(f"gh failed: {url}")


def search(q: str, per_page: int = 40) -> list[dict]:
    url = (f"{API}/search/repositories?q={urllib.parse.quote(q)}"
           f"&sort=stars&order=desc&per_page={per_page}")
    try:
        return gh(url).get("items", [])
    except Exception as e:                     # one bad query never sinks the run
        print(f"  query failed [{q}]: {e}", file=sys.stderr)
        return []


def is_skill(r: dict) -> bool:
    full = (r.get("full_name") or "").lower()
    if full in _DENY:
        return False
    desc = r.get("description") or ""
    if _ANTI.search(desc):                     # platform/app/library — not a skill
        return False
    topics = {t.lower() for t in (r.get("topics") or [])}
    if topics & _SKILL_TOPICS:
        return True
    blob = f"{r.get('name','')} {desc}"
    return bool(_SKILL_PHRASES.search(blob))


def categorize(r: dict) -> str:
    topics = {t.lower() for t in (r.get("topics") or [])}
    name = (r.get("name") or "").lower()
    desc = (r.get("description") or "").lower()
    blob = f"{name} {desc} {' '.join(topics)}"
    if re.search(r"\bawesome\b|curated|directory|collection of", blob):
        return "Collections"
    if re.search(r"\bmcp\b|model context protocol", blob):
        return "MCP & Tools"
    if re.search(r"subagent|multi-agent|orchestrat", blob):
        return "Subagents"
    if re.search(r"hook|slash[- ]?command|settings|workflow", blob):
        return "Commands & Hooks"
    if re.search(r"design|ui|ux|frontend|css|figma", blob):
        return "Design & UI"
    if re.search(r"test|review|debug|lint|security|audit", blob):
        return "Quality & Review"
    if re.search(r"memory|context|rag|knowledge", blob):
        return "Memory & Context"
    if re.search(r"writ|content|doc|seo|marketing", blob):
        return "Writing & Content"
    return "General Skills"


def days_since(iso: str | None) -> float | None:
    if not iso:
        return None
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return (datetime.now(timezone.utc) - dt).total_seconds() / 86400.0
    except ValueError:
        return None


def momentum(r: dict, max_stars: int) -> int:
    """0-100 from stars (log-scaled), push-recency, and rising-newness. No per-repo calls."""
    stars = r.get("stargazers_count", 0) or 0
    star_norm = math.log10(stars + 1) / math.log10(max(max_stars, 10) + 1)
    pushed = days_since(r.get("pushed_at"))
    if pushed is None:
        recency = 0.2
    else:
        recency = max(0.0, 1.0 - max(0.0, pushed) / 180.0)   # full <0d, 0 by 180d
    created = days_since(r.get("created_at"))
    young = 0.0
    if created is not None and created < 120 and stars >= 20:
        young = 1.0 - created / 120.0                          # rising-fast bonus
    score = 0.55 * star_norm + 0.32 * recency + 0.13 * young
    return max(1, min(100, round(score * 100)))


def slugify(full_name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", full_name.lower()).strip("-")


def build_items() -> list[dict]:
    seen: dict[str, dict] = {}
    for q in QUERIES:
        for r in search(q):
            full = r.get("full_name")
            if not full or full in seen:
                continue
            if not is_skill(r):
                continue
            seen[full] = r
        time.sleep(0.7)                        # be gentle on the search rate limit
    raw = list(seen.values())
    max_stars = max((r.get("stargazers_count", 0) or 0) for r in raw) if raw else 10
    items = []
    for r in raw:
        owner = r.get("owner") or {}
        items.append({
            "name": r.get("name", ""),
            "full_name": r.get("full_name", ""),
            "slug": slugify(r.get("full_name", "")),
            "url": r.get("html_url", ""),
            "owner": owner.get("login", ""),
            "owner_avatar": owner.get("avatar_url", ""),
            "stars": r.get("stargazers_count", 0) or 0,
            "forks": r.get("forks_count", 0) or 0,
            "open_issues": r.get("open_issues_count", 0) or 0,
            "language": r.get("language") or "",
            "license": ((r.get("license") or {}) or {}).get("spdx_id") or "",
            "pushed_at": r.get("pushed_at"),
            "created_at": r.get("created_at"),
            "description": (r.get("description") or "").strip(),
            "topics": r.get("topics") or [],
            "category": categorize(r),
            "momentum": momentum(r, max_stars),
        })
    items.sort(key=lambda x: (x["momentum"], x["stars"]), reverse=True)
    for i, it in enumerate(items, 1):
        it["rank"] = i
    return items


def write_json(items: list[dict]) -> dict:
    cats: dict[str, int] = {}
    for it in items:
        cats[it["category"]] = cats.get(it["category"], 0) + 1
    data = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "count": len(items),
        "categories": [{"name": k, "count": v} for k, v in sorted(cats.items(), key=lambda x: -x[1])],
        "items": items,
    }
    with open(os.path.join(HERE, "data.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    return data


def write_seo(data: dict) -> None:
    items = data["items"]
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # sitemap.xml — home + every detail page
    urls = [f"  <url><loc>{SITE_URL}/</loc><lastmod>{now}</lastmod><changefreq>daily</changefreq><priority>1.0</priority></url>"]
    for it in items:
        urls.append(f"  <url><loc>{SITE_URL}/p/{it['slug']}/</loc><lastmod>{now}</lastmod>"
                    f"<changefreq>weekly</changefreq><priority>0.6</priority></url>")
    sitemap = ('<?xml version="1.0" encoding="UTF-8"?>\n'
               '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
               + "\n".join(urls) + "\n</urlset>\n")
    open(os.path.join(HERE, "sitemap.xml"), "w", encoding="utf-8").write(sitemap)

    # robots.txt
    open(os.path.join(HERE, "robots.txt"), "w", encoding="utf-8").write(
        f"User-agent: *\nAllow: /\nSitemap: {SITE_URL}/sitemap.xml\n")

    # rss.xml — top 30 by momentum
    def esc(s):
        return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    rss_items = []
    for it in items[:30]:
        rss_items.append(
            f"    <item><title>{esc(it['full_name'])} — momentum {it['momentum']}</title>"
            f"<link>{SITE_URL}/p/{it['slug']}/</link>"
            f"<guid isPermaLink=\"false\">{esc(it['full_name'])}</guid>"
            f"<description>{esc(it['description'][:300])}</description></item>")
    rss = ('<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0">\n  <channel>\n'
           f"    <title>{SITE_NAME}</title>\n    <link>{SITE_URL}</link>\n"
           f"    <description>The living index of Claude Code &amp; AI-agent skills, ranked by momentum.</description>\n"
           + "\n".join(rss_items) + "\n  </channel>\n</rss>\n")
    open(os.path.join(HERE, "rss.xml"), "w", encoding="utf-8").write(rss)

    # llms.txt — a machine-readable summary for AI crawlers
    lines = [f"# {SITE_NAME}", "",
             "> The living index of Claude Code and AI-agent skills, ranked daily by momentum",
             "> (stars, push-recency, rising-newness) from live GitHub signals.", "",
             f"Updated: {data['generated_at']}", f"Skills indexed: {data['count']}", "",
             "## Top skills by momentum", ""]
    for it in items[:40]:
        lines.append(f"- [{it['full_name']}]({it['url']}) — momentum {it['momentum']}, "
                     f"⭐{it['stars']} — {it['category']} — {it['description'][:100]}")
    open(os.path.join(HERE, "llms.txt"), "w", encoding="utf-8").write("\n".join(lines) + "\n")


def main() -> int:
    if not token():
        print("WARNING: no GITHUB_TOKEN — low rate limit, results may be partial", file=sys.stderr)
    items = build_items()
    if not items:
        print("ERROR: no skills found — refusing to write empty data.json", file=sys.stderr)
        return 1
    data = write_json(items)
    write_seo(data)
    print(f"wrote data.json: {len(items)} skills across {len(data['categories'])} categories")
    print("  top 5:", ", ".join(f"{it['full_name']}({it['momentum']})" for it in items[:5]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
