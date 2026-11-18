#!/usr/bin/env python3
"""Daily source availability audit for every curated race; never infer race facts from HTML."""
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from urllib.robotparser import RobotFileParser
from urllib.error import HTTPError, URLError

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"data"
RACES=DATA/"utmb-race-distances.json"
OUT=DATA/"race-source-audit.json"
AGENT="TrailRaceSourceAudit/1.0 (public metadata; contact repository owner)"
def main():
    races=json.loads(RACES.read_text(encoding="utf-8"))["races"]
    now=datetime.now(timezone.utc).isoformat(timespec="seconds")
    urls=sorted({r.get("sourceUrl","") for r in races if r.get("sourceUrl","").startswith("https://")})
    robots={}
    results={}
    for url in urls:
        parsed=urlparse(url)
        origin=f"{parsed.scheme}://{parsed.netloc}"
        if origin not in robots:
            rp=RobotFileParser()
            rp.set_url(origin+"/robots.txt")
            try:
                rp.read()
                robots[origin]=rp
            except Exception:
                robots[origin]=None
        if robots[origin] is None or not robots[origin].can_fetch(AGENT,url):
            results[url]={"status":"not_checked","reason":"robots_unavailable_or_disallowed"}
            continue
        try:
            req=Request(url,headers={"User-Agent":AGENT,"Accept":"text/html"})
            with urlopen(req,timeout=15) as response:
                content_type=response.headers.get("Content-Type","")
                if response.status!=200 or "text/html" not in content_type:
                    raise ValueError("unexpected response")
                response.read(1024)
            results[url]={"status":"reachable","checkedAt":now}
        except (HTTPError,URLError,TimeoutError,ValueError) as error:
            results[url]={"status":"error","errorType":type(error).__name__}
        time.sleep(0.25)
    rows=[]
    for race in races:
        url=race.get("sourceUrl","")
        result=results.get(url,{"status":"not_checked","reason":"no_source_url"})
        rows.append({"raceId":race["id"],"sourceUrl":url,"sourceStatus":result["status"],
                     "lastDataVerifiedAt":race.get("verifiedAt"),
                     "dataCurrent":False,
                     "note":"Source reachability is not verification of distance, date, elevation, stones or registration."})
    report={"checkedAt":now,"raceCount":len(rows),"uniqueSourceCount":len(urls),
            "reachableSourceCount":sum(x["status"]=="reachable" for x in results.values()),
            "scope":"source_reachability_only","sources":results,"races":rows}
    previous=json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    if previous.get("sources")==results and previous.get("races")==rows:
        print("No source audit changes")
        return
    OUT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"Audited {len(rows)} race entries across {len(urls)} unique official URLs")
if __name__=="__main__":
    main()
