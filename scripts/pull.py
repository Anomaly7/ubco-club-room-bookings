"""Reads every room's bookings from the UBCO public timetable into all_rows.csv.

Default: ONE combined report for all rooms (3 requests in total), so frequent refreshes stay light on UBC's server.
--per-room: the old way, one room at a time with a pause (about 400 requests); only a fallback.
"""
import csv
import html
import re
import sys
import time

sys.path.insert(0, ".")
import sws  # noqa: E402

COLS = ["Name", "Section ID", "Type", "Name of Department", "Weeks", "Location", "Staff", "Module", "Day",
        "Start Time", "End Time"]


def rows_of(report):
    out = []
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", report, re.S):
        cells = [html.unescape(re.sub(r"<[^>]+>", "", c)).replace("\xa0", " ").strip()
                 for c in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)]
        if len(cells) == 11 and cells[0] != "Name":
            out.append(dict(zip(COLS, cells)))
    return out


def unique(rows):
    seen, out = set(), []
    for r in rows:
        k = tuple(r[c] for c in COLS)
        if k not in seen:
            seen.add(k)
            out.append(r)
    return out


def combined():
    p = sws.rooms_page()
    rooms = [v for v, _ in sws.options(p, "dlObject")]
    return unique(rows_of(sws.fetch_report(p, rooms, ["1-53"])))


def per_room():
    p = sws.rooms_page()
    allrows = []
    for i, (val, label) in enumerate(sws.options(p, "dlObject")):
        for _ in range(3):
            try:
                rep = sws.fetch_report(sws.rooms_page(), [val], ["1-53"])
                break
            except Exception:
                time.sleep(5)
        else:
            print("FAILED", label)
            continue
        allrows += rows_of(rep)
        print(i + 1, label, flush=True)
        time.sleep(1)
    return unique(allrows)


def main():
    rows = per_room() if "--per-room" in sys.argv else combined()
    with open("all_rows.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, COLS)
        w.writeheader()
        w.writerows(rows)
    print("TOTAL", len(rows))


if __name__ == "__main__":
    main()
