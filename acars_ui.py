#!/usr/bin/env python3
#
# acars-pi-dashboard — acars_ui.py
# Real-time ACARS web dashboard via Flask + SQLite (WAL mode)
#
# Project : [https://github.com/anthonyborriello/acars-pi-dashboard](https://github.com/anthonyborriello/acars-pi-dashboard)
# Author  : Antonio Borriello
# License : MIT
#

from flask import Flask, render_template_string, jsonify, request
import sqlite3
import json
import os
import glob
from datetime import datetime

app = Flask(__name__)
LOGS_DIR = "/home/pi/acars_logs"

HTML = r"""
<!DOCTYPE html>
<html>
<head>
<title>ACARS LIVE</title>
<style>
:root {
    --bg:    #000000;
    --fg:    #00ff99;
    --dim:   #aaaaaa;
    --red:   #ff5555;
    --blue:  #00ccff;
    --white: #ffffff;
}
* { box-sizing:border-box; margin:0; padding:0; }
body { background:var(--bg); color:var(--fg); font-family:'Courier New',monospace; font-size:13px; padding:12px; }
h2   { color:var(--fg); font-size:16px; letter-spacing:2px; margin-bottom:10px; }

.stats  { color:var(--dim); font-size:0.85em; margin-bottom:8px; }
#status          { color:var(--dim); font-size:0.78em; min-height:1em; margin-bottom:6px; }
#status.error    { color:var(--red); animation:blink 1.2s step-start infinite; }
@keyframes blink { 50%{opacity:0;} }

.toolbar { display:flex; gap:10px; align-items:center; flex-wrap:wrap; margin-bottom:8px; }
.toolbar select, .toolbar input, .toolbar button, .toolbar a.btn {
    background:#111; color:var(--fg); border:1px solid #333;
    padding:3px 7px; font-family:monospace; font-size:12px;
    text-decoration:none; display:inline-block;
}
.toolbar button        { cursor:pointer; }
.toolbar button:hover,
.toolbar a.btn:hover   { background:#222; }
.toolbar a.reset       { color:var(--red); font-size:12px; text-decoration:none; margin-left:4px; }

.sq-bar {
    display:flex; align-items:center; gap:10px;
    border:1px solid #1a2a1a; background:#050f08;
    padding:4px 8px; margin-bottom:8px; font-size:12px; color:#2a6a3a;
}
.sq-bar .sq-count { color:#3aaa5a; font-weight:bold; font-size:13px; min-width:30px; }
.sq-bar button {
    background:#0a1a0a; color:#3aaa5a; border:1px solid #1a4a2a;
    padding:2px 8px; font-family:monospace; font-size:11px; cursor:pointer;
    min-width:60px; text-align:center;
}
.sq-bar button:hover { background:#112211; }

table     { width:100%; border-collapse:collapse; }
thead th  {
    background:#0f0f0f; border-bottom:1px solid #333;
    padding:4px 6px; text-align:left; color:var(--dim);
    font-size:11px; letter-spacing:.5px; position:sticky; top:0;
}
tbody tr td          { border-bottom:1px solid #151515; padding:3px 6px; vertical-align:top; }
tbody tr:hover td    { background:#0f1a13; }

.complete td { color:var(--white); }
.ads  td     { color:var(--blue); }
.err  td     { color:var(--red); }
.sq   td     { color:#2a4a3a; font-size:11px; }
.sq.err td   { color:var(--red); }
.other td    { color:#777; }

.telemetry   { color:var(--blue); white-space:nowrap; }

tr.sq                { display:none; }
tr.sq.sq-show        { display:table-row; }

.new { animation:flash .8s ease-out; }
@keyframes flash { 0%{background:#003322;} 100%{background:transparent;} }

.badge {
    display:inline-block; padding:0 4px; border-radius:2px;
    font-size:10px; letter-spacing:.5px; font-weight:bold;
    margin-left:4px; vertical-align:middle;
    background:#1a2a1a; border:1px solid #336633; color:#88cc88;
}

/* Adaptive BELL label */
.bell-label {
    font-size: 9px;
    text-transform: lowercase;
    color: currentColor;
    background: rgba(255, 255, 255, 0.1);
    border: 1px solid currentColor;
    padding: 0px 3px;
    border-radius: 2px;
    vertical-align: middle;
    font-weight: bold;
    margin: 0 2px;
    font-family: sans-serif;
    opacity: 0.9;
}

tr.detail-row      { display:none; }
tr.detail-row.open { display:table-row; }
tr.detail-row td   {
    background:#050f08; border-bottom:1px solid #1a2a1a;
    padding:8px 16px; font-size:11px;
}
tr.has-detail      { cursor:pointer; }
tr.has-detail td:first-child::before {
    content:"▶ "; color:#2a4a3a; font-size:10px;
}
tr.has-detail.expanded td:first-child::before {
    content:"▼ "; color:#00ff99;
}

.detail-tree { display:flex; flex-direction:column; gap:4px; }
.detail-node { margin-left:0; }
.detail-children {
    margin-left:18px;
    border-left:1px solid #16301f;
    padding-left:10px;
    margin-top:3px;
}
.detail-group { color:#00ff99; font-size:10px; letter-spacing:1px; margin-top:6px; margin-bottom:2px; }
.detail-array { color:#66bb88; font-size:10px; letter-spacing:.5px; margin-top:4px; margin-bottom:2px; }
.detail-leaf { display:grid; grid-template-columns:max-content 1fr; gap:3px 16px; }
.detail-key { color:#3aaa5a; white-space:nowrap; padding-left:0; }
.detail-val { color:#aaaaaa; word-break:break-all; }

.message-text {
    font-family:'Courier New', monospace;
    font-size:11px;
    line-height:1.35em;
    white-space:pre-wrap;
    word-break:normal;
    overflow-wrap:normal;
    overflow-x:auto;
    color:#cccccc;
    background:#08110b;
    border:1px solid #16301f;
    padding:6px 10px;
    margin-left:0;
}
</style>
</head>
<body>
<h2>✈ ACARS LIVE DASHBOARD</h2>

<div class="stats">
    ⊞ <span id="current_day">{{ current }}</span> &nbsp;|&nbsp;
    ✉ <span id="total">{{ total }}</span> messages &nbsp;|&nbsp;
    ✈ <span id="aircraft">{{ aircraft }}</span> aircraft
</div>
<div id="status"></div>

<div class="toolbar">
    <select id="day-picker" onchange="location.href='/?day='+this.value">
        {% for d in days %}
        <option value="{{ d }}" {{ 'selected' if d == current else '' }}>{{ d }}</option>
        {% endfor %}
    </select>

    <form method="get" style="display:contents">
        <input type="hidden" name="day" value="{{ current }}">
        <input type="text" name="tail"   placeholder="Tail"   value="{{ filter_tail }}"   style="width:100px">
        <input type="text" name="flight" placeholder="Flight" value="{{ filter_flight }}" style="width:100px">
        <select name="label">
            <option value="">Label</option>
            {% for l in labels %}
            <option value="{{ l }}" {{ 'selected' if l == filter_label else '' }}>{{ l }}</option>
            {% endfor %}
        </select>
        <select name="assstat">
            <option value="">Status</option>
            <option value="complete"    {{ 'selected' if filter_assstat == 'complete'    else '' }}>FULL</option>
            <option value="in progress" {{ 'selected' if filter_assstat == 'in progress' else '' }}>In progress</option>
        </select>
        <button type="submit">🔍 Filter</button>
        <a href="/?day={{ current }}" class="reset">✖ Reset</a>
    </form>
    <a href="/raw?day={{ current }}" class="btn">📄 Raw Data</a>
    <button id="snd-btn" onclick="toggleSound()" style="border-color:#555;color:#555;">🔔 Sound</button>
    <a href="https://github.com/anthonyborriello/acars-pi-dashboard"
       class="btn" target="_blank" rel="noopener noreferrer">GitHub ↗</a>
</div>

<div class="sq-bar">
    ◎ SQ squitter &nbsp; <span class="sq-count" id="sq-count">{{ sq_count }}</span>
    <button id="sq-toggle" onclick="toggleSQ()">View</button>
</div>

<table>
<thead>
<tr>
    <th>Time</th><th>Freq</th><th>Label</th><th>Tail</th><th>Flight</th>
    <th>Blk</th><th>Msg#</th><th>Status</th><th>Text</th>
    <th>Lat</th><th>Lon</th><th>Alt</th><th>(GS/TRK/VS)</th>
</tr>
</thead>
<tbody id="msgbody">
{% for m in messages %}
<tr class="{{ m['cls'] }}{% if m['detail'] %} has-detail{% endif %}"
    {% if m['detail'] %}onclick="toggleDetail(this)" data-detail="{{ m['detail'] | tojson | forceescape }}"{% endif %}>
    <td>{{ m['ts'] }}</td>
    <td>{{ m['freq'] }}</td>
    <td style="white-space:nowrap;">
        {{ m['label'] }}{% if m['sublabel'] %}<span class="badge">{{ m['sublabel'] }}</span>{% endif %}
    </td>
    <td>{{ m['tail'] }}</td>
    <td>{{ m['flight'] }}</td>
    <td>{{ m['block_id'] }}</td>
    <td>{{ m['msgno'] }}</td>
    <td>{{ m['status'] }}</td>
    <td style="max-width:550px;word-break:break-all;">{{ m['text_original'] | safe }}</td>
    <td>{{ m['lat'] if m['lat'] is not none else '' }}</td>
    <td>{{ m['lon'] if m['lon'] is not none else '' }}</td>
    <td>{{ m['alt'] if m['alt'] is not none else '' }}</td>
    <td class="telemetry">{{ m['extra'] }}</td>
</tr>
{% if m['detail'] %}
<tr class="detail-row">
    <td colspan="13"></td>
</tr>
{% endif %}
{% endfor %}
</tbody>
</table>

<script>
var lastId     = {{ last_id }};
var currentDay = "{{ current }}";
var isToday    = (currentDay === new Date().toISOString().slice(0,10).replace(/-/g,"_"));
var sqVisible  = false;
var soundOn    = false;
var audioCtx   = null;

function getAudioCtx() {
    if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    return audioCtx;
}

function toggleSound() {
    soundOn = !soundOn;
    var btn = document.getElementById("snd-btn");
    btn.style.color       = soundOn ? "#00ff99" : "#555";
    btn.style.borderColor = soundOn ? "#336633" : "#555";
}

function beep(freq, dur, type, freqEnd) {
    if (!soundOn) return;
    var c = getAudioCtx(), o = c.createOscillator(), g = c.createGain();
    o.connect(g); g.connect(c.destination);
    o.type = type;
    o.frequency.setValueAtTime(freq, c.currentTime);
    if (freqEnd) o.frequency.linearRampToValueAtTime(freqEnd, c.currentTime + dur/1000);
    g.gain.setValueAtTime(0.3, c.currentTime);
    g.gain.exponentialRampToValueAtTime(0.001, c.currentTime + dur/1000);
    o.start(c.currentTime);
    o.stop(c.currentTime + dur/1000 + 0.05);
}

function toggleSQ() {
    sqVisible = !sqVisible;
    document.querySelectorAll("tr.sq").forEach(function(tr) {
        tr.classList.toggle("sq-show", sqVisible);
    });
    document.getElementById("sq-toggle").textContent = sqVisible ? "Hide" : "View";
}

function escapeHtml(v) {
    return String(v)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/\"/g, "&quot;")
        .replace(/'/g, "&#39;");
}

function isPlainObject(v) { return v !== null && typeof v === "object" && !Array.isArray(v); }

function renderNode(key, value) {
    var html = "";
    if (key === "text" && isPlainObject(value) && "text" in value) {
        html += '<div class="detail-node"><div class="detail-group">◈ ' + escapeHtml(key) + '</div>';
        html += '<div class="detail-children"><div class="message-text">' + value.text + '</div></div></div>';
        return html;
    }
    if (Array.isArray(value)) {
        html += '<div class="detail-node"><div class="detail-array">— ' + escapeHtml(key) + '</div><div class="detail-children">';
        value.forEach(function(item) {
            if (isPlainObject(item)) {
                Object.keys(item).forEach(function(k) { html += renderNode(k, item[k]); });
            } else {
                html += '<div class="detail-leaf"><div class="detail-key">' + escapeHtml(item) + '</div><div class="detail-val"></div></div>';
            }
        });
        html += '</div></div>';
        return html;
    }
    if (isPlainObject(value)) {
        html += '<div class="detail-node"><div class="detail-group">◈ ' + escapeHtml(key) + '</div><div class="detail-children">';
        Object.keys(value).forEach(function(childKey) { html += renderNode(childKey, value[childKey]); });
        html += '</div></div>';
        return html;
    }
    return '<div class="detail-leaf"><div class="detail-key">' + escapeHtml(key) + '</div><div class="detail-val">' + escapeHtml(value) + '</div></div>';
}

function buildDetailHTML(detail) {
    if (!detail || typeof detail !== "object") return "";
    var html = '<div class="detail-tree">';
    Object.keys(detail).forEach(function(key) { html += renderNode(key, detail[key]); });
    return html + '</div>';
}

function toggleDetail(tr) {
    var detailTr = tr.nextElementSibling;
    if (!detailTr || !detailTr.classList.contains("detail-row")) return;
    var isOpen = detailTr.classList.contains("open");
    if (!isOpen && !detailTr.querySelector(".detail-tree")) {
        var detail = tr.getAttribute("data-detail");
        try { detail = JSON.parse(detail); } catch(e) { detail = null; }
        detailTr.querySelector("td").innerHTML = buildDetailHTML(detail);
    }
    detailTr.classList.toggle("open", !isOpen);
    tr.classList.toggle("expanded", !isOpen);
}

function addRow(m) {
    var tbody = document.getElementById("msgbody");
    var tr    = document.createElement("tr");
    var cls   = m.cls + " new";
    if (m.label === "SQ" && sqVisible) cls += " sq-show";
    if (m.detail) cls += " has-detail";
    tr.className = cls;
    if (m.detail) {
        tr.setAttribute("data-detail", JSON.stringify(m.detail));
        tr.onclick = function() { toggleDetail(this); };
    }
    tr.innerHTML =
        "<td>" + (m.ts || "") + "</td>" +
        "<td>" + (m.freq || "") + "</td>" +
        "<td style='white-space:nowrap;'>" + (m.label || "") + (m.sublabel ? ' <span class="badge">' + m.sublabel + '</span>' : "") + "</td>" +
        "<td>" + (m.tail || "") + "</td>" +
        "<td>" + (m.flight || "") + "</td>" +
        "<td>" + (m.block_id || "") + "</td>" +
        "<td>" + (m.msgno || "") + "</td>" +
        "<td>" + (m.status || "") + "</td>" +
        "<td style='max-width:550px;word-break:break-all;'>" + (m.text_original || "") + "</td>" +
        "<td>" + (m.lat !== null ? m.lat : "") + "</td>" +
        "<td>" + (m.lon !== null ? m.lon : "") + "</td>" +
        "<td>" + (m.alt !== null ? m.alt : "") + "</td>" +
        "<td class='telemetry'>" + (m.extra || "") + "</td>";
    tbody.insertBefore(tr, tbody.firstChild);

    if (m.detail) {
        var dtr = document.createElement("tr");
        dtr.className = "detail-row";
        dtr.innerHTML = "<td colspan='13'></td>";
        tbody.insertBefore(dtr, tr.nextSibling);
    }

    if (m.label === "SQ") beep(300, 80, "sine", 120);
    else { beep(800, 90, "triangle"); setTimeout(function(){ beep(800, 90, "triangle"); }, 130); }
}

function setStatus(msg, isErr) {
    var el = document.getElementById("status");
    el.textContent = msg;
    el.className   = isErr ? "error" : "";
}

function poll() {
    if (!isToday) return;
    fetch("/api/new?day=" + currentDay + "&last_id=" + lastId)
        .then(function(r) { if (!r.ok) throw new Error("HTTP " + r.status); return r.json(); })
        .then(function(data) {
            data.messages.forEach(addRow);
            if (data.messages.length) lastId = data.last_id;
            document.getElementById("total").textContent    = data.total;
            document.getElementById("aircraft").textContent = data.aircraft;
            document.getElementById("sq-count").textContent = data.sq;
            setStatus("updated: " + new Date().toLocaleTimeString(), false);
        })
        .catch(function() { setStatus("⚠ connection lost — retrying…", true); });
}

if (isToday) setInterval(poll, 5000);
</script>
</body>
</html>
"""

EXCLUDED_FROM_DETAIL = {
    "freq", "label", "tail", "flight", "assstat", "text", "error",
    "block_id", "msgno", "ack", "channel", "timestamp",
    "station_id", "app", "sublabel"
}

def get_available_days():
    files = sorted(glob.glob(os.path.join(LOGS_DIR, "acars_*.db")), reverse=True)
    return [os.path.basename(f).replace("acars_", "").replace(".db", "") for f in files]

def enrich(m):
    label   = m.get("label", "")
    assstat = m.get("assstat", "")
    error   = m.get("error", 0)
    m.update(sublabel="", lat=None, lon=None, alt=None, extra="", block_id="", msgno="", detail=None)

    try:
        raw = m.get("raw", "{}")
        raw = json.loads(raw) if isinstance(raw, str) else raw
    except Exception:
        raw = {}

    m["block_id"] = raw.get("block_id", "")
    m["msgno"]    = raw.get("msgno", "")
    if label == "H1":
        m["sublabel"] = raw.get("sublabel", "")

    # Handle the text and replace BELL character with styled span
    try:
        raw_text = raw.get("text")
        if not isinstance(raw_text, str):
            raw_text = m.get("text", "")

        if isinstance(raw_text, str):
            # Replace BELL control char with adaptive styled label
            m["text_original"] = raw_text.replace('\x07', '<span class="bell-label">bell</span>')
        else:
            m["text_original"] = ""
    except Exception:
        m["text_original"] = ""

    # ADS-C Decoding
    try:
        for tag in raw.get("libacars", {}).get("arinc622", {}).get("adsc", {}).get("tags", []):
            report = tag.get("basic_report")
            if report and "lat" in report:
                m["lat"], m["lon"] = round(float(report["lat"]), 5), round(float(report["lon"]), 5)
                m["alt"] = report.get("alt")
            if "earth_ref_data" in tag:
                erd = tag["earth_ref_data"]
                gs, trk, vspd = erd.get("gnd_spd_kts"), erd.get("true_trk_deg"), erd.get("vspd_ftmin")
                if gs is not None:
                    res = f"{int(gs)} {int(trk)}"
                    if vspd is not None:
                        res += f" {int(vspd)}ft/min" if abs(vspd) > 150 else " 0"
                    m["extra"] = res
                break
    except Exception: pass

    # Prepare detailed view
    try:
        detail = {}
        if m.get("text_original"): detail["text"] = {"text": m["text_original"]}
        if "libacars" in raw: detail["libacars"] = raw["libacars"]

        metadata = {k: v for k, v in raw.items() if k not in EXCLUDED_FROM_DETAIL and k not in ("level", "noise", "libacars")}
        if metadata: detail["metadata"] = metadata

        signal = {k: raw[k] for k in ("level", "noise") if k in raw}
        if signal: detail["signal"] = signal
        m["detail"] = detail if detail else None
    except Exception: pass

    if label == "SQ": m["cls"] = "sq err" if error else "sq"
    elif m["lat"] is not None: m["cls"] = "ads"
    elif assstat == "complete": m["cls"] = "complete"
    elif error: m["cls"] = "err"
    else: m["cls"] = "other"

    m["status"] = {"in progress": "[...]", "out of sequence": "[OOS]", "complete": "[FULL]"}.get(assstat, "")
    return m

def db_connect(day):
    path = os.path.join(LOGS_DIR, f"acars_{day}.db")
    if not os.path.exists(path): return None
    conn = sqlite3.connect(path); conn.row_factory = sqlite3.Row
    return conn

def get_messages(day, tail="", flight="", label="", assstat=""):
    conn = db_connect(day)
    if not conn: return [], 0
    q, p = "SELECT * FROM messages WHERE 1=1", []
    if tail:   q += " AND tail LIKE ?";   p.append(f"%{tail}%")
    if flight: q += " AND flight LIKE ?"; p.append(f"%{flight}%")
    if label:  q += " AND label = ?";     p.append(label)
    if assstat: q += " AND assstat = ?";   p.append(assstat)
    q += " ORDER BY ts DESC"
    rows = conn.execute(q, p).fetchall()
    last = conn.execute("SELECT MAX(id) FROM messages").fetchone()[0] or 0
    conn.close()
    return [enrich(dict(r)) for r in rows], last

def get_stats(conn):
    total = conn.execute("SELECT COUNT(*) FROM messages WHERE label != 'SQ'").fetchone()[0]
    aircraft = conn.execute("SELECT COUNT(DISTINCT tail) FROM messages WHERE label != 'SQ' AND tail != ''").fetchone()[0]
    sq = conn.execute("SELECT COUNT(*) FROM messages WHERE label = 'SQ'").fetchone()[0]
    return total, aircraft, sq

def get_labels(day):
    conn = db_connect(day)
    if not conn: return []
    rows = conn.execute("SELECT DISTINCT label FROM messages ORDER BY label").fetchall()
    conn.close()
    return [r[0] for r in rows]

@app.route("/")
def index():
    days = get_available_days()
    day = request.args.get("day", datetime.now().strftime("%Y_%m_%d"))
    msgs, last_id = get_messages(day, request.args.get("tail", ""), request.args.get("flight", ""), request.args.get("label", ""), request.args.get("assstat", ""))
    conn = db_connect(day)
    total, aircraft, sq_count = get_stats(conn) if conn else (0, 0, 0)
    if conn: conn.close()
    return render_template_string(HTML, messages=msgs, days=days, current=day, total=total, aircraft=aircraft, sq_count=sq_count, labels=get_labels(day), last_id=last_id, filter_tail=request.args.get("tail", ""), filter_flight=request.args.get("flight", ""), filter_label=request.args.get("label", ""), filter_assstat=request.args.get("assstat", ""))

@app.route("/api/new")
def api_new():
    day = request.args.get("day", datetime.now().strftime("%Y_%m_%d"))
    conn = db_connect(day)
    if not conn: return jsonify({"messages": [], "last_id": 0, "total": 0, "aircraft": 0, "sq": 0})
    last_id = int(request.args.get("last_id", 0))
    rows = conn.execute("SELECT * FROM messages WHERE id > ? ORDER BY id ASC", (last_id,)).fetchall()
    new_last = conn.execute("SELECT MAX(id) FROM messages").fetchone()[0] or last_id
    total, aircraft, sq = get_stats(conn); conn.close()
    return jsonify({"messages": [enrich(dict(r)) for r in rows], "last_id": new_last, "total": total, "aircraft": aircraft, "sq": sq})

@app.route("/raw")
def raw():
    day = request.args.get("day", datetime.now().strftime("%Y_%m_%d"))
    limit = min(int(request.args.get("limit", 1000)), 5000)
    conn = db_connect(day)
    if not conn: return jsonify({"error": "No DB"}), 404
    rows = conn.execute("SELECT * FROM messages ORDER BY ts DESC LIMIT ?", (limit,)).fetchall(); conn.close()
    result = []
    for r in rows:
        d = dict(r)
        try: d["raw"] = json.loads(d["raw"])
        except: pass
        result.append(d)
    return jsonify(result)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
