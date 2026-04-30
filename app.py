import os
import json
import ssl
from datetime import datetime, timedelta
from urllib.request import urlopen, Request
from urllib.parse import urlencode
from flask import Flask, render_template_string, request

app = Flask(__name__)

# ---------- CONFIG ----------
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
PIXELS_PER_MINUTE = 1
SESSION_STORE = []
TIME_POINTS = set()

# ---------- UTIL ----------
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
    h, m = map(int, hm.split(":"))
    return h * 60 + m


# ---------- DATA ----------
def sync_wed_to_sun():
    SESSION_STORE.clear()
    TIME_POINTS.clear()

    today = datetime.now().date()
    weekday = today.weekday()

    # Mittwoch der aktuellen Woche
    delta_to_wed = (weekday - 2) % 7
    start_date = today - timedelta(days=delta_to_wed)
    end_date = start_date + timedelta(days=4)

    params = {
        "page": 1,
        "perPage": 1000,
        "skipTotal": 1,
        "sort": "start",
        "filter": f"is_deleted=false && event_date>='{start_date}' && event_date<='{end_date}'",
    }

    url = "https://oana.asdf.ooo/api/collections/sessions/records?" + urlencode(params)

    req = Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"})
    context = ssl.create_default_context()

    with urlopen(req, timeout=15, context=context) as response:
        data = json.loads(response.read().decode("utf-8"))

    for item in data.get("items", []):
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

            start_min = to_minutes(start)
            end_min = to_minutes(end)
            if end_min <= start_min:
                continue

            TIME_POINTS.add(start_min)
            TIME_POINTS.add(end_min)

            percent = int((used / max_p) * 100) if max_p > 0 else 0

            SESSION_STORE.append({
                "day": day_name,
                "start_min": start_min,
                "end_min": end_min,
                "text": f"{title}\n{used} / {max_p} ({percent}%)",
                "color": heat_color(percent),
            })
        except Exception:
            continue


def build_time_axis():
    if not TIME_POINTS:
        return [], 0, 0

    sorted_points = sorted(TIME_POINTS)
    base = sorted_points[0]
    end = sorted_points[-1]

    labels = []
    last = None
    for m in sorted_points:
        if last is None or m - last >= 30:
            h = m // 60
            mm = m % 60
            labels.append({
                "label": f"{h:02d}:{mm:02d}",
                "top": m - base,
            })
            last = m

    height = end - base
    return labels, base, height


# ---------- HTML ----------
HTML = """
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>Wochenkalender – Auslastung (%)</title>
<style>
body { font-family: Arial, sans-serif; }
.calendar {
    display: grid;
    grid-template-columns: 90px repeat(5, 1fr);
}
.header {
    text-align: center;
    font-weight: bold;
    padding: 6px;
}
.times {
    position: relative;
}
.time {
    position: absolute;
    font-size: 11px;
}
.day {
    position: relative;
    border-left: 1px solid #ccc;
}
.session {
    position: absolute;
    left: 5px;
    right: 5px;
    padding: 4px;
    border-radius: 4px;
    font-size: 11px;
    white-space: pre-line;
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

    <div class="times" style="height: {{ height }}px;">
        {% for t in times %}
            <div class="time" style="top: {{ t.top }}px;">{{ t.label }}</div>
        {% endfor %}
    </div>

    {% for d in days %}
        <div class="day" id="c{{ d }}" style="height: {{ height }}px;"></div>
    {% endfor %}
</div>

{% for s in sessions %}
<div class="session"
     data-day="{{ s.day }}"
     style="
        top: {{ s.start_min - base_time }}px;
        height: {{ s.end_min - s.start_min }}px;
        background: {{ s.color }};
     ">
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

# ---------- ROUTE ----------
@app.route("/", methods=["GET", "HEAD"])
def main():
    if request.method == "GET":
        sync_wed_to_sun()

    times, base_time, height = build_time_axis()

    return render_template_string(
        HTML,
        days=DISPLAY_DAYS,
        sessions=SESSION_STORE,
        times=times,
        base_time=base_time,
        height=height,
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
