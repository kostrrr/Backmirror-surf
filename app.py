import os
import requests
from datetime import datetime
from flask import Flask, render_template_string

app = Flask(__name__)

DAYS = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
PIXELS_PER_HOUR = 44

SESSION_STORE = {}

def heat_color(percent):
    if percent == 100:
        return "#b00000"
    if percent >= 80:
        return "#d9480f"
    if percent >= 60:
        return "#f49300"
    if percent >= 40:
        return "#ffd43b"
    return "#fff4cc"

def time_to_px(hm):
    h, m = map(int, hm.split(":"))
    return ((h - 11) * 60 + m) * PIXELS_PER_HOUR / 60

def sync_today_sessions():
    today = datetime.now().strftime("%Y-%m-%d")

    url = (
        "https://oana.asdf.ooo/api/collections/sessions/records"
        "?page=1"
        "&perPage=1000"
        "&skipTotal=1"
        "&sort=start"
        f"&filter=is_deleted = false && event_date = '{today}'"
    )

    response = requests.get(url, timeout=10)
    response.raise_for_status()

    items = response.json().get("items", [])

    for item in items:
        key = (
            item.get("event_date"),
            item.get("start"),
            item.get("end"),
            item.get("category_external_id"),
        )

        used = item.get("participants_count", 0)
        max_p = item.get("max_participants", 0)

        if key not in SESSION_STORE:
            SESSION_STORE[key] = {
                "day": DAYS[datetime.strptime(item["event_date"], "%Y-%m-%d").weekday()],
                "start": item["start"],
                "end": item["end"],
                "used": used,
                "max": max_p,
                "title": item.get("title", "Session"),
            }
        else:
            SESSION_STORE[key]["used"] = max(SESSION_STORE[key]["used"], used)

def prepare_sessions_for_view():
    out = []
    for s in SESSION_STORE.values():
        percent = 0
        if s["max"] > 0:
            percent = int((s["used"] / s["max"]) * 100)

        out.append({
            "day": s["day"],
            "top": time_to_px(s["start"]),
            "height": time_to_px(s["end"]) - time_to_px(s["start"]),
            "text": f'{s["title"]}\n{s["used"]} / {s["max"]} ({percent}%)',
            "color": heat_color(percent),
        })
    return out

HTML = """
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>Wochenkalender – Auslastung (%)</title>
<style>
body { font-family: Arial, sans-serif; }
.calendar { display:grid; grid-template-columns:80px repeat(7,1fr); }
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

@app.route("/")
def main():
    sync_today_sessions()
    sessions = prepare_sessions_for_view()
    return render_template_string(
        HTML,
        days=DAYS,
        sessions=sessions,
        h=time_to_px("22:00")
    )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
