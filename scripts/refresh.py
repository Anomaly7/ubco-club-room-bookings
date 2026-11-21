"""Refresh the SUO club room-booking dataset from the UBCO public timetable.

  python refresh.py          quick check: all rooms, this week + the next 5 (one request, every 10 minutes)
  python refresh.py --full   whole year, in 6-week chunks (once a day)

Only event bookings ("WRB" rows) are kept, in data/event_rows.csv. Merge rule for each window pulled: the timetable returns
every booking that has a date in that window, so a stored booking with a date in the window that didn't come back was
changed or cancelled and is dropped; everything returned replaces what was there; bookings outside the window are kept.
Then build.py rebuilds the CSVs and summary, and new / removed upcoming club bookings are appended to data/changes.md.
If UBC's site fails or returns something implausible, nothing is written (the last good data stays).
"""
import csv
import datetime as dt
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)
sys.path.insert(0, HERE)
import pull  # noqa: E402
import sws  # noqa: E402

DATA = os.path.join(os.path.dirname(HERE), "data")
STORE = os.path.join(DATA, "event_rows.csv")
CLUBS = os.path.join(DATA, "suo_club_room_bookings_2026W.csv")
WEEK1 = dt.date(2026, 8, 24)  # timetable week 1 (Monday)
LAST_WEEK = 53
COLS = pull.COLS
PACIFIC = dt.timezone(dt.timedelta(hours=-7), "Pacific")  # BC is on permanent daylight time (UTC-7)


def today():
    return dt.datetime.now(PACIFIC).date()


def log(msg):
    line = f"{dt.datetime.now(PACIFIC):%Y-%m-%d %H:%M} {msg}"
    print(line)
    with open(os.path.join(DATA, "refresh.log"), "a", encoding="utf-8") as f:
        f.write(line + "\n")


def weeks_of(spec):
    out = set()
    for part in spec.split(","):
        part = part.strip()
        if part:
            a, _, b = part.partition("-")
            out.update(range(int(a), int(b or a) + 1))
    return out


def load_store():
    if not os.path.exists(STORE):
        return []
    with open(STORE, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def fetch(week_numbers):
    """All rooms, the given week numbers, one combined report. Event (WRB) rows only."""
    page = sws.rooms_page()
    rooms = [v for v, _ in sws.options(page, "dlObject")]
    values = {lab.split(" w/c")[0].replace("Week ", "").strip(): v for v, lab in sws.options(page, "lbWeeks")
              if lab.startswith("Week ")}
    wanted = [values[str(w)] for w in week_numbers if str(w) in values]
    rows = pull.unique(pull.rows_of(sws.fetch_report(page, rooms, wanted)))
    return [r for r in rows if r["Type"].startswith("WRB")], len(rows)


def merge(store, fresh, window):
    window = set(window)
    keep = [r for r in store if not (weeks_of(r["Weeks"]) & window)]
    return pull.unique(keep + fresh)


def club_keys():
    if not os.path.exists(CLUBS):
        return {}
    with open(CLUBS, encoding="utf-8") as f:
        return {(r["date"], r["start"], r["end"], r["room"], r["event"]): r for r in csv.DictReader(f)}


def main():
    full = "--full" in sys.argv
    now_week = max(1, (today() - WEEK1).days // 7 + 1)
    if full:
        windows = [list(range(w, min(w + 6, LAST_WEEK + 1))) for w in range(1, LAST_WEEK + 1, 6)]
    else:
        windows = [list(range(now_week, min(now_week + 6, LAST_WEEK + 1)))]
    store = load_store()
    for window in windows:
        try:
            fresh, total = fetch(window)
        except Exception as e:  # site down, timeout, page changed
            log(f"Pull FAILED for weeks {window[0]}-{window[-1]} ({type(e).__name__}: {str(e)[:200]}); kept the previous data.")
            try:  # what the timetable actually answered, for the run log
                url, page = sws.get(sws.BASE)
                import re as _re
                title = _re.search(r"<title>(.*?)</title>", page, _re.S | _re.I)
                print("Timetable answered:", url, "| title:", title.group(1).strip() if title else "-", "|", len(page), "bytes")
            except Exception as e2:
                print("Timetable unreachable:", type(e2).__name__, str(e2)[:200])
            return 1
        before_in_window = sum(1 for r in store if weeks_of(r["Weeks"]) & set(window))
        # A class-filled window with no events, or losing most events at once, means a bad read, not real cancellations.
        if (total and not fresh and before_in_window > 20) or (before_in_window > 40 and len(fresh) < before_in_window * 0.4):
            log(f"Suspicious result for weeks {window[0]}-{window[-1]} ({len(fresh)} events, had {before_in_window}); "
                "kept the previous data.")
            return 1
        store = merge(store, fresh, window)

    with open(STORE, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, COLS)
        w.writeheader()
        w.writerows(store)

    before = club_keys()
    with open("all_rows.csv", "w", newline="", encoding="utf-8") as f:  # build.py reads this
        w = csv.DictWriter(f, COLS)
        w.writeheader()
        w.writerows(store)
    res = subprocess.run([sys.executable, "build.py", DATA], capture_output=True, text=True)
    os.remove("all_rows.csv")
    if res.returncode != 0:
        log("Build FAILED: " + res.stderr[-300:].replace("\n", " "))
        return 1
    after = club_keys()

    t = today().isoformat()
    added = [after[k] for k in sorted(set(after) - set(before)) if k[0] >= t]
    removed = [before[k] for k in sorted(set(before) - set(after)) if k[0] >= t]
    if before and (added or removed):
        stamp = dt.datetime.now(PACIFIC).strftime("%Y-%m-%d %H:%M")
        with open(os.path.join(DATA, "changes.md"), "a", encoding="utf-8") as f:
            f.write(f"\n## {stamp} (Pacific)\n\n")
            for r in added:
                f.write(f"- **Added:** {r['club']}: {r['event']}, {r['date']} {r['start']}-{r['end']}, {r['room']}\n")
            for r in removed:
                f.write(f"- **Removed:** {r['club']}: {r['event']}, {r['date']} {r['start']}-{r['end']}, {r['room']}\n")
    log(f"OK ({'full' if full else 'quick'}): {len(store)} event bookings, {len(after)} club booking dates "
        f"({len(added)} new, {len(removed)} removed upcoming).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
