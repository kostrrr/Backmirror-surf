import os
from flask import Flask, render_template_string

app = Flask(__name__)

DAYS = ["Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]

def heat_color(percent):
    if percent == 100:
        return "#b00000"      # Alarm-Rot
    elif percent >= 80:
        return "#d9480f"
    elif percent >= 60:
        return "#f49300"
    elif percent >= 40:
        return "#ffd43b"
    else:
        return "#fff4cc"

SESSIONS = [
    {
        "day": "Mittwoch",
        "start": "15:15",
        "end": "16:00",
        "text": "Basic\n6 / 10 (60%)",
        "color": heat_color(60),
    },
    {
        "day": "Freitag",
        "start": "18:45",
        "end": "19:30",
        "text": "Basic Intense\n5 / 5 (100%)",
        "color": heat_color(100),
    },
    {
        "day": "Samstag",
        "start": "14:45",
        "end": "15:30",
        "text": "Basic Intense\n3 / 5 (60%)",
        "color": heat_color(60),
    },
    {
        "day": "Sonntag",
        "start": "14:00",
        "end": "14:30",
        "text": "Employee\nnicht buchbar",
        "color": "#cccccc",
    }
]

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
    border-bottom: 1px solid #eee;
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
     style="
        top: {{ s.top }}px;
        height: {{ s.height }}px;
        background: {{ s.color }};
     "
     data-day="{{ s.day }}">
{{ s.text }}
</div>
{% endfor %}

<script>
document.querySelectorAll(".session").forEach(el => {
    const day = el.dataset.day;
    const col = document.getElementById("col-" + day);
    if (col) col.appendChild(el);
});
</script>

</body>
</html>
"""

def time_to_px(t):
    h, m = map(int, t.split(":"))
    return ((h - 11) * 60 + m) * 44 / 60

@app.route("/")
def calendar():
    rendered = []
    for s in SESSIONS:
        rendered.append({
            **s,
            "top": time_to_px(s["start"]),
            "height": time_to_px(s["end"]) - time_to_px(s["start"]),
        })

    return render_template_string(
        HTML,
        days=DAYS,
        sessions=rendered,
        total_height=time_to_px("22:00")
    )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
