import os
import json
import ssl
from datetime import datetime, date, timedelta
from urllib.request import urlopen, Request
from urllib.parse import urlencode
from flask import Flask, render_template_string, request

app = Flask(__name__)

ALL_WEEKDAYS = {
    0: "Montag",
    1: "Dienstag",
    2: "Mittwoch",
    3: "Donnerstag",
    4: "Freitag",
    5: "Samstag",
    6: "Sonntag",
}

DISPLAY_WEEKDAYS = [2, 3, 4, 5, 6]  # Mi–So
PIXELS_PER_MINUTE = 2


def heat_color(p):
    if p >= 90: return "#b00000"
    if p >= 70: return "#d9480f"
    if p >= 50: return "#f49300"
    if p >= 30: return "#ffd43b"
    return "#fff4cc"


def minutes_from_iso(ts):
    dt = datetime.fromisoformat(ts)
    return dt.hour * 60 + dt.minute


def fetch_sessions():
    params = {
        "page": 1,
        "perPage": 2000,
        "skipTotal": 1,
        "sort": "event_date,start",
        "filter": "is_deleted=false && source='coremanager' && source_category_id=4",
        "fields": "event_date,start,end,title,participants_count,max_participants",
    }
    url = "https://oana.asdf.ooo/api/collections/sessions/records?" + urlencode(params)
    req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    ctx = ssl.create_default_context()
    with urlopen(req, timeout=30, context=ctx) as r:
        return json.loads(r.read().decode()).get("items", [])


def week_bounds(ref):
    wd = ref.weekday()
    start = ref - timedelta(days=(wd - 2) % 7)
    end = start + timedelta(days=4)
    return start, end


# ---------- SHARED CALENDAR BUILDER ----------
def build_calendar(dayslots):
    calendar = []
    for key in sorted(dayslots):
        day = dayslots[key]
        base = min(day["times"])
        top = max(day["times"])
        height = (top - base) * PIXELS_PER_MINUTE

        calendar.append({
            "label": day["label"],
            "height": height,
            "slots": [{
                "label": f"{m//60:02d}:{m%60:02d}",
                "top": (m - base) * PIXELS_PER_MINUTE
            } for m in sorted(day["times"])],
            "sessions": [{
                "top": (s["start"] - base) * PIXELS_PER_MINUTE,
                "height": (s["end"] - s["start"]) * PIXELS_PER_MINUTE,
                "text": s["text"],
                "color": s["color"],
            } for s in day["sessions"]],
        })
    return calendar


# ---------- WEEK VIEW ----------
def build_week_view(offset):
    ws, we = week_bounds(date.today() + timedelta(weeks=offset))
    days = {}

    for s in fetch_sessions():
        d = datetime.strptime(s["event_date"], "%Y-%m-%d").date()
        if not (ws <= d <= we): continue
        if d.weekday() not in DISPLAY_WEEKDAYS: continue

        sm = minutes_from_iso(s["start"])
        em = minutes_from_iso(s["end"])
        if em <= sm: continue

        used = int(s["participants_count"] or 0)
        maxp = int(s["max_participants"] or 0)
        pct = int((used / maxp) * 100) if maxp else 0

        key = d.isoformat()
        if key not in days:
            days[key] = {
                "label": f"{ALL_WEEKDAYS[d.weekday()]} {d.strftime('%d.%m')}",
                "times": set(),
                "sessions": [],
            }

        days[key]["times"].update([sm, em])
        days[key]["sessions"].append({
            "start": sm,
            "end": em,
            "text": f"{s['title']}\n{used}/{maxp} ({pct}%)",
            "color": heat_color(pct),
        })

    return build_calendar(days), ws, we


# ---------- MONTH AVERAGE VIEW ----------
def build_month_view(year, month):
    slots = {}

    for s in fetch_sessions():
        d = datetime.strptime(s["event_date"], "%Y-%m-%d").date()
        if d.year != year or d.month != month: continue
        if d.weekday() not in DISPLAY_WEEKDAYS: continue

        sm = minutes_from_iso(s["start"])
        em = minutes_from_iso(s["end"])
        used = int(s["participants_count"] or 0)
        maxp = int(s["max_participants"] or 0)
        if maxp == 0: continue

        pct = (used / maxp) * 100
        key = (d.weekday(), sm, em, s["title"])

        slots.setdefault(key, {
            "weekday": d.weekday(),
            "start": sm,
            "end": em,
            "title": s["title"],
            "values": []
        })["values"].append(pct)

    days = {}
    for slot in slots.values():
        avg = int(sum(slot["values"]) / len(slot["values"]))
        wd = slot["weekday"]
        fake_date = date(2026, 1, 5 + wd)  # stable weekday only
        key = fake_date.isoformat()

        days.setdefault(key, {
            "label": ALL_WEEKDAYS[wd],
            "times": set(),
            "sessions": [],
        })

        days[key]["times"].update([slot["start"], slot["end"]])
        days[key]["sessions"].append({
            "start": slot["start"],
            "end": slot["end"],
            "text": f"{slot['title']}\nØ {avg}%",
            "color": heat_color(avg),
        })

    return build_calendar(days)


HTML = """
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>Auslastung</title>
<style>
body{font-family:Arial;}
.nav{margin-bottom:12px;}
.days{display:flex;gap:24px;}
.day{min-width:320px;padding-left:60px;border-left:1px solid #ccc;position:relative;}
.time{position:absolute;left:-55px;font-size:11px;}
.session{position:absolute;left:0;right:10px;padding:8px;border-radius:4px;}
</style>
</head>
<body>

<h2>{{ title }}</h2>

<div class="nav">
<a href="/?view=week&week_offset={{ week_offset - 1 }}">◀ Vorige Woche</a> |
<a href="/?view=week&week_offset={{ week_offset + 1 }}">Nächste Woche ▶</a> |
<a href="/?view=month">Monat (Ø)</a>
</div>

<div class="days">
{% for d in calendar %}
<div class="day">
<b>{{ d.label }}</b>
<div style="height:{{ d.height }}px;position:relative;">
{% for t in d.slots %}<div class="time" style="top:{{t.top}}px">{{t.label}}</div>{% endfor %}
{% for s in d.sessions %}
<div class="session" style="top:{{s.top}}px;height:{{s.height}}px;background:{{s.color}}">{{s.text}}</div>
{% endfor %}
</div>
</div>
{% endfor %}
</div>

</body>
</html>
"""


@app.route("/")
def main():
    view = request.args.get("view", "week")

    if view == "month":
        today = date.today()
        cal = build_month_view(today.year, today.month)
        return render_template_string(
            HTML,
            title=f"Monats‑Ø {today.strftime('%m.%Y')}",
            calendar=cal,
            week_offset=0
        )

    offset = int(request.args.get("week_offset", 0))
    cal, ws, we = build_week_view(offset)
    return render_template_string(
        HTML,
        title=f"Woche {ws.strftime('%d.%m')} – {we.strftime('%d.%m')}",
        calendar=cal,
        week_offset=offset
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
