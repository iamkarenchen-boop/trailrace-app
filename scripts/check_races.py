#!/usr/bin/env python3
"""Conservative public-page change detector. Changes are NOT verified race announcements."""
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "data" / "race-monitor.json"
SNAPSHOTS = ROOT / "data" / "page-snapshots.json"
HISTORY = ROOT / "data" / "monitor-history.json"
KEYWORDS = re.compile(r"registration|register|lottery|ballot|drawing|qualification|qualifying|running stones|报名|抽签|资格|inscription|tirage au sort|iscrizioni|anmeldung", re.I)
MAX_BYTES = 1_000_000
CATEGORIES = [
    ("registration_deadline", "high", r"registration deadline|registration closes?|closing date|报名截止|截止报名|date limite d.inscription|fin des inscriptions"),
    ("registration_open", "high", r"registration opens?|registration is open|register now|报名开放|开放报名|ouverture des inscriptions|iscrizioni aperte"),
    ("lottery", "high", r"lottery|ballot|draw results?|tirage au sort|抽签|中签"),
    ("eligibility", "high", r"qualif(?:ication|ying)|running stones|eligib(?:le|ility)|参赛资格|报名资格"),
    ("race_category", "medium", r"race distance|race format|new distance|取消组别|新增组别|course distance"),
]
def classify(snippets):
    text = " ".join(snippets)
    matched = [{"category": category, "priority": priority} for category, priority, pattern in CATEGORIES if re.search(pattern, text, re.I)]
    return matched or [{"category": "other_page_text", "priority": "low"}]


class PageText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.skip = 0
    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "svg", "noscript"):
            self.skip += 1
    def handle_endtag(self, tag):
        if tag in ("script", "style", "svg", "noscript") and self.skip:
            self.skip -= 1
    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)

def read_json(path, fallback):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return fallback

def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def extract(url):
    request = Request(url, headers={"User-Agent": "TrailRacePublicPageMonitor/0.1 (GitHub Actions; public metadata only)", "Accept": "text/html"})
    with urlopen(request, timeout=20) as response:
        if response.status != 200:
            raise ValueError("Unexpected HTTP status")
        if "text/html" not in response.headers.get("Content-Type", ""):
            raise ValueError("Not an HTML page")
        raw = response.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise ValueError("Page exceeds size limit")
        charset = response.headers.get_content_charset() or "utf-8"
    parser = PageText()
    parser.feed(raw.decode(charset, errors="replace"))
    text = re.sub(r"\s+", " ", " ".join(parser.parts)).strip()
    snippets = []
    for match in list(KEYWORDS.finditer(text))[:60]:
        snippets.append(text[max(0, match.start()-85):match.end()+150])
    normalized = sorted(set(re.sub(r"\s+", " ", snippet).strip().lower() for snippet in snippets))
    return hashlib.sha256("\n".join(normalized).encode("utf-8")).hexdigest(), len(normalized)

def main():
    registry = read_json(REGISTRY, {})
    previous = read_json(SNAPSHOTS, {})
    history = read_json(HISTORY, {"events": []})
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    success = 0
    for event in registry.get("events", []):
        key = event["id"]
        url = event["officialUrl"]
        try:
            digest, count, snippets = extract(url)
            success += 1
            old = previous.get(key, {})
            if old.get("hash") and old["hash"] != digest:
                old_snippets = set(old.get("snippets", []))
                added = [item for item in snippets if item not in old_snippets] if "snippets" in old else []
                # Existing snapshots only contain hashes. Never claim a precise category without an old text baseline.
                labels = classify(added) if added else [{"category": "unclassified_change", "priority": "low"}]
                history["events"].append({"raceId": key, "detectedAt": now, "type": "page_keyword_change", "status": "needs_review", "sourceUrl": url, "categories": labels, "description": "Potentially relevant page text changed. Categories are automated hints, not confirmed facts."})
            previous[key] = {"hash": digest, "keywordMatches": count, "lastSuccessfulCheck": now, "sourceUrl": url}
            event["lastChecked"] = now
            event["checkStatus"] = "checked"
        except (HTTPError, URLError, TimeoutError, ValueError, UnicodeError) as error:
            event["checkStatus"] = "error"
            event["lastErrorAt"] = now
            print(f"{key}: check failed ({type(error).__name__})", file=sys.stderr)
    history["events"] = history["events"][-100:]
    registry["monitoringActive"] = True
    registry["lastRun"] = now
    registry["lastRunSuccessCount"] = success
    write_json(REGISTRY, registry)
    write_json(SNAPSHOTS, previous)
    write_json(HISTORY, history)
    print(f"Checked {success}/{len(registry.get('events', []))} sources; {len(history['events'])} retained review items.")

if __name__ == "__main__":
    main()
