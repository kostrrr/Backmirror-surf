import os
from flask import Flask, render_template_string

app = Flask(__name__)

DAYS = ["Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]

def heat_color(percent):
    if percent == 100:
        return "#b00000"      # sehr dunkel rot
    elif percent >= 80:
        return "#d9480f"      # dunkel
    elif percent >= 60:
        return "#f49300"      # mittel
    elif percent >= 40:
        return "#ffd43b"      # hell
    else:
        return "#fff4cc"      # sehr hell gelb

SESSIONS = [
    {
        "day": "Freitag",
        "start": "18:45",
        "end": "19:30",
        "type": "Basic Intense",
        "max": 5,
        "used": 5
    },
    {
        "day": "Samstag",
        "start": "14:45",
        "end": "15:30",
        "type": "Basic Intense",
        "max": 5,
        "used": 3
    },
    {
        "day": "Sonntag",
        "start": "14:00",
        "end": "14:30",
        "type": "Employee",
        "max": None,
        "used": None
    },
    {
        "day": "Mittwoch",
        "start": "15:15",
        "end": "16:00",
        "type": "Basic",
        "max": 10,
        "used": 6
    }
]

RENDER_SESSIONS = []
for s in SESSIONS:
    if s["type"] == "Employee":
        color = "#cccccc"
        text = "Employee\nnicht buchbar"
    else:
        percent = int((s["used"] / s["max"]) * 100)
        color = heat_color(percent)
        text = f"{s['type']}\n{s['used']} / {s['max']} ({percent}%)"

    RENDER_SESSIONS.append({
        "day": s["day"],
        "start": s["start"],
        "end": s["end"],
        "text": text,
        "color": color
    })

HTML = """
<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<title>Session-Auslastung – Woche</title>
<style>
body { font-family: Arial, sans-serif; }
.calendar { display: grid; grid-template-columns: 80px repeat(5, 1fr); }
.time { border-bottom: 1px solid #eee; font-size: 12px; padding: 4px; }
.day { border-left: 1px solid #ccc; position: relative; height: 44px; }
.header { font-weight: bold; text-align: center; padding: 6px; border-bottom: 2px solid #000; }
.session {
    position: absolute;
    left: 4px;
    right: 4px;
    border-radius: 4px;
    padding: 4px;
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

    {% for hour in range(11,22) %}
        <div class="time">{{ "%02d:00"|format(hour) }}</div>
        {% for d in days %}
            <div class="day"></div>
        {% endfor %}
    {% endfor %}
</div>

{% for s in sessions %}
<div class="session"
     style="
        top: {{ (s.start.split(':')[0]|int - 11)*44 + (s.start.split(':')[1]|int)/60*44 }}px;
        height: {{ ((s.end.split(':')[0]|int*60 + s.end.split(':')[1]|int) - (s.start.split(':')[0]|int*60 + s.start.split(':')[1]|int)) /60*44 }}px;
        grid-column: {{ days.index(s.day) + 2 }};
        background: {{ s.color }};
     ">
{{ s.text }}
</div>
{% endfor %}

</body>
</html>
"""

@app.route("/")
def calendar():
    return render_template_string(
        HTML,
        days=DAYS,
        sessions=RENDER_SESSIONS
    )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
