import os
import json
import ssl
from urllib.request import urlopen, Request
from urllib.parse import urlencode
from flask import Flask, render_template_string

app = Flask(__name__)

API_BASE = "https://oana.asdf.ooo/api/collections/sessions/records"

def fetch_raw_sessions():
    params = {
        "page": 1,
        "perPage": 1000,
        "skipTotal": 1,
        "sort": "event_date,start",
        "filter": "is_deleted=false && source='coremanager' && source_category_id=4",
    }

    url = API_BASE + "?" + urlencode(params)

    req = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json",
        },
    )

    context = ssl.create_default_context()
    with urlopen(req, timeout=30, context=context) as response:
        data = json.loads(response.read().decode("utf-8"))

    return data.get("items", [])


HTML = """
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>DEBUG – Raw Session Dump</title>
<style>
body { font-family: monospace; white-space: pre; }
h2 { font-family: Arial, sans-serif; }
.entry { margin-bottom: 20px; border-bottom: 1px solid #ccc; padding-bottom: 10px; }
</style>
</head>
<body>

<h2>DEBUG – Sessions vom /sessions-Endpoint</h2>
<p>Anzahl Sessions: {{ sessions|length }}</p>

{% for s in sessions %}
<div class="entry">
event_date: {{ s.event_date }}
start: {{ s.start }}
end: {{ s.end }}
title: {{ s.title }}
participants: {{ s.participants_count }} / {{ s.max_participants }}
</div>
{% endfor %}

</body>
</html>
"""

@app.route("/")
def debug():
    sessions = fetch_raw_sessions()
    return render_template_string(HTML, sessions=sessions)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
