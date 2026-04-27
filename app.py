import os
from datetime import datetime, timedelta
from flask import Flask, render_template_string

app = Flask(__name__)

DAYS = ["Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]

PIXELS_PER_HOUR = 44

def heat_color(percent):
    if percent == 100:
        return "#b00000"
    elif percent >= 80:
        return "#d9480f"
    elif percent >= 60:
        return "#f49300"
    elif percent >= 40:
        return "#ffd43b"
    else:
        return "#fff4cc"

def time_to_px(t):
    h, m = map(int, t.split(":"))
    return ((h - 11) * 60 + m) * PIXELS_PER_HOUR / 60

def parse_time(t):
    return datetime.strptime(t, "%H:%M").time()

def in_valid_window(start_time):
    now = datetime.now().time()
    start = parse_time(start_time)
    start_dt = datetime.combine(datetime.today(), start)
    return (
        start_dt - timedelta(minutes=5)
        <= datetime.combine(datetime.today(), now)
        <= start_dt + timedelta(minutes=40)
    )

# Beispiel-Sessions (Simulation)
RAW_SESSIONS = [
    {
        "day": "Mittwoch",
        "start": "15:15",
        "end": "16:00",
        "type": "Basic",
        "max": 10,
        "used": 6,
    },
    {
        "day": "Freitag",
        "start": "18:45",
        "end": "19:30",
        "type": "Basic Intense",
        "max": 5,
        "used": 5,
    },
    {
        "day": "Samstag",
        "start": "14:45",
        "end": "15:30",
        "type": "Basic Intense",
        "max": 5,
        "used": 3,
    },
    {
        "day": "Sonntag",
        "start": "14:00",
        "end": "14:30",
        "type": "Employee",
        "max": None,
        "used": None,
    },
]

def prepare_sessions():
    rendered = []
    for s in RAW_SESSIONS:

        # Employee immer anzeigen (keine Zeitregel)
        if s["type"] == "Employee":
            rendered.append({
                "day": s["day"],
                "top": time_to_px(s["start"]),
                "height": time_to_px(s["end"]) - time_to_px(s["start"]),
                "text": "Employee\nnicht buchbar",
                "color": "#cccccc",
            })
            continue

        # Zeitfenster erzwingen
        if not in_valid_window(s["start"]):
            continue

        percent = int((s["used"] / s["max"]) * 100)
        rendered.append({
            "day": s["day"],
            "top": time_to_px(s["start"]),
            "height": time_to_px(s["end"]) - time_to_px(s["start"]),
            "text": f"{s['type']}\n{s['used']} / {s['max']} ({percent}%)",
            "color": heat_color(percent),
        })

    return rendered

HTML = """
<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<title>Wochenkalender – Auslastung (%)</title>
<style>
body { font-family: Arial, sans-serif; }
.calendar {
    display: grid;
    grid-template-columns: 80px repeat(5, 1fr);
}
.header {
    text-align: center;
    font-weight: bold;
    padding: 6px;
    border-bottom: 2px solid #000;
}
.time {
    font-size: 12px;
    padding: 4px;
}
.day-column {
    position: relative;
    height: {{ total_height }}px;
    border-left: 1px solid #ccc;
}
.session {
    position: absolute;
    left: 5px;
    right: 5px;
    padding: 4px;
    font-size: 11px;
    border-radius: 4px;
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

    <div class="time">11:00<br>–<br>22:00</div>
    {% for d in days %}
        <div class="day-column" id="col-{{ d }}"></div>
    {% endfor %}
</div>

{% for s in sessions %}
<div class="session"
     style="top: {{ s.top }}px; height: {{ s.height }}px; background: {{ s.color }};"
     data-day="{{ s.day }}">
{{ s.text }}
</div>
{% endfor %}

<script>
document.querySelectorAll(".session").forEach(el => {
    const col = document.getElementById("col-" + el.dataset.day);
    if (col) col.appendChild(el);
});
</script>

</body>
</html>
"""

@app.route("/")
def calendar():
    sessions = prepare_sessions()
    return render_template_string(
        HTML,
        days=DAYS,
        sessions=sessions,
        total_height=time_to_px("22:00"),
    )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
``
