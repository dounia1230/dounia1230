"""Refresh the profile card from GitHub's public contribution graph and API.

Run with Python 3.11+. GITHUB_TOKEN is optional for local runs.
The contribution total matches the public profile, including any private
contribution counts the account owner has chosen to make public.
"""

import html
import json
import os
from pathlib import Path
import re
from urllib.parse import urlencode
from urllib.request import Request, urlopen


USERNAME = "dounia1230"
ROOT = Path(__file__).resolve().parents[1]


def fetch(url, *, api=False):
    headers = {"User-Agent": f"{USERNAME}-profile-stats"}
    if api:
        headers["Accept"] = "application/vnd.github+json"
        if token := os.environ.get("GITHUB_TOKEN"):
            headers["Authorization"] = f"Bearer {token}"
    with urlopen(Request(url, headers=headers), timeout=30) as response:
        text = response.read().decode("utf-8")
    return json.loads(text) if api else text


def get_stats():
    graph = fetch(f"https://github.com/users/{USERNAME}/contributions")
    headings = re.findall(r"<h2\b[^>]*>(.*?)</h2>", graph, re.S)
    contribution_total = None
    for heading in headings:
        text = html.unescape(re.sub(r"<[^>]+>", " ", heading))
        text = " ".join(text.split())
        match = re.search(r"\b([\d,]+) contributions? in the last year\b", text)
        if match:
            contribution_total = int(match[1].replace(",", ""))
            break
    if contribution_total is None:
        raise ValueError("GitHub contribution total was not found; keeping the existing card")

    repositories = []
    page = 1
    while True:
        batch = fetch(
            f"https://api.github.com/users/{USERNAME}/repos?per_page=100&page={page}",
            api=True,
        )
        repositories.extend(batch)
        if len(batch) < 100:
            break
        page += 1

    counts = {}
    for kind in ("pr", "issue"):
        query = urlencode({"q": f"author:{USERNAME} type:{kind}", "per_page": 1})
        result = fetch(f"https://api.github.com/search/issues?{query}", api=True)
        if result.get("incomplete_results", True):
            raise ValueError("GitHub returned incomplete search results; keeping the existing card")
        counts[kind] = result["total_count"]

    return [
        ("Contributions (last year)", contribution_total),
        ("Stars earned", sum(repo["stargazers_count"] for repo in repositories if not repo["fork"])),
        ("Public repositories", len(repositories)),
        ("Public pull requests", counts["pr"]),
        ("Public issues", counts["issue"]),
    ]


def render(stats):
    rows = []
    for index, (label, value) in enumerate(stats):
        y = 65 + index * 25
        rows.append(
            f'<circle cx="26" cy="{y - 5}" r="4" fill="#c4b5fd" />'
            f'<text x="42" y="{y}">{html.escape(label)}:</text>'
            f'<text x="440" y="{y}" text-anchor="end">{value:,}</text>'
        )
    description = "; ".join(f"{label}: {value:,}" for label, value in stats)
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="495" height="195" viewBox="0 0 495 195" role="img" aria-labelledby="title desc">
  <title id="title">Dounia Ouakil's GitHub Stats</title>
  <desc id="desc">{html.escape(description)}. Refreshed daily from GitHub.</desc>
  <rect width="495" height="195" rx="6" fill="#0d1117" />
  <style>text {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif; font-size: 14px; font-weight: 600; fill: #c9d1d9; }} .title {{ font-size: 18px; fill: #f4a6c4; }}</style>
  <text x="20" y="30" class="title">Dounia Ouakil's GitHub Stats</text>
  {''.join(rows)}
</svg>
'''


if __name__ == "__main__":
    stats = get_stats()
    card = render(stats)
    (ROOT / "assets" / "github-stats.svg").write_text(card, encoding="utf-8")
    for label, value in stats:
        print(f"{label}: {value:,}")
