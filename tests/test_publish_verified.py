#!/usr/bin/env python3
"""Isolated publisher smoke tests. All writes go to a temporary directory."""
import contextlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from importlib.util import spec_from_file_location, module_from_spec

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "publish_verified.py"
spec = spec_from_file_location("publish_verified", SCRIPT)
publisher = module_from_spec(spec)
spec.loader.exec_module(publisher)

class FakeResponse:
    def __init__(self, issue):
        self.issue = issue
    def __enter__(self):
        return io.BytesIO(json.dumps(self.issue).encode())
    def __exit__(self, *args):
        return False

class PublishTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        (root / "data").mkdir()
        (root / "data/race-monitor.json").write_text(json.dumps({"events":[{"id":"utmb","name":"UTMB Mont-Blanc","officialUrl":"https://montblanc.utmb.world/"}]}))
        (root / "data/monitor-history.json").write_text(json.dumps({"events":[{"raceId":"utmb","issueNumber":42,"status":"needs_review"}]}))
        (root / "data/verified-updates.json").write_text('{"updates":[]}')
        self.root = root
        self.old = publisher.RACES, publisher.OUT, publisher.ROOT
        publisher.ROOT = root
        publisher.RACES = root / "data/race-monitor.json"
        publisher.OUT = root / "data/verified-updates.json"

    def tearDown(self):
        publisher.RACES, publisher.OUT, publisher.ROOT = self.old
        self.tmp.cleanup()

    def run_publish(self, source="https://montblanc.utmb.world/races/utmb", issue=42, category="lottery", title="[REVIEWED] Official lottery schedule"):
        args = ["publish_verified.py","--race","utmb","--headline",title,"--source",source,"--race-year","2027","--distance","UTMB","--category",category,"--review-issue",str(issue),"--verified-by","test-reviewer","--evidence","Official race announcement confirms the lottery schedule for 2027.","--confirm-reviewed","YES"]
        with patch.object(sys,"argv",args), patch.dict(os.environ,{"GITHUB_TOKEN":"fake-token","GITHUB_REPOSITORY":"example/trailrace-app"}), patch.object(publisher,"urlopen",return_value=FakeResponse({"state":"open","title":title,"html_url":"https://github.com/example/trailrace-app/issues/42"})), contextlib.redirect_stdout(io.StringIO()):
            publisher.main()

    def test_publish_and_prevent_duplicate(self):
        self.run_publish()
        records=json.loads(publisher.OUT.read_text())["updates"]
        self.assertEqual(len(records),1)
        self.assertEqual(records[0]["category"],"lottery")
        self.assertEqual(records[0]["status"],"manually_verified")
        with self.assertRaises(SystemExit):
            self.run_publish()
        self.assertEqual(len(json.loads(publisher.OUT.read_text())["updates"]),1)

    def test_reject_unofficial_source(self):
        with self.assertRaises(SystemExit):
            self.run_publish(source="https://example.org/not-an-official-announcement")
        self.assertEqual(json.loads(publisher.OUT.read_text())["updates"],[])

    def test_reject_unmatched_issue(self):
        with self.assertRaises(SystemExit):
            self.run_publish(issue=99)
        self.assertEqual(json.loads(publisher.OUT.read_text())["updates"],[])

    def test_reject_test_issue(self):
        with self.assertRaises(SystemExit):
            self.run_publish(title="[TEST ONLY] Simulated alert")
        self.assertEqual(json.loads(publisher.OUT.read_text())["updates"],[])

if __name__ == "__main__":
    unittest.main()
