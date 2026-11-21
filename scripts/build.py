import csv, re, datetime as dt, collections, os, sys

OUT = sys.argv[1]
clubs = [l.strip() for l in open(os.path.join(OUT, "suo_clubs_2026-11-21.txt"), encoding="utf-8") if l.strip()]

# Club codes seen at the start of booking titles -> SUO club (checked against the SUO directory, 2026-11-21).
ALIAS = {
    "GC": "Games Club Okanagan", "SBT": "Steel Bridge Team", "JDCW": "JDC West Okanagan", "MR": "Marine Robotics",
    "PCU": "Psychology Course Union", "CCU": "Chemistry Course Union (CCU)", "OES": "Engineering Society",
    "EngSoc": "Engineering Society", "QSCU": "Quantitative Sciences Course Union", "P2C": "Power to Change",
    "Aerospace": "Aerospace Club", "RoverCraft": "Okanagan Rover Craft", "ORC": "Okanagan Rover Craft",
    "Anime": "Okanagan Anime Club", "HKSC": "Hong Kong Student Club", "BSA": "Black Student Association",
    "CSCU": "Computer Science Course Union of the SUO", "EZCU": "Ecology & Zoology Course Union (EZCU)",
    "MCU": "Microbiology Course Union", "UDC": "Unite Dance Club", "UCM": "University Christian Ministries (UCM)",
    "WIE": "Women in Engineering", "Spark": "Spark Student Association", "SPARK": "Spark Student Association",
    "PDC": "Pre-Dental Club", "NCU": "Nursing Course Union", "Esports": "Okanagan Esports Association",
    "EIA": "Engineers in Action, Okanagan Chapter", "BCCU": "Biochemistry Course Union",
    "BMSCU": "Bachelor of Media Studies Course Union", "AnCU": "Anthropology Course Union", "ANCU": "Anthropology Course Union",
    "BSCU": "Biological Sciences Course Union", "CRobotics": "Combat Robotics Club", "FSA": "Filipino Student Association",
    "GCU": "Geography Course Union", "Giddah": "Giddha Club", "Giddha": "Giddha Club", "GNCTR": "Concrete Toboggan Club (GNCTR)",
    "KMR": "Kelowna Mountain Riders", "PPE": "Philosophy, Political Science, Economics Course Union", "AgeLink": "Age-Link Club",
    "AIClub": "Artificial Intelligence Club", "AIC": "Artificial Intelligence Club", "ChessClub": "Okanagan Chess Club",
    "Karaoke": "Karaoke Club", "ECU": "English Course Union", "PLS": "Pre-Law Society", "CSA": "Commerce Student Association",
    "ISA": "Indian Student Association", "TWS": "The Wildlife Society Okanagan Student Chapter",
    "MES": "Medical Exploration Society", "HEAT": "HEAT Robotics", "Games": "Games Club Okanagan", "RCraft": "Okanagan Rover Craft", "ComR": "Combat Robotics Club", "CSCE/WSP": "CSCE Okanagan Student Chapter",
}
AMBIGUOUS = {
    "MSA": "Muslim Student Association or Malaysian Student Association in Kelowna",
    "SCU": "Sociology Course Union or Sustainability Course Union",
    "ASA": "Asian Student Association of SUO or Arab Student Club",
    "ACU": "Anthropology Course Union (probably)",
}
TITLE_HINT = [(re.compile(p, re.I), c) for p, c in [
    (r"\bEESC course union\b|\bEESC Student", "Earth & Environmental Science Course Union"),
    (r"\bchess\b", "Okanagan Chess Club"), (r"\bkaraoke\b", "Karaoke Club"), (r"\bGames? Night\b", "Games Club Okanagan"),
    (r"\bTheatre Club\b", "Theatre Club"), (r"\bMath Club\b", "SUO Math Club"), (r"\bCoding Club\b", "Coding Club"),
    (r"\bBook Club\b", "English Course Union"),
]]
UNIVERSITY = re.compile(
    r"^\^?Exam|^DRC\b|^University Closed|^SEO\b|^STEM\b|^Stem\b|^SoE\b|^SOE\b|Faculty Council|^FASS\b|^FoS\b|^FCCS\b|"
    r"^RA Training|^Campus|^UBCO Campus|^AV\b|^Projector|^Scheduling|^CL-Placeholder|^OAA\b|^Midterm|^EAP_O|^Medical Intake|"
    r"^Athletics|^Rec\b|^Ambassador|^Department|^Co-op|^Career|^SL\b|^SLH\b|^SPEXM|^DEXM|^OOTEXM|^EXM\b|^PRJ\d|^WWEST|"
    r"^[A-Z]{2,5}_O|^[A-Z]{3,4}\s?\d{3}|^Riley|^MEETING/SEL|^TRAINING/SEL|^Marking|^WVB\b|^AARA|^Workshop|^Seminar|^ECON|^BIOL|^Biology Dept|^PSYO|^EESC meeting|^GEESC|^HES|^School of|^Admin|^Maintenance|^AAA|^CMO\d|^CCS_|^URA|^CEP|^Electrical Program|^Trainer Workshop|^CanaDAM|^PanCanCompChem|^PlantBreeding|^ISW")
WEEK1 = dt.date(2026, 8, 24)
DAYS = {"Mon": 0, "Tue": 1, "Wed": 2, "Thu": 3, "Fri": 4, "Sat": 5, "Sun": 6}
BUILDINGS = {"ART": "Arts Building", "ASC": "Arts & Sciences Centre", "CCS": "Creative & Critical Studies", "COM": "Commons",
             "EDL": "Engineering Development Lab", "EME": "Engineering, Management & Education", "FIP": "Fipke Centre",
             "LIB": "Library", "SCI": "Science Building", "ADM": "Administration Building", "UNC": "University Centre"}
DATEPART = re.compile(
    r"\s+(\d{2}-[A-Z][a-z]{2}-\d{4}|(?:(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)[a-z]*,?\s*)+\(week\(s\):.*?\)|"
    r"(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday).*?\(week\(s\):.*?\))\s+\d{1,2}:\d{2}\s*-.*$")


def weeks(spec):
    out = []
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        a, _, b = part.partition("-")
        out += range(int(a), int(b or a) + 1)
    return out


def classify(title):
    tok = title.split()[0] if title.split() else ""
    if tok in ALIAS:
        return "SUO club or course union", ALIAS[tok], "club code " + tok, "high"
    if tok in AMBIGUOUS:
        return "SUO club or course union", AMBIGUOUS[tok], "club code " + tok + " (ambiguous)", "medium"
    low = title.lower()
    for c in clubs:
        core = re.sub(r"\s*\(.*?\)|\bSUO\b|\bOkanagan\b|@|\bat UBC\b", "", c).strip().lower()
        if len(core) > 6 and core in low:
            return "SUO club or course union", c, "club name in title", "high"
    for rx, c in TITLE_HINT:
        if rx.search(title):
            return "SUO club or course union", c, "keyword in title", "medium"
    if UNIVERSITY.match(title):
        return "University (exams, classes, departments, admin)", "", "title pattern", "high"
    return "Unclassified", "", "", ""


rows = [r for r in csv.DictReader(open("all_rows.csv", encoding="utf-8")) if r["Type"].startswith("WRB")]
occ, seen = [], set()
for r in rows:
    m = DATEPART.search(r["Name"])
    title = (r["Name"][:m.start()] if m else r["Name"]).strip()
    cat, club, basis, conf = classify(title)
    if r["Type"] == "WRB-CANCELLED":
        cat = "Cancelled"
    room = r["Location"]
    bcode = room.split()[0] if room else ""
    for w in weeks(r["Weeks"]):
        for d in [x.strip() for x in r["Day"].split(",") if x.strip() in DAYS]:
            day = WEEK1 + dt.timedelta(weeks=w - 1, days=DAYS[d])
            key = (title, day, r["Start Time"], r["End Time"], room)
            if key in seen:
                continue
            seen.add(key)
            occ.append({"date": day.isoformat(), "weekday": d, "start": r["Start Time"].zfill(5), "end": r["End Time"].zfill(5),
                        "room": room, "building": BUILDINGS.get(bcode, bcode), "event": title, "category": cat, "club": club,
                        "match_basis": basis, "confidence": conf, "sws_week": w, "booking_status": r["Type"],
                        "raw_booking_name": r["Name"]})
occ.sort(key=lambda o: (o["date"], o["start"], o["room"]))
cols = list(occ[0].keys())


def write(name, data):
    with open(os.path.join(OUT, name), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, cols)
        w.writeheader()
        w.writerows(data)


clubocc = [o for o in occ if o["category"] == "SUO club or course union"]
write("all_room_event_bookings_2026W.csv", occ)
write("suo_club_room_bookings_2026W.csv", clubocc)

cats = collections.Counter(o["category"] for o in occ)
byclub = collections.Counter(o["club"] for o in clubocc)
byroom = collections.Counter(o["room"] for o in clubocc)
byday = collections.Counter(o["weekday"] for o in clubocc)
byhour = collections.Counter(o["start"][:2] for o in clubocc)
bymonth = collections.Counter(o["date"][:7] for o in clubocc)
uncl = collections.Counter(o["event"] for o in occ if o["category"] == "Unclassified")
order = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
with open(os.path.join(OUT, "summary.md"), "w", encoding="utf-8") as f:
    f.write("# UBCO room bookings by SUO clubs, 2026 Winter (pulled 2026-11-21)\n\n")
    f.write("Source: UBCO public online timetable (https://sws-oka.as.it.ubc.ca/sws_2026/), all 102 rooms it lists, "
            "weeks 1-53 (2026-08-24 to 2027-08-29). Classes are left out; only event bookings (\"WRB\" web room bookings).\n\n")
    f.write("## Booking occurrences by category\n\n" + "\n".join(f"- {k}: {v}" for k, v in cats.most_common()) + "\n\n")
    f.write(f"## SUO clubs and course unions ({len(byclub)} clubs, {len(clubocc)} room bookings)\n\n| Club | Bookings |\n|---|---|\n")
    f.write("\n".join(f"| {k} | {v} |" for k, v in byclub.most_common()) + "\n\n")
    f.write("## Rooms clubs use most\n\n| Room | Bookings |\n|---|---|\n")
    f.write("\n".join(f"| {k} | {v} |" for k, v in byroom.most_common(20)) + "\n\n")
    f.write("## By weekday\n\n" + " · ".join(f"{d} {byday[d]}" for d in order) + "\n\n")
    f.write("## By start hour\n\n" + " · ".join(f"{h}:00 {n}" for h, n in sorted(byhour.items())) + "\n\n")
    f.write("## By month\n\n" + " · ".join(f"{m} {n}" for m, n in sorted(bymonth.items())) + "\n\n")
    f.write("## Unclassified booking titles (most common 60; some may be clubs with unfamiliar codes)\n\n")
    f.write("\n".join(f"- {k} ({v})" for k, v in uncl.most_common(60)) + "\n")
print(cats.most_common())
print(len(byclub), "clubs,", len(clubocc), "club bookings")
print(byclub.most_common(15))
print("unclassified top:", [k for k, _ in uncl.most_common(50)])
