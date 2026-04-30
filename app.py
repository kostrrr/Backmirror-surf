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

PIXELS_PER_MINUTE = 2


def heat_color(percent: int) -> str:
    if percent >= 90:
        return "#b00000"
    if percent >= 70:
        return "#d9480f"
    if percent >= 50:
        return "#f49300"
    if percent >= 30:
        return "#ffd43b"
    return "#fff4cc"


def minutes_from_iso(ts: str) -> int:
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
    context = ssl.create_default_context()

    with urlopen(req, timeout=30, context=context) as r:
        return json.loads(r.read().decode("utf-8")).get("items", [])


def get_week_bounds(ref):
    wd = ref.weekday()
    wed = ref - timedelta(days=(wd - 2) % 7)
    sun = wed + timedelta(days=4)
    return wed, sun


# ---------------- WEEK VIEW ----------------
def build_week_calendar(week_offset):
    ref = date.today() + timedelta(weeks=week_offset)
    ws, we = get_week_bounds(ref)

    days = {}
    for s in fetch_sessions():
        d = datetime.strptime(s["event_date"], "%Y-%m-%d").date()
        if not (ws <= d <= we):
            continue

        sm = minutes_from_iso(s["start"])
        em = minutes_from_iso(s["end"])
        if em <= sm:
            continue

        used = int(s.get("participants_count") or 0)
        maxp = int(s.get("max_participants") or 0)
        percent = int((used / maxp) * 100) if maxp > 0 else 0

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
            "text": f"{s['title']}\n{used}/{maxp} ({percent}%)",
            "color": heat_color(percent),
        })

    calendar = []
    for k in sorted(days):
        d = days[k]
        base = min(d["times"])
        top = max(d["times"])
        height = (top - base) * PIXELS_PER_MINUTE

        slots = [{
            "label": f"{m//60:02d}:{m%60:02d}",
            "top": (m - base) * PIXELS_PER_MINUTE
        } for m in sorted(d["times"])]

        sessions = [{
            "top": (s["start"] - base) * PIXELS_PER_MINUTE,
            "height": (s["end"] - s["start"]) * PIXELS_PER_MINUTE,
            "text": s["text"],
            "color": s["color"],
        } for s in d["sessions"]]

        calendar.append({
            "label": d["label"],
            "height": height,
            "slots": slots,
            "sessions": sessions,
        })

    return calendar, ws, we


# ---------------- MONTH AVERAGE VIEW ----------------
def build_month_average(year, month):
    slots = {}

    for s in fetch_sessions():
        d = datetime.strptime(s["event_date"], "%Y-%m-%d").date()
        if d.year != year or d.month != month:
            continue

        weekday = d.weekday()
        sm = minutes_from_iso(s["start"])
        em = minutes_from_iso(s["end"])
        title = s["title"]

        used = int(s.get("participants_count") or 0)
        maxp = int(s.get("max_participants") or 0)
        if maxp == 0:
            continue

        percent = (used / maxp) * 100

        key = (weekday, sm, em, title)

        if key not in slots:
            slots[key] = {
                "values": [],
                "weekday": weekday,
                "start": sm,
                "end": em,
                "title": title,
            }

        slots[key]["values"].append(percent)

    rows = []
    for s in slots.values():
        avg = sum(s["values"]) / len(s["values"])
        rows.append({
            "weekday": ALL_WEEKDAYS[s["weekday"]],
            "start": f"{s['start']//60:02d}:{s['start']%60:02d}",
            "end": f"{s['end']//60:02d}:{s['end']%60:02d}",
            "title": s["title"],
            "avg": round(avg),
            "color": heat_color(int(avg)),
        })

    rows.sort(key=lambda r: (list(ALL_WEEKDAYS.values()).index(r["weekday"]), r["start"]))
    return rows


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
table{border-collapse:collapse;width:100%;}
th,td{padding:6px;border-bottom:1px solid #ddd;text-align:left;}
.badge{padding:4px 8px;border-radius:4px;color:#000;}
</style>
</head>
<body>

<h2>{{ title }}</h2>

<div class="nav">
<a href="/?view=week">Woche</a> |
<a href="/?view=month">Monat (Ø‑Auslastung)</a>
</div>

{% if view == "week" %}
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

{% else %}
<table>
<tr>
<th>Wochentag</th>
<th>Zeit</th>
<th>Session</th>
<th>Ø Auslastung</th>
</tr>
{% for r in rows %}
<tr>
<td>{{ r.weekday }}</td>
<td>{{ r.start }}–{{ r.end }}</td>
<td>{{ r.title }}</td>
<td><span class="badge" style="background:{{ r.color }}">{{ r.avg }}%</span></td>
</tr>
{% endfor %}
</table>
{% endif %}

</body>
</html>
"""


@app.route("/")
def main():
    view = request.args.get("view", "week")

    if view == "month":
        today = date.today()
        rows = build_month_average(today.year, today.month)
        return render_template_string(
            HTML,
            view="month",
            title=f"Monats‑Durchschnitt {today.strftime('%m.%Y')}",
            rows=rows,
        )

    week_offset = int(request.args.get("week_offset", 0))
    calendar, ws, we = build_week_calendar(week_offset)
    return render_template_string(
        HTML,
        view="week",
        title=f"Woche {ws.strftime('%d.%m')} – {we.strftime('%d.%m')}",
        calendar=calendar,
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
