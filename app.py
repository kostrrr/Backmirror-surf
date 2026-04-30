import os
import json
import ssl
from datetime import datetime, timedelta
from urllib.request import urlopen, Request
from urllib.parse import urlencode
from flask import Flask, render_template_string

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

PIXELS_PER_MINUTE = 1


def heat_color(percent):
    if percent >= 100:
        return "#b00000"
    if percent >= 80:
        return "#d9480f"
    if percent >= 60:
        return "#f49300"
    if percent >= 40:
        return "#ffd43b"
    return "#fff4cc"


def to_minutes(hm):
    h, m = hm.split(":")
    return int(h) * 60 + int(m)


def fetch_sessions():
    today = datetime.now().date()
    start_date = (today - timedelta(days=7)).strftime("%Y-%m-%d")
    end_date = (today + timedelta(days=14)).strftime("%Y-%m-%d")

    params = {
        "page": 1,
        "perPage": 1000,
        "skipTotal": 1,
        "sort": "event_date,start",
        "filter": (
            "is_deleted=false && "
            "source='coremanager' && "
            "source_category_id=4 && "
            f"event_date>='{start_date}' && event_date<='{end_date}'"
        ),
        "fields": (
            "event_date,start,end,title,"
            "participants_count,max_participants"
        ),
    }

    url = "https://oana.asdf.ooo/api/collections/sessions/records?" + urlencode(params)

    req = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json",
        },
    )

    context = ssl.create_default_context()
    with urlopen(req, timeout=30, context=context) as response:
        payload = json.loads(response.read().decode("utf-8"))

    return payload.get("items", [])


def build_calendar():
    raw = fetch_sessions()
    days = {}

    for item in raw:
        try:
            event_date = item.get("event_date")
            start = item.get("start")
            end = item.get("end")
            if not event_date or not start or not end:
                continue

            date_obj = datetime.strptime(event_date, "%Y-%m-%d").date()
            weekday_label = ALL_WEEKDAYS[date_obj.weekday()]

            start_min = to_minutes(start)
            end_min = to_minutes(end)
            if end_min <= start_min:
                continue

            used = int(item.get("participants_count") or 0)
            max_p = int(item.get("max_participants") or 0)
            percent = int((used / max_p) * 100) if max_p > 0 else 0
            title = (item.get("title") or "Session").strip()

            if event_date not in days:
                days[event_date] = {
                    "label": f"{weekday_label} {date_obj.strftime('%d.%m')}",
                    "sessions": [],
                    "times": set(),
                }

            days[event_date]["times"].add(start_min)
            days[event_date]["times"].add(end_min)

            days[event_date]["sessions"].append({
                "start": start_min,
                "end": end_min,
                "text": f"{title}\n{used} / {max_p} ({percent}%)",
                "color": heat_color(percent),
            })
        except Exception:
            continue

    calendar = []

    for date_key in sorted(days.keys()):
        d = days[date_key]
        base = min(d["times"])
        end = max(d["times"])
        height = end - base

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
            "height": height * PIXELS_PER_MINUTE,
            "slots": slots,
            "sessions": sessions,
        })

    return calendar


HTML = """
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>Wochenkalender – Auslastung (%)</title>
<style>
body { font-family: Arial, sans-serif; }
.days { display: flex; gap: 20px; }
.day { position: relative; padding-left: 60px; border-left: 1px solid #ccc; }
.day-title { font-weight: bold; margin-bottom: 6px; }
.timeline { position: relative; }
.time { position: absolute; left: -55px; font-size: 11px; }
.session {
    position: absolute;
    left: 0;
    right: 10px;
    padding: 4px;
    border-radius: 4px;
    font-size: 11px;
    white-space: pre-line;
}
</style>
</head>
<body>

<h2>Wochenkalender – Auslastung (%)</h2>

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
    calendar = build_calendar()
    return render_template_string(HTML, calendar=calendar)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
