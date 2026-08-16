#!/usr/bin/env python3
"""
Fetches recent public GitHub activity and recently-updated repos for
SHRUTI-BARUA and injects them into README.md between marker comments.

Runs stdlib-only (urllib) so the GitHub Actions workflow needs no pip install.
"""
import json
import os
import re
import urllib.request
from datetime import datetime

USERNAME = "SHRUTI-BARUA"
README_PATH = "README.md"
HEADERS = {"User-Agent": USERNAME, "Accept": "application/vnd.github+json"}

# GitHub Actions injects this automatically (see workflow's `env:` block).
# Authenticated requests get a 5,000/hr rate limit instead of 60/hr.
_token = os.environ.get("GITHUB_TOKEN")
if _token:
    HEADERS["Authorization"] = f"Bearer {_token}"


def fetch_json(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode())


def fmt_date(iso_str):
    return datetime.strptime(iso_str, "%Y-%m-%dT%H:%M:%SZ").strftime("%Y-%m-%d")


def build_activity_section():
    """Last few PushEvents -> 'repo - message - date' lines."""
    try:
        events = fetch_json(f"https://api.github.com/users/{USERNAME}/events/public")
    except Exception as e:
        return [f"_Couldn't load recent activity ({e})_"]

    lines = []
    seen = set()
    for ev in events:
        if ev.get("type") != "PushEvent":
            continue
        repo = ev["repo"]["name"]
        commits = ev.get("payload", {}).get("commits", [])
        if not commits:
            continue
        msg = commits[-1]["message"].splitlines()[0][:80]
        key = (repo, msg)
        if key in seen:
            continue
        seen.add(key)
        date = fmt_date(ev["created_at"])
        lines.append(f"[{repo}](https://github.com/{repo}) — {msg} - {date}")
        if len(lines) >= 5:
            break

    if not lines:
        lines = ["_No recent public push activity yet — go commit something!_"]
    return lines


def build_repos_section():
    """Most recently updated public repos -> name + description."""
    try:
        repos = fetch_json(
            f"https://api.github.com/users/{USERNAME}/repos?sort=updated&per_page=6"
        )
    except Exception as e:
        return [f"_Couldn't load repos ({e})_"]

    lines = []
    for r in repos:
        if r.get("fork"):
            continue
        name = r["name"]
        desc = r.get("description") or "No description yet"
        date = fmt_date(r["pushed_at"])
        lines.append(f"[{name}]({r['html_url']}) — {desc} - {date}")
        if len(lines) >= 5:
            break

    if not lines:
        lines = ["_No public repos found yet_"]
    return lines


def replace_section(content, marker, lines):
    start = f"<!-- {marker} starts -->"
    end = f"<!-- {marker} ends -->"
    block = "\n".join(lines)
    pattern = re.compile(re.escape(start) + r".*?" + re.escape(end), re.DOTALL)
    replacement = f"{start}\n{block}\n{end}"
    if not pattern.search(content):
        raise SystemExit(f"Markers for '{marker}' not found in {README_PATH}")
    return pattern.sub(replacement, content)


def main():
    with open(README_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    content = replace_section(content, "activity", build_activity_section())
    content = replace_section(content, "repos", build_repos_section())

    with open(README_PATH, "w", encoding="utf-8") as f:
        f.write(content)

    print("README.md updated.")


if __name__ == "__main__":
    main()
