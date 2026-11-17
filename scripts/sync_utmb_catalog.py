#!/usr/bin/env python3
"""Conservative UTMB event-series discovery. No login, bypass or race-detail scraping."""
import json
import re
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse, urljoin
from urllib.request import Request, urlopen
from urllib.robotparser import RobotFileParser

ROOT = Path(__file__).resolve().parents[1]
URL = "https://utmb.world/utmb-world-series-events"
OUT = ROOT / "data/utmb-events.json"
AGENT = "TrailRaceCatalog/0.1 (+public event catalog; daily)"

class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.active = None
        self.parts = []
        self.items = []
        self.anchors = 0
    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.anchors += 1
            self.active = dict(attrs).get("href", "")
            self.parts = []
    def handle_data(self, data):
        if self.active is not None:
            self.parts.append(data)
    def handle_endtag(self, tag):
        if tag == "a" and self.active is not None:
            self.items.append((self.active, " ".join(" ".join(self.parts).split())))
            self.active = None
            self.parts = []

def parse_events(html):
    p = Links()
    p.feed(html)
    found = {}
    candidate_hosts = set()
    for href, label in p.items:
        url = urlparse(urljoin(URL, href))
        host = (url.hostname or "").lower()
        if not re.fullmatch(r"[a-z0-9-]+\\.utmb\\.world", host):
            continue
        if host in ("img.utmb.world", "live.utmb.world", "eushop.utmb.world"):
            continue
        candidate_hosts.add(host)
        # Event directory links use date-range text; exclude global navigation links.
        if not re.search(r"\\b20\\d{2}\\b", label):
            continue
        slug = host.split(".")[0]
        found[slug] = {
            "id": "utmbseries_" + slug, "slug": slug,
            "name": slug.replace("-", " ").title(),
            "officialUrl": "https://" + host + "/",
            "dateRangeText": label, "eventDate": None,
            "sourceUrl": URL, "dateVerified": False
        }
    return sorted(found.values(), key=lambda e: e["slug"]), {
        "htmlBytes": len(html.encode("utf-8")),
        "anchorCount": p.anchors,
        "eventDomainCandidates": len(candidate_hosts),
        "datedEventLinks": len(found),
        "hasEventDirectoryHeading": "UTMB World Series Events" in html,
        "nextData": 'id="__NEXT_DATA__"' in html,
        "nuxtData": "__NUXT_DATA__" in html or "__NUXT__" in html,
        "utmbDomainMentions": html.lower().count(".utmb.world"),
        "eventKeywords": {k: html.lower().count(k) for k in ("lavaredo", "chianti", "istria", "mozart", "andorra")},
        "linkHostSamples": sorted({urlparse(urljoin(URL, href)).hostname or "" for href, _ in p.items})[:12],
        "eventLinkSamples": [urlparse(urljoin(URL, href)).path[:100] for href, label in p.items if any(k in (href+" "+label).lower() for k in ("lavaredo", "chianti", "istria"))][:8]
    }

def main():
    robots = RobotFileParser()
    robots.set_url("https://utmb.world/robots.txt")
    robots.read()
    if not robots.can_fetch(AGENT, URL):
        raise SystemExit("UTMB robots rules unavailable or disallow catalog fetch; no update.")
    req = Request(URL, headers={"User-Agent": AGENT, "Accept": "text/html"})
    with urlopen(req, timeout=25) as r:
        html = r.read(3_000_000).decode("utf-8", errors="replace")
    events, diagnostics = parse_events(html)
    print("Safe HTML diagnostics:", json.dumps(diagnostics, sort_keys=True))
    print(f"Catalog parser discovered {len(events)} dated event series.")
    if len(events) < 30:
        raise SystemExit(f"Only {len(events)} events parsed; refusing to overwrite existing catalog.")
    previous = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    # Date text is copied from the directory; it is an event-wide range, never a race start date.
    result = {"source": URL, "checkedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
              "scope": "event_series_only", "count": len(events), "events": events}
    if previous.get("events") == events:
        print(f"No event changes ({len(events)} series); preserving last data.")
        return
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Updated UTMB series catalog: {len(events)} entries")

if __name__ == "__main__":
    main()
