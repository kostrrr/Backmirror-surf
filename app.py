import os
import json
import ssl
from datetime import datetime, timedelta, date
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

PIXELS_PER_MINUTE = 2  # ✅ größer + lesbar


def heat_color(percent: int) -> str:
    if percent >= 100:
        return "#b00000"
    if percent >= 80:
        return "#d9480f"
    if percent >= 60:
        return "#f49300"
    if percent >= 40:
        return "#ffd43b"
    return "#fff4cc"


def minutes_from_iso(ts: str) -> int:
    dt = datetime.fromisoformat(ts)
    return dt.hour * 60 + dt.minute


def get_week_bounds(ref: date):
    """Mittwoch–Sonntag der Referenzwoche"""
    weekday = ref.weekday()  # Mon=0
    wed = ref - timedelta(days=(weekday - 2) % 7)
    sun = wed + timedelta(days=4)
    return wed, sun


def fetch_sessions():
    params = {
        "page": 1,
        "perPage": 1000,
        "skipTotal": 1,
        "sort": "event_date,start",
        "filter": "is_deleted=false && source='coremanager' && source_category_id=4",
        "fields": "event_date,start,end,title,participants_count,max_participants",
    }

    url = "https://oana.asdf.ooo/api/collections/sessions/records?" + urlencode(params)
    req = Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"})
    context = ssl.create_default_context()

    with urlopen(req, timeout=30, context=context) as response:
        data = json.loads(response.read().decode("utf-8"))

    return data.get("items", [])


def build_week_calendar(week_offset: int):
    today = date.today()
    ref_date = today + timedelta(weeks=week_offset)
    week_start, week_end = get_week_bounds(ref_date)

    raw = fetch_sessions()
    days = {}

    for item in raw:
        event_date = item.get("event_date")
        if not event_date:
            continue

        d = datetime.strptime(event_date, "%Y-%m-%d").date()
        if not (week_start <= d <= week_end):
            continue

        start_ts = item.get("start")
        end_ts = item.get("end")
        if not start_ts or not end_ts:
            continue

        start_min = minutes_from_iso(start_ts)
        end_min = minutes_from_iso(end_ts)
        if end_min <= start_min:
            continue

        used = int(item.get("participants_count") or 0)
        max_p = int(item.get("max_participants") or 0)
        percent = int((used / max_p) * 100) if max_p > 0 else 0
        title = (item.get("title") or "Session").strip()

        key = d.isoformat()
        if key not in days:
            days[key] = {
                "label": f"{ALL_WEEKDAYS[d.weekday()]} {d.strftime('%d.%m')}",
                "times": set(),
                "sessions": [],
            }

        days[key]["times"].add(start_min)
        days[key]["times"].add(end_min)

        days[key]["sessions"].append({
            "start": start_min,
            "end": end_min,
            "text": f"{title}\n{used} / {max_p} ({percent}%)",
            "color": heat_color(percent),
        })

    calendar = []

    for key in sorted(days.keys()):
        d = days[key]
        base = min(d["times"])
        top = max(d["times"])
        height = (top - base) * PIXELS_PER_MINUTE

        slots = []
        for m in sorted(d["times"]):
            h = m // 60
            mm = m % 60
            slots.append({
                "label": f"{h:02d}:{mm:02d}",
                "top": (m - base) * PIXELS_PER_MINUTE,
            })

        sessions = []
        for s in d["sessions"]:
            sessions.append({
                "top": (s["start"] - base) * PIXELS_PER_MINUTE,
                "height": (s["end"] - s["start"]) * PIXELS_PER_MINUTE,
                "text": s["text"],
                "color": s["color"],
            })

        calendar.append({
            "label": d["label"],
            "height": height,
            "slots": slots,
            "sessions": sessions,
        })

    return calendar, week_start, week_end


HTML = """
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>Wochenkalender – Auslastung (%)</title>
<style>
body { font-family: Arial, sans-serif; }
.nav { margin-bottom: 10px; }
.days { display: flex; gap: 20px; align-items: flex-start; }
.day { position: relative; padding-left: 60px; border-left: 1px solid #ccc; }
.day-title { font-weight: bold; margin-bottom: 6px; }
.timeline { position: relative; }
.time { position: absolute; left: -55px; font-size: 11px; }
.session {
    position:absolute;
    left:0;
    right:10px;
    padding:6px;
    border-radius:4px;
    font-size:12px;
    white-space:pre-line;
}
</style>
</head>
<body>

<h2>Wochenkalender – Auslastung (%)</h2>

<div class="nav">
  <a href="/?week_offset={{ week_offset - 1 }}">◀ Vorige Woche</a> |
  <strong>{{ week_start }} – {{ week_end }}</strong> |
  <a href="/?week_offset={{ week_offset + 1 }}">Nächste Woche ▶</a>
</div>

<div class="days">
{% for d in calendar %}
  <div class="day">
    <div class="day-title">{{ d.label }}</div>
    <div class="timeline" style="height: {{ d.height }}px;">
      {% for t in d.slots %}
        <div class="time" style="top: {{ t.top }}px;">{{ t.label }}</div>
      {% endfor %}
      {% for s in d.sessions %}
        <div class="session"
             style="top: {{ s.top }}px; height: {{ s.height }}px; background: {{ s.color }};">
          {{ s.text }}
        </div>
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
    week_offset = int(request.args.get("week_offset", 0))
    calendar, ws, we = build_week_calendar(week_offset)
    return render_template_string(
        HTML,
        calendar=calendar,
        week_start=ws.strftime("%d.%m.%Y"),
        week_end=we.strftime("%d.%m.%Y"),
        week_offset=week_offset,
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
