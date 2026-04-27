import os
from datetime import datetime, timedelta
from flask import Flask, render_template_string
app = Flask(name)
DAYS = ["Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
PIXELS_PER_HOUR = 44
# ========= DATENSPEICHER (IN-MEMORY) =========
MEASUREMENTS = []
def heat_color(p):
if p == 100: return "#b00000"
if p >= 80:  return "#d9480f"
if p >= 60:  return "#f49300"
if p >= 40:  return "#ffd43b"
return "#fff4cc"
def time_to_px(hm):
h, m = map(int, hm.split(":"))
return ((h - 11) * 60 + m) * PIXELS_PER_HOUR / 60
def in_time_window(start):
now = datetime.now()
s = datetime.combine(now.date(), datetime.strptime(start, "%H:%M").time())
return s - timedelta(minutes=5) <= now <= s + timedelta(minutes=40)
# ========= BEISPIEL-SESSIONS (SIMULATION) =========
RAW = [
{"day":"Mittwoch","start":"15:15","end":"16:00","type":"Basic","max":10,"used":6},
{"day":"Freitag","start":"18:45","end":"19:30","type":"Basic Intense","max":5,"used":5},
{"day":"Samstag","start":"14:45","end":"15:30","type":"Basic Intense","max":5,"used":3},
{"day":"Sonntag","start":"14:00","end":"14:30","type":"Employee"}
]
def collect_measurement(session, percent):
MEASUREMENTS.append({
"date": datetime.now().date(),
"day": session["day"],
"start": session["start"],
"end": session["end"],
"percent": percent,
"recorded_at": datetime.now()
})
def prepare_sessions():
out = []
for s in RAW:
top = time_to_px(s["start"])
height = time_to_px(s["end"]) - top
    # Employee: anzeigen, aber NIE sammeln  
    if s["type"] == "Employee":  
        out.append({  
            "day": s["day"],  
            "top": top,  
            "height": height,  
            "text": "Employee\nnicht buchbar",  
            "color": "#cccccc"  
        })  
        continue  

    percent = int(s["used"] / s["max"] * 100)  

    # ========= SAMMELLOGIK =========
    if percent == 100 or in_time_window(s["start"]):  
        collect_measurement(s, percent)  
    else:  
        continue  

    out.append({  
        "day": s["day"],  
        "top": top,  
        "height": height,  
        "text": f"{s['type']}\n{s['used']} / {s['max']} ({percent}%)",  
        "color": heat_color(percent)  
    })  
return out  

HTML = """
  
  
  
<meta charset="utf-8">  
<title>Wochenkalender – Auslastung (%)</title>  
<style>  
body { font-family: Arial, sans-serif; }  
.calendar { display:grid; grid-template-columns:80px repeat(5,1fr); }  
.header { text-align:center; font-weight:bold; padding:6px; }  
.day { position:relative; height:{{h}}px; border-left:1px solid #ccc; }  
.session {  
  position:absolute; left:5px; right:5px;  
  padding:4px; border-radius:4px;  
  font-size:11px; white-space:pre-line;  
}  
</style>  
  
  
Wochenkalender – Auslastung (%)  
  
{% for d in days %}{{d}}{% endfor %}  
11:00–22:00{% for d in days %}{% endfor %}  
  
{% for s in sessions %}
  
{{s.text}}  
  
{% endfor %}  
<script>  
document.querySelectorAll(".session").forEach(e=>{  
  document.getElementById("c"+e.dataset.day).appendChild(e);  
});  
</script>  
  
  
"""  
@app.route("/")
def main():
return render_template_string(
HTML,
days=DAYS,
sessions=prepare_sessions(),
h=time_to_px("22:00")
)
if name == "main":
port = int(os.environ.get("PORT", 10000))
app.run(host="0.0.0.0", port=port)
