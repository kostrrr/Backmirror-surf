import os
import json
import ssl
from datetime import datetime, date, timedelta
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

PIXELS_PER_MINUTE = 2


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


def fetch_sessions():
    params = {
        "page": 1,
        "perPage": 2000,
        "skipTotal": 1,
        "sort": "event_date,start",
        "filter": "is_deleted=false && source='coremanager' && source_category_id=4",
        "fields": "event_date,start,end,participants_count,max_participants",
    }

    url = "https://oana.asdf.ooo/api/collections/sessions/records?" + urlencode(params)
    req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    context = ssl.create_default_context()

    with urlopen(req, timeout=30, context=context) as r:
        return json.loads(r.read().decode("utf-8")).get("items", [])


# ---------- MONATS-HEATMAP ----------
def build_month_heatmap(year: int, month: int):
    sessions = fetch_sessions()
    slots = {}

    for s in sessions:
        d = datetime.strptime(s["event_date"], "%Y-%m-%d").date()
        if d.year != year or d.month != month:
            continue

        start = minutes_from_iso(s["start"])
        end = minutes_from_iso(s["end"])
        used = int(s.get("participants_count") or 0)
        max_p = int(s.get("max_participants") or 0)
        if max_p == 0:
            continue

        percent = int((used / max_p) * 100)

        m = (start // 45) * 45  # 45‑Minuten‑Raster
        key = m
        slots[key] = max(slots.get(key, 0), percent)

    if not slots:
        return [], 0

    base = min(slots.keys())
    top = max(slots.keys()) + 45

    heatmap = []
    for m in sorted(slots.keys()):
        h, mm = divmod(m, 60)
        heatmap.append({
            "label": f"{h:02d}:{mm:02d}",
            "top": (m - base) * PIXELS_PER_MINUTE,
            "height": 45 * PIXELS_PER_MINUTE,
            "percent": slots[m],
            "color": heat_color(slots[m]),
        })

    total_height = (top - base) * PIXELS_PER_MINUTE
    return heatmap, total_height


HTML = """
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>Auslastung</title>
<style>
body{font-family:Arial;}
.nav{margin-bottom:10px;}
.column{position:relative;padding-left:60px;min-width:360px;}
.time{position:absolute;left:-55px;font-size:11px;}
.block{
 position:absolute;left:0;right:10px;
 padding:8px;border-radius:4px;font-size:12px;
}
</style>
</head>
<body>

<h2>{{ title }}</h2>

<div class="nav">
<a href="/?view=week">Woche</a> |
<a href="/?view=month">Monat (Heatmap)</a>
</div>

<div class="column" style="height:{{ height }}px;">
{% for b in blocks %}
  <div class="time" style="top:{{ b.top }}px">{{ b.label }}</div>
  <div class="block"
       style="top:{{ b.top }}px;height:{{ b.height }}px;background:{{ b.color }}">
    {{ b.percent }}%
  </div>
{% endfor %}
</div>

</body>
</html>
"""


@app.route("/")
def main():
    view = request.args.get("view", "week")

    if view == "month":
        today = date.today()
        blocks, height = build_month_heatmap(today.year, today.month)
        return render_template_string(
            HTML,
            title=f"Monats‑Heatmap {today.strftime('%m.%Y')}",
            blocks=blocks,
            height=height,
        )

    return "Wochenansicht bleibt unverändert – nutze ?view=month"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
