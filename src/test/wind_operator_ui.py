#!/usr/bin/env python3
"""Browser-based operator UI for WindForcePlugin."""
import argparse
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

import msgpack
import zmq


INDEX_HTML = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Wind Operator</title>
<style>
:root {
  color-scheme: light;
  --bg: #f5f6f8;
  --panel: #ffffff;
  --ink: #18202a;
  --muted: #657080;
  --line: #d8dde5;
  --accent: #177245;
  --accent-strong: #0d5c35;
  --warn: #a8481c;
  --bad: #9e2635;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  background: var(--bg);
  color: var(--ink);
}
header {
  height: 54px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 18px;
  background: #202833;
  color: white;
  border-bottom: 1px solid #111820;
}
h1 { margin: 0; font-size: 18px; font-weight: 650; letter-spacing: 0; }
.header-status { display: flex; align-items: center; gap: 10px; font-size: 13px; color: #d8dee8; }
.dot { width: 10px; height: 10px; border-radius: 999px; background: var(--bad); }
.dot.ok { background: #39a969; }
main {
  display: grid;
  grid-template-columns: minmax(330px, 430px) minmax(460px, 1fr);
  gap: 16px;
  padding: 16px;
}
section {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 14px;
}
h2 { margin: 0 0 12px; font-size: 15px; font-weight: 650; }
.log-title { margin-top: 16px; justify-content: space-between; }
.log-title h2 { margin: 0; }
.grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }
.field { display: flex; flex-direction: column; gap: 6px; }
.field.full { grid-column: 1 / -1; }
label { font-size: 12px; color: var(--muted); }
.group-label { grid-column: 1 / -1; font-size: 12px; color: var(--muted); font-weight: 650; }
.inline-note { font-size: 12px; color: var(--muted); }
.formula {
  grid-column: 1 / -1;
  border: 1px solid var(--line);
  border-radius: 6px;
  background: #fbfcfd;
  padding: 9px 10px;
  font-size: 13px;
  color: var(--ink);
}
.formula strong { font-size: 15px; }
input[type="number"], input[type="text"] {
  height: 36px;
  border: 1px solid var(--line);
  border-radius: 6px;
  padding: 6px 8px;
  font-size: 14px;
  background: white;
  color: var(--ink);
}
input[type="range"] { width: 100%; }
.row { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
button {
  height: 36px;
  border: 1px solid var(--line);
  border-radius: 6px;
  padding: 0 12px;
  background: white;
  color: var(--ink);
  font-size: 14px;
  cursor: pointer;
}
button:hover { border-color: #9aa4b2; }
button.primary { background: var(--accent); color: white; border-color: var(--accent); }
button.primary:hover { background: var(--accent-strong); }
button.danger { color: white; background: var(--bad); border-color: var(--bad); }
button.toggle.active { background: #dcefe5; border-color: var(--accent); color: var(--accent-strong); }
.direction-pad {
  display: grid;
  grid-template-columns: repeat(3, 44px);
  grid-template-rows: repeat(3, 36px);
  gap: 6px;
  align-items: center;
  justify-content: center;
  margin-top: 4px;
}
.direction-pad button { padding: 0; }
.direction-pad .north { grid-column: 2; grid-row: 1; }
.direction-pad .west { grid-column: 1; grid-row: 2; }
.direction-pad .east { grid-column: 3; grid-row: 2; }
.direction-pad .south { grid-column: 2; grid-row: 3; }
.status-grid { display: grid; grid-template-columns: repeat(4, minmax(110px, 1fr)); gap: 10px; }
.metric {
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 10px;
  background: #fbfcfd;
  min-height: 74px;
}
.metric .label { font-size: 12px; color: var(--muted); }
.metric .value { margin-top: 6px; font-size: 22px; font-weight: 700; }
.metric .unit { font-size: 12px; color: var(--muted); margin-left: 3px; }
.log {
  height: 180px;
  overflow: auto;
  background: #121820;
  color: #d9e2ee;
  border-radius: 6px;
  padding: 10px;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 12px;
  line-height: 1.5;
  white-space: pre;
}
small { color: var(--muted); }
@media (max-width: 900px) {
  main { grid-template-columns: 1fr; }
  .status-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
</style>
</head>
<body>
<header>
  <h1>Wind Operator</h1>
  <div class="header-status"><span id="status-dot" class="dot"></span><span id="status-text">Waiting for plugin status</span></div>
</header>
<main>
  <section>
    <h2>Command</h2>
    <div class="grid">
      <div class="field">
        <label for="knots">Horizontal wind</label>
        <input id="knots" type="number" value="0" min="0" max="60" step="0.5">
      </div>
      <div class="field">
        <label for="wind-slider">Horizontal wind slider</label>
        <input id="wind-slider" type="range" min="0" max="60" value="0" step="0.5">
      </div>
      <div class="group-label">Direction</div>
      <div class="field">
        <label for="direction">Direction deg</label>
        <input id="direction" type="number" value="0" min="0" max="359" step="1">
      </div>
      <div class="field">
        <label for="direction-slider">Direction slider</label>
        <input id="direction-slider" type="range" min="0" max="359" value="0">
      </div>
      <div class="field full">
        <div class="direction-pad" aria-label="Direction cardinal buttons">
          <button class="north" data-dir="90" title="90 deg">N</button>
          <button class="west" data-dir="180" title="180 deg">W</button>
          <button class="east" data-dir="0" title="0 deg">E</button>
          <button class="south" data-dir="270" title="270 deg">S</button>
        </div>
        <div class="inline-note">0=E/+X, 90=N/+Y, 180=W/-X, 270=S/-Y</div>
      </div>
      <div class="field">
        <label for="ramp-start">Ramp start m</label>
        <input id="ramp-start" type="number" value="0" step="1">
      </div>
      <div class="field">
        <label for="ramp-end">Ramp end m</label>
        <input id="ramp-end" type="number" value="100" step="1">
      </div>
      <div class="field">
        <label for="drag">Drag coefficient</label>
        <input id="drag" type="number" value="1.1" step="0.1">
      </div>
      <div class="field">
        <label for="area">Reference area m2</label>
        <input id="area" type="number" value="0.12" step="0.01">
      </div>
      <div class="formula">Drag coefficient x reference area = <strong id="command-cda">0.132</strong> CdA</div>
      <div class="formula">Force = 0.5 x air density x CdA x relative speed^2, clamped by max force</div>
      <div class="field">
        <label for="max-force">Max force clamp N</label>
        <input id="max-force" type="number" value="80" step="1">
      </div>
    </div>
    <div class="row" style="margin-top: 14px;">
      <button id="send" class="primary">Send</button>
      <button id="live" class="toggle">Live</button>
      <button id="calm" class="danger">Zero Wind</button>
    </div>
  </section>
  <section>
    <h2>Status</h2>
    <div class="status-grid">
      <div class="metric"><div class="label">Altitude</div><div class="value"><span id="altitude">--</span><span class="unit">m</span></div></div>
      <div class="metric"><div class="label">Actual wind</div><div class="value"><span id="actual-wind">--</span><span class="unit">kt</span></div></div>
      <div class="metric"><div class="label">Target wind</div><div class="value"><span id="target-wind">--</span><span class="unit">kt</span></div></div>
      <div class="metric"><div class="label">Force</div><div class="value"><span id="force">--</span><span class="unit">N</span></div></div>
      <div class="metric"><div class="label">Direction</div><div class="value"><span id="status-direction">--</span><span class="unit">deg</span></div></div>
      <div class="metric"><div class="label">Relative speed</div><div class="value"><span id="relative-speed">--</span><span class="unit">m/s</span></div></div>
      <div class="metric"><div class="label">CdA</div><div class="value"><span id="cda">--</span></div></div>
      <div class="metric"><div class="label">Commands</div><div class="value"><span id="commands">--</span></div></div>
    </div>
    <div class="row log-title">
      <h2>Log</h2>
      <button id="save-log">Save Log</button>
    </div>
    <div id="log" class="log"></div>
  </section>
</main>
<script>
const $ = (id) => document.getElementById(id);
let liveMode = false;
let liveTimer = null;
let lastLiveLog = 0;

function numberValue(id) {
  const raw = $(id).value;
  if (raw === "") return null;
  const value = Number(raw);
  return Number.isFinite(value) ? value : null;
}

function commandPayload() {
  const payload = {
    speed_knots: numberValue("knots") || 0,
    direction_deg: numberValue("direction") || 0,
    ramp_start_altitude: numberValue("ramp-start") || 0,
    ramp_end_altitude: numberValue("ramp-end") || 0
  };
  const drag = numberValue("drag");
  const area = numberValue("area");
  const maxForce = numberValue("max-force");
  if (drag !== null) payload.drag_coefficient = drag;
  if (area !== null) payload.reference_area = area;
  if (maxForce !== null) payload.max_force = maxForce;
  return payload;
}

function log(line) {
  const box = $("log");
  const stamp = new Date().toLocaleTimeString();
  box.textContent += `[${stamp}] ${line}\n`;
  box.scrollTop = box.scrollHeight;
}

function logFilename() {
  const stamp = new Date().toISOString().replace(/[:.]/g, "-");
  return `wind_operator_log_${stamp}.txt`;
}

function saveLog() {
  const content = $("log").textContent || "";
  const blob = new Blob([content], {type: "text/plain;charset=utf-8"});
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = logFilename();
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

async function sendCommand(payload = commandPayload(), options = {}) {
  const response = await fetch("/api/command", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(payload)
  });
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || "command failed");
  if (!options.quiet) {
    log(`sent wind=${payload.speed_knots}kt dir=${payload.direction_deg}deg ramp=${payload.ramp_start_altitude}..${payload.ramp_end_altitude}m`);
  }
}

function scheduleLiveSend() {
  if (!liveMode) return;
  clearTimeout(liveTimer);
  liveTimer = setTimeout(() => {
    sendCommand(commandPayload(), {quiet: true})
      .then(() => {
        const now = Date.now();
        if (now - lastLiveLog > 1000) {
          const p = commandPayload();
          log(`live wind=${p.speed_knots}kt dir=${p.direction_deg}deg ramp=${p.ramp_start_altitude}..${p.ramp_end_altitude}m`);
          lastLiveLog = now;
        }
      })
      .catch((err) => log(`error: ${err.message}`));
  }, 120);
}

function toggleLive() {
  liveMode = !liveMode;
  $("live").classList.toggle("active", liveMode);
  log(liveMode ? "live mode on" : "live mode off");
  if (liveMode) scheduleLiveSend();
}

function setDirection(value) {
  const normalized = ((Number(value) % 360) + 360) % 360;
  $("direction").value = normalized;
  $("direction-slider").value = normalized;
  scheduleLiveSend();
}

function setWind(value) {
  const wind = Math.max(Number(value) || 0, 0);
  $("knots").value = wind;
  $("wind-slider").value = Math.min(wind, Number($("wind-slider").max));
  scheduleLiveSend();
}

function updateCommandCda() {
  const drag = numberValue("drag") || 0;
  const area = numberValue("area") || 0;
  $("command-cda").textContent = (drag * area).toFixed(3);
  scheduleLiveSend();
}

function handleCommandInput() {
  scheduleLiveSend();
}

function fmt(value, digits = 1) {
  return typeof value === "number" && Number.isFinite(value) ? value.toFixed(digits) : "--";
}

async function pollStatus() {
  try {
    const response = await fetch("/api/status");
    const status = await response.json();
    const age = status.age_seconds;
    const fresh = age !== null && age < 3;
    $("status-dot").classList.toggle("ok", fresh);
    $("status-text").textContent = fresh ? "Plugin status live" : "Waiting for plugin status";
    if (!status.data) return;
    const d = status.data;
    $("altitude").textContent = fmt(d.altitude_m, 1);
    $("actual-wind").textContent = fmt(d.actual_wind_knots, 1);
    $("target-wind").textContent = fmt(d.target_wind_knots, 1);
    $("force").textContent = fmt(d.force_n, 1);
    $("status-direction").textContent = fmt(d.direction_deg, 0);
    $("relative-speed").textContent = fmt(d.relative_speed_mps, 1);
    $("cda").textContent = fmt((d.drag_coefficient || 0) * (d.reference_area || 0), 3);
    $("commands").textContent = d.received_control_count ?? "--";
  } catch (err) {
    $("status-dot").classList.remove("ok");
    $("status-text").textContent = "UI server not responding";
  }
}

$("send").addEventListener("click", () => sendCommand().catch((err) => log(`error: ${err.message}`)));
$("save-log").addEventListener("click", saveLog);
$("live").addEventListener("click", toggleLive);
$("calm").addEventListener("click", () => {
  setWind(0);
  sendCommand().catch((err) => log(`error: ${err.message}`));
});
$("knots").addEventListener("input", (event) => setWind(event.target.value));
$("wind-slider").addEventListener("input", (event) => setWind(event.target.value));
$("direction").addEventListener("input", (event) => setDirection(event.target.value));
$("direction-slider").addEventListener("input", (event) => setDirection(event.target.value));
$("ramp-start").addEventListener("input", handleCommandInput);
$("ramp-end").addEventListener("input", handleCommandInput);
$("drag").addEventListener("input", updateCommandCda);
$("area").addEventListener("input", updateCommandCda);
$("max-force").addEventListener("input", handleCommandInput);
document.querySelectorAll("[data-dir]").forEach((button) => {
  button.addEventListener("click", () => setDirection(button.dataset.dir));
});

setInterval(pollStatus, 500);
updateCommandCda();
pollStatus();
log("operator UI ready");
</script>
</body>
</html>
"""


class WindBridge:
    def __init__(self, control_endpoint, control_topic, status_endpoint, status_topic):
        self.control_endpoint = control_endpoint
        self.control_topic = control_topic.encode("utf-8")
        self.status_endpoint = status_endpoint
        self.status_topic = status_topic.encode("utf-8")
        self.context = zmq.Context()
        self.publisher = self.context.socket(zmq.PUB)
        self.publisher.bind(control_endpoint)
        self.status = None
        self.status_time = None
        self.status_lock = threading.Lock()
        self.running = True
        self.status_thread = threading.Thread(target=self._status_loop, daemon=True)
        self.status_thread.start()
        time.sleep(0.5)

    def send_command(self, command):
        payload = msgpack.packb(command, use_bin_type=True)
        # Send a short burst to reduce PUB/SUB first-message loss for manual clicks.
        for _ in range(3):
            self.publisher.send_multipart([self.control_topic, payload])
            time.sleep(0.03)

    def latest_status(self):
        with self.status_lock:
            if self.status_time is None:
                return {"data": None, "age_seconds": None}
            return {
                "data": self.status,
                "age_seconds": time.time() - self.status_time,
            }

    def _status_loop(self):
        subscriber = self.context.socket(zmq.SUB)
        subscriber.setsockopt(zmq.SUBSCRIBE, self.status_topic)
        subscriber.connect(self.status_endpoint)
        poller = zmq.Poller()
        poller.register(subscriber, zmq.POLLIN)
        while self.running:
            events = dict(poller.poll(250))
            if subscriber not in events:
                continue
            try:
                parts = subscriber.recv_multipart(zmq.NOBLOCK)
                if len(parts) != 2:
                    continue
                data = msgpack.unpackb(parts[1], raw=False)
                with self.status_lock:
                    self.status = data
                    self.status_time = time.time()
            except Exception:
                continue
        subscriber.close(0)

    def close(self):
        self.running = False
        self.publisher.close(0)
        self.context.term()


def parse_args():
    parser = argparse.ArgumentParser(description="Operator web UI for WindForcePlugin.")
    parser.add_argument("--listen-host", default="0.0.0.0", help="HTTP listen host")
    parser.add_argument("--listen-port", type=int, default=8088, help="HTTP listen port")
    parser.add_argument("--control-endpoint", default="tcp://127.0.0.1:5570")
    parser.add_argument("--control-topic", default="wind/control")
    parser.add_argument("--status-endpoint", default="tcp://127.0.0.1:5571")
    parser.add_argument("--status-topic", default="wind/status")
    return parser.parse_args()


def make_handler(bridge):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            return

        def _send_json(self, data, status=200):
            body = json.dumps(data).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _send_html(self):
            body = INDEX_HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            path = urlparse(self.path).path
            if path == "/" or path == "/index.html":
                self._send_html()
            elif path == "/api/status":
                self._send_json(bridge.latest_status())
            else:
                self._send_json({"error": "not found"}, 404)

        def do_POST(self):
            path = urlparse(self.path).path
            if path != "/api/command":
                self._send_json({"error": "not found"}, 404)
                return
            length = int(self.headers.get("Content-Length", "0"))
            try:
                command = json.loads(self.rfile.read(length).decode("utf-8"))
                bridge.send_command(validate_command(command))
                self._send_json({"ok": True})
            except Exception as exc:
                self._send_json({"error": str(exc)}, 400)

    return Handler


def validate_command(command):
    required = ["speed_knots", "direction_deg", "ramp_start_altitude", "ramp_end_altitude"]
    clean = {}
    for key in required:
        clean[key] = float(command[key])
    for key in ["drag_coefficient", "reference_area", "max_force"]:
        if key in command and command[key] is not None:
            clean[key] = float(command[key])
    return clean


def main():
    args = parse_args()
    bridge = WindBridge(
        args.control_endpoint,
        args.control_topic,
        args.status_endpoint,
        args.status_topic,
    )
    server = ThreadingHTTPServer((args.listen_host, args.listen_port), make_handler(bridge))
    print(f"Wind operator UI: http://127.0.0.1:{args.listen_port}")
    print(f"Control: {args.control_endpoint} topic='{args.control_topic}'")
    print(f"Status:  {args.status_endpoint} topic='{args.status_topic}'")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping wind operator UI.")
    finally:
        server.server_close()
        bridge.close()


if __name__ == "__main__":
    main()
