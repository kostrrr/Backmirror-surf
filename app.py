import os
import json
import ssl
from datetime import datetime
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

PIXELS_PER_HOUR = 44
SESSION_STORE = {}

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
        return ((h - 11) * 60 + m) * PIXELS_PER_HOUR / 60
    except Exception:
        return 0

def sync_today_sessions():
    today = datetime.now().strftime("%Y-%m-%d")

    params = {
        "page": 1,
        "perPage": 1000,
        "skipTotal": 1,
        "sort": "start",
        "filter": f"is_deleted=false && event_date='{today}'",
    }

    url = "https://oana.asdf.ooo/api/collections/sessions/records?" + urlencode(params)

    try:
        req = Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0",
                "Accept": "application/json",
            },
        )

        context = ssl.create_default_context()

        with urlopen(req, timeout=10, context=context) as response:
            raw = response.read().decode("utf-8")
            payload = json.loads(raw)

        items = payload.get("items", [])
    except Exception:
        return

    for item in items:
        try:
            event_date = item.get("event_date")
            start = item.get("start")
            end = item.get("end")
            category_id = item.get("category_external_id")

            if not event_date or not start or not end or not category_id:
                continue

            weekday_index = datetime.strptime(event_date, "%Y-%m-%d").weekday()
            day_name = ALL_WEEKDAYS.get(weekday_index)

            if day_name not in DISPLAY_DAYS:
                continue

            used = int(item.get("participants_count") or 0)
            max_p = int(item.get("max_participants") or 0)
            title = (item.get("title") or "Session").strip()

            key = (event_date, start, end, category_id)

            if key not in SESSION_STORE:
                SESSION_STORE[key] = {
                    "day": day_name,
                    "start": start,
                    "end": end,
                    "used": used,
                    "max": max_p,
                    "title": title,
                }
            else:
                if used > SESSION_STORE[key]["used"]:
                    SESSION_STORE[key]["used"] = used
        except Exception:
            continue

def prepare_sessions_for_view():
    sessions = []

    for s in SESSION_STORE.values():
        max_p = s.get("max", 0)
        used = s.get("used", 0)

        percent = int((used / max_p) * 100) if max_p > 0 else 0

        top = time_to_px(s["start"])
        height = time_to_px(s["end"]) - top
        if height <= 0:
            height = PIXELS_PER_HOUR

        sessions.append({
            "day": s["day"],
            "top": top,
            "height": height,
            "text": f"{s['title']}\n{used} / {max_p} ({percent}%)",
            "color": heat_color(percent),
        })

    return sessions

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
.day { position:relative; height:{{ h }}px; border-left:1px solid #ccc; }
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

    <div>11:00–22:00</div>
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
        sync_today_sessions()
    return render_template_string(
        HTML,
        days=DISPLAY_DAYS,
        sessions=prepare_sessions_for_view(),
        h=time_to_px("22:00"),
    )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
