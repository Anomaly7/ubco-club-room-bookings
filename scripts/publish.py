"""Run the refresh on this PC and publish the data to GitHub (Sam, 2026-11-21).

UBC's timetable sits behind "UBC VPNLess Access" for connections from outside its approved networks, so GitHub's cloud
runners can't read it. This PC can, so a Windows scheduled task runs this every 10 minutes:
  - a quick refresh (all rooms, this week + next 5, one request);
  - a full-year refresh instead when the last one was over 20 hours ago;
  - commits data/ and pushes to GitHub only if a booking changed.
"""
import os
import subprocess
NOWIN = getattr(subprocess, "CREATE_NO_WINDOW", 0)  # no console flash on Windows
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
STAMP = os.path.join(REPO, "data", ".last_full")


def git(*args):
    return subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True, creationflags=NOWIN)


def main():
    full = not os.path.exists(STAMP) or time.time() - os.path.getmtime(STAMP) > 20 * 3600
    git("pull", "--rebase", "--autostash", "-q")
    res = subprocess.run([sys.executable, os.path.join(HERE, "refresh.py")] + (["--full"] if full else []), cwd=HERE, creationflags=NOWIN)
    if res.returncode != 0:
        return res.returncode
    if full:
        with open(STAMP, "w") as f:
            f.write(str(int(time.time())))
    git("add", "data")
    if git("diff", "--cached", "--quiet").returncode == 0:
        return 0  # nothing changed
    stamp = time.strftime("%Y-%m-%d %H:%M")
    git("commit", "-q", "-m", f"Bookings update {stamp} Pacific")
    out = git("push", "-q")
    if out.returncode != 0:
        print("push failed:", out.stderr[-300:])
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
