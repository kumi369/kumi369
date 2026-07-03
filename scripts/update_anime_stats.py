from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = ROOT / "assets" / "anime-stats.svg"
USERNAME = os.getenv("GITHUB_USERNAME", "kumi369")
TOKEN = os.getenv("GITHUB_TOKEN")


@dataclass
class Stats:
    total_stars: int
    year_commits: int
    total_prs: int
    total_issues: int
    contributed_repos: int
    year_label: int


def github_graphql(query: str, variables: dict) -> dict:
    if not TOKEN:
        raise RuntimeError("GITHUB_TOKEN is required to update anime stats.")

    body = json.dumps({"query": query, "variables": variables}).encode("utf-8")
    request = Request(
        "https://api.github.com/graphql",
        data=body,
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Content-Type": "application/json",
            "User-Agent": f"{USERNAME}-anime-stats-updater",
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        message = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"GitHub API request failed: {message}") from exc

    if payload.get("errors"):
        raise RuntimeError(f"GitHub API returned errors: {payload['errors']}")

    return payload["data"]


def fetch_total_stars() -> int:
    query = """
    query($username: String!, $cursor: String) {
      user(login: $username) {
        repositories(
          ownerAffiliations: OWNER
          isFork: false
          first: 100
          after: $cursor
          privacy: PUBLIC
        ) {
          nodes {
            stargazerCount
          }
          pageInfo {
            hasNextPage
            endCursor
          }
        }
      }
    }
    """

    cursor = None
    total = 0

    while True:
        data = github_graphql(query, {"username": USERNAME, "cursor": cursor})
        repositories = data["user"]["repositories"]
        total += sum(repo["stargazerCount"] for repo in repositories["nodes"])

        if not repositories["pageInfo"]["hasNextPage"]:
            return total

        cursor = repositories["pageInfo"]["endCursor"]


def fetch_contribution_stats() -> Stats:
    now = datetime.now(timezone.utc)
    year_start = datetime(now.year, 1, 1, tzinfo=timezone.utc).isoformat()
    year_end = datetime(now.year + 1, 1, 1, tzinfo=timezone.utc).isoformat()

    query = """
    query($username: String!, $from: DateTime!, $to: DateTime!) {
      user(login: $username) {
        contributionsCollection(from: $from, to: $to) {
          totalCommitContributions
          totalPullRequestContributions
          totalIssueContributions
          totalRepositoriesWithContributedCommits
        }
      }
    }
    """

    data = github_graphql(
        query,
        {"username": USERNAME, "from": year_start, "to": year_end},
    )
    contributions = data["user"]["contributionsCollection"]

    return Stats(
        total_stars=fetch_total_stars(),
        year_commits=contributions["totalCommitContributions"],
        total_prs=contributions["totalPullRequestContributions"],
        total_issues=contributions["totalIssueContributions"],
        contributed_repos=contributions["totalRepositoriesWithContributedCommits"],
        year_label=now.year,
    )


def build_svg(stats: Stats) -> str:
    return f"""<svg width="920" height="310" viewBox="0 0 920 310" fill="none" xmlns="http://www.w3.org/2000/svg">
  <rect width="920" height="310" rx="20" fill="#FFFFFF"/>
  <rect x="1.5" y="1.5" width="917" height="307" rx="18.5" stroke="#E5E7EB" stroke-width="3"/>
  <text x="42" y="58" fill="#111827" font-family="Segoe UI, Arial, sans-serif" font-size="30" font-weight="700">GitHub Stats</text>
  <text x="42" y="86" fill="#64748B" font-family="Segoe UI, Arial, sans-serif" font-size="15">anime mode • auto-updating</text>

  <rect x="38" y="118" width="380" height="42" rx="14" fill="#F8FAFC"/>
  <text x="58" y="145" fill="#334155" font-family="Segoe UI, Arial, sans-serif" font-size="18" font-weight="600">Total Stars</text>
  <text x="380" y="145" text-anchor="end" fill="#0F172A" font-family="Segoe UI, Arial, sans-serif" font-size="24" font-weight="800">{stats.total_stars}</text>

  <rect x="38" y="170" width="380" height="42" rx="14" fill="#F8FAFC"/>
  <text x="58" y="197" fill="#334155" font-family="Segoe UI, Arial, sans-serif" font-size="18" font-weight="600">{stats.year_label} Commits</text>
  <text x="380" y="197" text-anchor="end" fill="#0F172A" font-family="Segoe UI, Arial, sans-serif" font-size="24" font-weight="800">{stats.year_commits}</text>

  <rect x="38" y="222" width="380" height="42" rx="14" fill="#F8FAFC"/>
  <text x="58" y="249" fill="#334155" font-family="Segoe UI, Arial, sans-serif" font-size="18" font-weight="600">Total PRs</text>
  <text x="380" y="249" text-anchor="end" fill="#0F172A" font-family="Segoe UI, Arial, sans-serif" font-size="24" font-weight="800">{stats.total_prs}</text>

  <rect x="450" y="118" width="180" height="65" rx="18" fill="#EEF2FF"/>
  <text x="470" y="145" fill="#475569" font-family="Segoe UI, Arial, sans-serif" font-size="16" font-weight="600">Issues</text>
  <text x="470" y="170" fill="#1E293B" font-family="Segoe UI, Arial, sans-serif" font-size="34" font-weight="800">{stats.total_issues}</text>

  <rect x="450" y="198" width="180" height="65" rx="18" fill="#ECFEFF"/>
  <text x="470" y="225" fill="#475569" font-family="Segoe UI, Arial, sans-serif" font-size="16" font-weight="600">Contributed</text>
  <text x="470" y="250" fill="#1E293B" font-family="Segoe UI, Arial, sans-serif" font-size="34" font-weight="800">{stats.contributed_repos}</text>

  <g transform="translate(670 78)">
    <path d="M62 14L90 34L78 0L62 14Z" fill="#5B7CFA"/>
    <path d="M162 14L134 34L146 0L162 14Z" fill="#5B7CFA"/>
    <ellipse cx="112" cy="76" rx="56" ry="58" fill="#D9E6FF"/>
    <path d="M68 76C68 44 88 20 112 20C136 20 156 44 156 76V114H68V76Z" fill="#7AA2FF"/>
    <path d="M86 116C86 144 98 164 112 164C126 164 138 144 138 116H86Z" fill="#F8D4D8"/>
    <ellipse cx="94" cy="78" rx="6" ry="10" fill="#1E293B"/>
    <ellipse cx="130" cy="78" rx="6" ry="10" fill="#1E293B"/>
    <path d="M106 96C110 100 114 100 118 96" stroke="#1E293B" stroke-width="4" stroke-linecap="round"/>
    <circle cx="82" cy="94" r="7" fill="#F9A8D4" fill-opacity="0.7"/>
    <circle cx="142" cy="94" r="7" fill="#F9A8D4" fill-opacity="0.7"/>
    <rect x="72" y="168" width="80" height="58" rx="14" fill="#FFFFFF" stroke="#CBD5E1" stroke-width="3"/>
    <text x="112" y="207" text-anchor="middle" fill="#0F172A" font-family="Segoe UI, Arial, sans-serif" font-size="36" font-weight="800">{stats.year_commits}</text>
    <path d="M94 132L80 182" stroke="#7AA2FF" stroke-width="10" stroke-linecap="round"/>
    <path d="M130 132L144 182" stroke="#7AA2FF" stroke-width="10" stroke-linecap="round"/>
    <path d="M88 226L76 274" stroke="#7AA2FF" stroke-width="12" stroke-linecap="round"/>
    <path d="M136 226L148 274" stroke="#7AA2FF" stroke-width="12" stroke-linecap="round"/>
    <path d="M72 276H92" stroke="#1E293B" stroke-width="8" stroke-linecap="round"/>
    <path d="M132 276H152" stroke="#1E293B" stroke-width="8" stroke-linecap="round"/>
  </g>
</svg>
"""


def main() -> None:
    stats = fetch_contribution_stats()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(build_svg(stats), encoding="utf-8")
    print(f"Updated {OUTPUT_PATH} for {USERNAME}.")


if __name__ == "__main__":
    main()
