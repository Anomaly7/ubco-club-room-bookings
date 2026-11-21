import re, sys, html, urllib.parse, urllib.request, http.cookiejar
BASE = "https://sws-oka.as.it.ubc.ca/sws_2026/"
jar = http.cookiejar.CookieJar()
op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
op.addheaders = [("User-Agent", "Mozilla/5.0 (UBCO student; room-usage research)")]
def get(url, data=None):
    r = op.open(url, urllib.parse.urlencode(data, doseq=True).encode() if data else None, timeout=240)
    return r.geturl(), r.read().decode("utf-8", "replace")
def fields(page):
    out = {}
    for m in re.finditer(r'<input[^>]+type="hidden"[^>]*>', page):
        n = re.search(r'name="([^"]+)"', m.group(0)); v = re.search(r'value="([^"]*)"', m.group(0))
        if n: out[n.group(1)] = html.unescape(v.group(1)) if v else ""
    return out
def options(page, sel):
    block = re.search(r'<select[^>]+id="%s".*?</select>' % sel, page, re.S).group(0)
    return [(html.unescape(v), html.unescape(t).strip()) for v, t in re.findall(r'<option[^>]*value="([^"]*)"[^>]*>(.*?)</option>', block, re.S)]
def rooms_page():
    _, p = get(BASE)
    f = fields(p); f["__EVENTTARGET"] = "LinkBtn_locationByZone"; f["__EVENTARGUMENT"] = ""
    return get(BASE, f)[1]
def report(page, room_values, week_values, days="1-7", period=None, rtype=None):
    f = fields(page)
    per = period or options(page, "dlPeriod")[3][0]
    typ = rtype or options(page, "dlType")[2][0]
    f.update({"dlObject": room_values, "lbWeeks": week_values, "lbDays": days, "dlPeriod": per, "dlType": typ, "bGetTimetable": "View Timetable"})
    return get(BASE, f)
if __name__ == "__main__":
    p = rooms_page()
    rooms = options(p, "dlObject"); weeks = options(p, "lbWeeks"); days = options(p, "lbDays")
    print(len(rooms), "rooms; weeks e.g.", weeks[:3], "days", days[:2])
    url, out = report(p, [rooms[1][0]], [weeks[1][0]], days[0][0])
    print("REPORT URL:", url[:150]); open("sample.html", "w", encoding="utf-8").write(out); print(len(out))

def fetch_report(page, room_values, week_values, days="1-7"):
    report(page, room_values, week_values, days)
    return get(BASE + "showtimetable.aspx")[1]
