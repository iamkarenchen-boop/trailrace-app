#!/usr/bin/env python3
"""Publish a manually verified race announcement; never publish classifier guesses."""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen
import os

ROOT = Path(__file__).resolve().parents[1]
RACES = ROOT / "data/race-monitor.json"
OUT = ROOT / "data/verified-updates.json"

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--race", required=True)
    p.add_argument("--headline", required=True)
    p.add_argument("--source", required=True)
    p.add_argument("--race-year", type=int, required=True)
    p.add_argument("--distance", required=True)
    p.add_argument("--category", required=True, choices=["registration", "lottery", "eligibility"])
    p.add_argument("--review-issue", type=int, required=True)
    p.add_argument("--verified-by", required=True)
    a = p.parse_args()
    registry = json.loads(RACES.read_text(encoding="utf-8"))
    race = next((r for r in registry["events"] if r["id"] == a.race), None)
    if not race:
        p.error("Unknown race ID")
    source = urlparse(a.source)
    official = urlparse(race["officialUrl"])
    if source.scheme != "https" or not source.hostname or not (source.hostname == official.hostname or source.hostname.endswith("." + official.hostname)):
        p.error("Source must be HTTPS on the registered official event domain")
    if a.race_year < 2026 or a.race_year > 2100 or not 3 <= len(a.headline.strip()) <= 240 or not 1 <= len(a.distance.strip()) <= 60 or a.review_issue < 1:
        p.error("Invalid year, headline, distance or review issue")
    history = json.loads((ROOT / "data/monitor-history.json").read_text(encoding="utf-8"))
    matching = [e for e in history.get("events", []) if e.get("issueNumber") == a.review_issue and e.get("raceId") == a.race]
    if len(matching) != 1 or matching[0].get("status") != "needs_review":
        p.error("Review Issue must match exactly one pending alert for this race")
    token = os.environ.get("GITHUB_TOKEN")
    repository = os.environ.get("GITHUB_REPOSITORY")
    if not token or not repository:
        p.error("GitHub review authorization unavailable")
    req = Request(f"https://api.github.com/repos/{repository}/issues/{a.review_issue}", headers={
        "Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json", "User-Agent": "TrailRaceReview/0.1"})
    with urlopen(req, timeout=20) as response:
        issue = json.load(response)
    if issue.get("state") != "open" or issue.get("pull_request") or "[TEST ONLY]" in issue.get("title", ""):
        p.error("Review Issue must be open, real, and not a pull request")
    if a.source.rstrip("/") == ("https://github.com/" + repository).rstrip("/"):
        p.error("A repository URL is not an official race announcement")
    data = json.loads(OUT.read_text(encoding="utf-8"))
    records = data["updates"]
    key = f"{a.race}:{a.review_issue}"
    if any(item["id"] == key for item in records):
        p.error("This review Issue has already been published")
    records.append({
        "id": key, "raceId": a.race, "raceName": race["name"],
        "raceYear": a.race_year, "distance": a.distance.strip(), "category": a.category,
        "headline": a.headline.strip(), "sourceUrl": a.source,
        "reviewIssue": a.review_issue, "verifiedBy": a.verified_by,
        "verifiedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "status": "manually_verified"
    })
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Published reviewed update:", key)

if __name__ == "__main__":
    main()
