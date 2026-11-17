#!/usr/bin/env python3
"""Mark an existing monitored GitHub Issue as false positive, without publishing."""
import argparse
import json
import os
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError

ROOT=Path(__file__).resolve().parents[1]
HISTORY=ROOT/"data/monitor-history.json"

def api(path, method="GET", data=None):
    repo=os.environ["GITHUB_REPOSITORY"]
    token=os.environ["GITHUB_TOKEN"]
    req=Request(f"https://api.github.com/repos/{repo}/{path}",
        data=json.dumps(data).encode() if data is not None else None,
        headers={"Authorization":f"Bearer {token}","Accept":"application/vnd.github+json",
                 "Content-Type":"application/json","User-Agent":"TrailRaceReview/0.1"},method=method)
    with urlopen(req,timeout=20) as res:
        return json.load(res)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--issue",type=int,required=True)
    p.add_argument("--reason",required=True)
    p.add_argument("--reviewer",required=True)
    a=p.parse_args()
    if a.issue<=0 or len(a.reason.strip())<8:
        p.error("Valid issue number and a specific reason (8+ chars) required")
    issue=api(f"issues/{a.issue}")
    if issue.get("pull_request") or "[TEST ONLY]" in issue.get("title",""):
        p.error("Test or pull-request items cannot be dismissed as race findings")
    history=json.loads(HISTORY.read_text(encoding="utf-8"))
    matches=[e for e in history["events"] if e.get("issueNumber")==a.issue]
    if len(matches)!=1 or matches[0].get("status")!="needs_review":
        p.error("Issue is not linked to exactly one pending monitored change")
    item=matches[0]
    # Record decision in repository data before closing issue.
    item["status"]="dismissed"
    item["reviewedBy"]=a.reviewer
    item["reviewReason"]=a.reason.strip()
    from datetime import datetime,timezone
    item["reviewedAt"]=datetime.now(timezone.utc).isoformat(timespec="seconds")
    HISTORY.write_text(json.dumps(history,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("Dismissal recorded; workflow will close issue after committing history")

if __name__=="__main__":
    main()
