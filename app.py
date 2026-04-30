import os
import json
import ssl
from datetime import datetime, timedelta
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

DISPLAY_DAYS = ["Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]

BASE_START_HOUR = 10
BASE_END_HOUR = 22
PIXELS_PER_HOUR = 45
TOTAL_HEIGHT = (BASE_END_HOUR - BASE_START_HOUR) * PIXELS_PER_HOUR

SESSION_STORE = []


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


def time_to_px(hm):
    try:
        h, m = map(int, hm.split(":"))
        minutes = (h - BASE_START_HOUR) * 60 + m
        if minutes < 0:
            minutes = 0
        return minutes * PIXELS_PER_HOUR / 60
    except Exception:
        return 0


def build_time_slots():
    slots = []
    current = BASE_START_HOUR * 60
    end = BASE_END_HOUR * 60
    while current <= end:
        h = current // 60
        m = current % 60
        slots.append({"label": f"{h:02d}:{m:02d}", "top": (current - BASE_START_HOUR * 60) * PIXELS_PER_HOUR / 60})
        current += 45
    return slots


def sync_week_sessions():
    try:
        SESSION_STORE.clear()

        today = datetime.now().date()
        weekday_index = today.weekday()
        start_date = today.strftime("%Y-%m-%d")
        end_date = (today + timedelta(days=6 - weekday_index)).strftime("%Y-%m-%d")

        params = {
            "page": 1,
            "perPage": 1000,
            "skipTotal": 1,
            "sort": "start",
            "filter": f"is_deleted=false && event_date>='{start_date}' && event_date<='{end_date}'",
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
        with urlopen(req, timeout=10, context=context) as response:
            payload = json.loads(response.read().decode("utf-8"))

        items = payload.get("items", [])
    except Exception:
        return

    for item in items:
        try:
            event_date = item.get("event_date")
            start = item.get("start")
            end = item.get("end")
            title = (item.get("title") or "Session").strip()
            used = int(item.get("participants_count") or 0)
            max_p = int(item.get("max_participants") or 0)

            if not event_date or not start or not end:
                continue

            weekday_idx = datetime.strptime(event_date, "%Y-%m-%d").weekday()
            day_name = ALL_WEEKDAYS.get(weekday_idx)

            if day_name not in DISPLAY_DAYS:
                continue

            top = time_to_px(start)
            bottom = time_to_px(end)
            height = bottom - top
            if height <= 0:
                height = PIXELS_PER_HOUR

            percent = int((used / max_p) * 100) if max_p > 0 else 0

            SESSION_STORE.append({
                "day": day_name,
                "top": top,
                "height": height,
                "text": f"{title}\n{used} / {max_p} ({percent}%)",
                "color": heat_color(percent),
            })
        except Exception:
            continue


HTML = """
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>Wochenkalender – Auslastung (%)</title>
<style>
body { font-family: Arial, sans-serif; }
.calendar { display:grid; grid-template-columns:80px repeat(5,1fr); }
.header { text-align:center; font-weight:bold; padding:6px; }
.times { position:relative; height:{{ total_height }}px; }
.time { position:absolute; font-size:11px; }
.day { position:relative; height:{{ total_height }}px; border-left:1px solid #ccc; }
.session {
    position:absolute;
    left:5px;
    right:5px;
    padding:4px;
    border-radius:4px;
    font-size:11px;
    white-space:pre-line;
}
</style>
</head>
<body>

<h2>Wochenkalender – Auslastung (%)</h2>

<div class="calendar">
    <div></div>
    {% for d in days %}
        <div class="header">{{ d }}</div>
    {% endfor %}

    <div class="times">
        {% for t in slots %}
        <div class="time" style="top:{{ t.top }}px;">{{ t.label }}</div>
        {% endfor %}
    </div>

    {% for d in days %}
    <div class="day" id="c{{ d }}"></div>
    {% endfor %}
</div>

{% for s in sessions %}
<div class="session"
     data-day="{{ s.day }}"
     style="top:{{ s.top }}px; height:{{ s.height }}px; background:{{ s.color }};">
{{ s.text }}
</div>
{% endfor %}

<script>
document.querySelectorAll(".session").forEach(el => {
    const col = document.getElementById("c" + el.dataset.day);
    if (col) col.appendChild(el);
});
</script>

</body>
</html>
"""


@app.route("/", methods=["GET", "HEAD"])
def main():
    if request.method == "GET":
        try:
            sync_week_sessions()
        except Exception:
            pass

    return render_template_string(
        HTML,
        days=DISPLAY_DAYS,
        sessions=SESSION_STORE,
        slots=build_time_slots(),
        total_height=TOTAL_HEIGHT,
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
