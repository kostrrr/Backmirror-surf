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

# Beispielhafte echte Sessions (Simulation)
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

# Aufbereitung für Anzeige
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
<html>
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
