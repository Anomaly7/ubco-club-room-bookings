# UBCO club room bookings

A dataset of the UBC Okanagan classrooms and labs booked for **Students' Union Okanagan (SUO) clubs and course unions**,
refreshed automatically every 10 minutes.

## Where the data comes from

Clubs request rooms through SUO's event booking process, and the classroom bookings are entered in UBC's room-booking
system. They appear on UBCO's public online timetable (https://sws-oka.as.it.ubc.ca/sws_2026/) as event ("WRB") bookings,
named with the club's code, e.g. `GC GamesNight` (Games Club) or `P2C Community Build` (Power to Change).
The timetable does not say who booked a room, so the club is matched from that code (see `ALIAS` in `scripts/build.py`)
against SUO's club directory (`data/suo_clubs_2026-11-21.txt`).

Not included (not public): SUO's tabling spaces (COM 101, UNC 100/100A), the UNC Ballroom and foyers (Outlook calendars),
and Library study rooms (LibCal).

## Files (`data/`)

| File | What it is |
|---|---|
| `suo_club_room_bookings_2026W.csv` | One row per club booking date: date, weekday, start, end, room, building, event, club, how the club was matched, confidence |
| `all_room_event_bookings_2026W.csv` | Every non-class booking (clubs, exams, university events, unclassified) |
| `summary.md` | Counts by club, room, weekday, start hour and month |
| `changes.md` | Upcoming club bookings that were added or removed, with the time they were noticed |
| `event_rows.csv` | The raw event bookings as the timetable lists them |

## How it updates

A GitHub Actions job (`.github/workflows/refresh.yml`):
- every 10 minutes asks the timetable for all rooms for this week and the next five, in **one** request;
- once a day refreshes the whole year in 6-week chunks.

If the timetable is down or returns something implausible, nothing is changed. Classes are never stored.
Run it yourself with `python scripts/refresh.py` (or `--full`).

Unclassified bookings that are probably clubs with unfamiliar codes are listed at the end of `summary.md`;
add the code to `ALIAS` in `scripts/build.py` to include them.
