"""Archive official NBA injury report PDFs verbatim, with revisions.

The NBA publishes an injury report roughly hourly as a PDF whose filename carries
its nominal report time. Files for past dates remain retrievable, so most of the
project's modelling window can be archived now rather than only captured forward.

This script STORES ONLY. It does not parse, interpret or derive features, so the
archive stays a faithful record that later parsing can be re-run against.

Two timestamps are recorded per file and they are not the same thing: the
filename hour is the NBA's nominal report slot, and retrieved_at is when we
fetched it. Neither is a verified publication timestamp, and a file fetched today
for a game in 2023 proves nothing about what was visible before that game. Only
reports captured prospectively support an availability-at-cutoff claim; archived
ones support research. The manifest records which mode each file came from.
"""
import argparse
import hashlib
import json
import time
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError
from datetime import datetime, timezone, date, timedelta

BASE = "https://ak-static.cms.nba.com/referee/injury/Injury-Report_{date}_{hour}.pdf"
# Slots that matter most: the day-before 5pm deadline, the game-day window, and
# the late-afternoon revisions closest to a T-60 cutoff.
DEFAULT_HOURS = ("11AM", "01PM", "05PM", "06PM", "07PM", "08PM")
ARCHIVE_NOTE = ("Retrieved after the fact; supports research only. An archived report "
                "does not establish what was visible before a past game.")


def fetch(url, timeout=30):
    try:
        with urlopen(Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=timeout) as response:
            return response.status, response.read()
    except HTTPError as exc:
        return exc.code, b""
    except URLError:
        return 0, b""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", required=True, help="First date, YYYY-MM-DD")
    parser.add_argument("--end", required=True, help="Last date inclusive, YYYY-MM-DD")
    parser.add_argument("--out", required=True, help="Archive directory; reused across runs")
    parser.add_argument("--hours", default=",".join(DEFAULT_HOURS))
    parser.add_argument("--max-files", type=int, default=200, help="Stop after this many new files")
    parser.add_argument("--sleep", type=float, default=1.0, help="Seconds between requests")
    parser.add_argument("--prospective", action="store_true",
                        help="Mark files as captured close to their report time, not backfilled")
    a = parser.parse_args()
    out = Path(a.out)
    (out/"pdf").mkdir(parents=True, exist_ok=True)
    index_path = out/"index.jsonl"
    seen = set()
    if index_path.exists():
        for line in index_path.read_text().splitlines():
            if line.strip():
                seen.add(json.loads(line)["filename"])
    hours = [h.strip() for h in a.hours.split(",") if h.strip()]
    start = date.fromisoformat(a.start)
    end = date.fromisoformat(a.end)
    if end < start:
        raise SystemExit("--end must not precede --start")
    if a.max_files <= 0:
        raise SystemExit("--max-files must be positive")
    downloaded = missing = skipped = 0
    day = start
    with index_path.open("a") as index:
        while day <= end and downloaded < a.max_files:
            for hour in hours:
                if downloaded >= a.max_files:
                    break
                stamp = day.isoformat()
                filename = f"Injury-Report_{stamp}_{hour}.pdf"
                if filename in seen:
                    skipped += 1
                    continue
                url = BASE.format(date=stamp, hour=hour)
                status, body = fetch(url)
                time.sleep(a.sleep)
                if status != 200 or not body.startswith(b"%PDF"):
                    missing += 1
                    continue
                (out/"pdf"/filename).write_bytes(body)
                index.write(json.dumps({
                    "filename": filename, "url": url, "report_date": stamp, "report_hour": hour,
                    "retrieved_at": datetime.now(timezone.utc).isoformat(),
                    "bytes": len(body), "sha256": hashlib.sha256(body).hexdigest(),
                    "capture": "prospective" if a.prospective else "backfill",
                    "note": None if a.prospective else ARCHIVE_NOTE})+"\n")
                index.flush()
                downloaded += 1
            day += timedelta(days=1)
    print(json.dumps({"archive": str(out), "downloaded": downloaded, "already_held": skipped,
                      "absent_or_failed": missing, "last_date_attempted": day.isoformat(),
                      "note": "Rerun with a later --start to continue; existing files are never refetched."},
                     indent=2))


if __name__ == "__main__":
    main()
