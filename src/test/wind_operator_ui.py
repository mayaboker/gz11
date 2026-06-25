#!/usr/bin/env python3
"""Browser-based operator UI for WindForcePlugin."""
import argparse
import errno
import json
import socketserver
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlparse

import msgpack
import zmq


class ThreadingHTTPServer(socketserver.ThreadingMixIn, HTTPServer):
    daemon_threads = True


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
button.with-icon { display: inline-flex; align-items: center; gap: 7px; }
button svg { width: 16px; height: 16px; stroke: currentColor; fill: none; stroke-width: 2; stroke-linecap: round; stroke-linejoin: round; flex: 0 0 auto; }
button svg.fill-icon { fill: currentColor; stroke: none; }
button.primary { background: var(--accent); color: white; border-color: var(--accent); }
button.primary:hover { background: var(--accent-strong); }
button.danger { color: white; background: var(--bad); border-color: var(--bad); }
button.toggle.active { background: #dcefe5; border-color: var(--accent); color: var(--accent-strong); }
button.recording { background: #fff1f2; border-color: var(--bad); color: var(--bad); }
.scenario-status { font-size: 12px; color: var(--muted); min-height: 18px; }
.direction-dial-wrap { display: flex; justify-content: center; margin-top: 2px; }
.direction-dial {
  position: relative;
  width: 168px;
  height: 168px;
  border: 1px solid var(--line);
  border-radius: 50%;
  background: radial-gradient(circle at center, #ffffff 0 34%, #eef3f0 35% 36%, #fbfcfd 37% 100%);
  touch-action: none;
  cursor: pointer;
  user-select: none;
}
.direction-dial:focus { outline: 2px solid var(--accent); outline-offset: 3px; }
.direction-dial::before, .direction-dial::after {
  content: "";
  position: absolute;
  background: #d8dde5;
  left: 50%;
  top: 50%;
  transform: translate(-50%, -50%);
}
.direction-dial::before { width: 1px; height: 132px; }
.direction-dial::after { width: 132px; height: 1px; }
.dial-label {
  position: absolute;
  width: 28px;
  height: 24px;
  border: 0;
  padding: 0;
  background: transparent;
  color: var(--muted);
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
}
.dial-label:hover { color: var(--accent-strong); }
.dial-label.north { left: 70px; top: 5px; }
.dial-label.east { right: 3px; top: 72px; }
.dial-label.south { left: 70px; bottom: 5px; }
.dial-label.west { left: 3px; top: 72px; }
.dial-needle {
  position: absolute;
  left: 50%;
  top: 50%;
  width: 3px;
  height: 58px;
  background: var(--accent);
  border-radius: 999px;
  transform-origin: 50% 100%;
  transform: translate(-50%, -100%) rotate(0deg);
  pointer-events: none;
}
.dial-handle {
  position: absolute;
  left: 50%;
  top: 14px;
  width: 20px;
  height: 20px;
  border: 3px solid white;
  border-radius: 50%;
  background: var(--accent);
  box-shadow: 0 2px 8px rgba(24, 32, 42, 0.25);
  transform: translate(-50%, -50%);
  pointer-events: none;
}
.dial-center {
  position: absolute;
  left: 50%;
  top: 50%;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: #202833;
  transform: translate(-50%, -50%);
  pointer-events: none;
}
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
        <div class="direction-dial-wrap">
          <div id="direction-dial" class="direction-dial" role="slider" tabindex="0" aria-label="Wind direction" aria-valuemin="0" aria-valuemax="359" aria-valuenow="0">
            <button type="button" class="dial-label north" data-dir="0" title="0 deg">N</button>
            <button type="button" class="dial-label east" data-dir="90" title="90 deg">E</button>
            <button type="button" class="dial-label south" data-dir="180" title="180 deg">S</button>
            <button type="button" class="dial-label west" data-dir="270" title="270 deg">W</button>
            <div id="dial-needle" class="dial-needle"></div>
            <div id="dial-handle" class="dial-handle"></div>
            <div class="dial-center"></div>
          </div>
        </div>
        <div class="inline-note">Compass heading: 0=N, 90=E, 180=S, 270=W</div>
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
      <div class="field">
        <label>&nbsp;</label>
        <button id="calm" type="button" class="with-icon">Zero Wind</button>
      </div>
    </div>
    <div class="row" style="margin-top: 14px;">
      <button id="send" class="primary">Send</button>
      <button id="live" class="toggle">Live</button>
    </div>
    <div class="row" style="margin-top: 8px;">
      <button id="record" type="button" class="with-icon">Record</button>
      <button id="play" type="button" class="with-icon">Play</button>
      <button id="stop-playback" type="button" class="danger with-icon" hidden>Stop</button>
      <input id="scenario-file" type="file" accept="application/json,.json" hidden>
    </div>
    <div id="scenario-status" class="scenario-status"></div>
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
let recording = false;
let recordStartedAt = 0;
let recordTimer = null;
let recordedCommands = [];
let playing = false;
let playbackPaused = false;
let playbackTimers = [];
let playbackRunId = 0;
let playbackCommands = [];
let playbackDurationMs = 0;
let playbackStartedAt = 0;
let playbackElapsedMs = 0;
let playbackNextIndex = 0;
let latestPluginStatus = null;
let lastPlaybackCommand = null;
let syncCommandWhenStatusUpdates = false;
let suppressLiveSend = false;

function numberValue(id) {
  const raw = $(id).value;
  if (raw === "") return null;
  const value = Number(raw);
  return Number.isFinite(value) ? value : null;
}

function normalizeDegrees(value) {
  return ((Number(value) % 360) + 360) % 360;
}

function compassToGazeboDegrees(value) {
  return normalizeDegrees(90 - Number(value));
}

function gazeboToCompassDegrees(value) {
  return normalizeDegrees(90 - Number(value));
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

function scenarioFilename() {
  const stamp = new Date().toISOString().replace(/[:.]/g, "-");
  return `wind_scenario_${stamp}.json`;
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

function downloadJsonFile(data, filename) {
  const content = JSON.stringify(data, null, 2);
  const blob = new Blob([content], {type: "application/json;charset=utf-8"});
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

async function saveJsonFile(data, filename) {
  try {
    const response = await fetch("/api/scenario/save", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({filename, scenario: data})
    });
    const result = await response.json();
    if (response.ok && result.saved) {
      if (result.path) log(`scenario saved to ${result.path}`);
      if (result.fallback) log("native save dialog unavailable; used /tmp/wind_scenarii fallback");
      return true;
    }
    if (response.ok && result.canceled) return false;
    if (result.error) log(`server save unavailable: ${result.error}`);
  } catch (err) {
    log(`server save unavailable: ${err.message}`);
  }
  downloadJsonFile(data, filename);
  return true;
}

function scenarioStatus(line) {
  $("scenario-status").textContent = line || "";
}

function formatDuration(ms) {
  const totalSeconds = Math.max(0, Math.floor(ms / 1000));
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  const tenths = Math.floor((Math.max(0, ms) % 1000) / 100);
  if (minutes > 0) return `${minutes}m ${String(seconds).padStart(2, "0")}.${tenths}s`;
  return `${seconds}.${tenths}s`;
}

function scenarioDurationMs(commands, fallbackMs = 0) {
  if (!Array.isArray(commands) || commands.length === 0) return Math.max(0, Math.round(fallbackMs));
  return Math.max(0, ...commands.map((entry) => Math.round(Number(entry.at_ms) || 0)));
}

function commandCountLabel(count) {
  return `${count} command${count === 1 ? "" : "s"}`;
}
function iconSvg(name) {
  const icons = {
    record: '<svg class="fill-icon" viewBox="0 0 16 16" aria-hidden="true"><circle cx="8" cy="8" r="5"></circle></svg>',
    play: '<svg class="fill-icon" viewBox="0 0 16 16" aria-hidden="true"><path d="M5 3.5v9l7-4.5z"></path></svg>',
    pause: '<svg class="fill-icon" viewBox="0 0 16 16" aria-hidden="true"><rect x="4" y="3" width="3" height="10" rx="0.8"></rect><rect x="9" y="3" width="3" height="10" rx="0.8"></rect></svg>',
    stop: '<svg class="fill-icon" viewBox="0 0 16 16" aria-hidden="true"><rect x="4" y="4" width="8" height="8" rx="1.4"></rect></svg>',
    windOff: '<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M2 6h7.5a2 2 0 1 0-2-2"></path><path d="M2 10h10a2 2 0 1 1-2 2"></path><path d="M3 14 13 2"></path></svg>'
  };
  return icons[name] || '';
}

function setButtonContent(id, icon, label) {
  const button = $(id);
  button.classList.add("with-icon");
  button.innerHTML = `${iconSvg(icon)}<span>${label}</span>`;
}


function recordingDurationMs() {
  return recordStartedAt > 0 ? Math.max(0, Math.round(performance.now() - recordStartedAt)) : 0;
}

function updateRecordingStatus() {
  if (!recording) return;
  scenarioStatus(`Recording ${commandCountLabel(recordedCommands.length)}, duration ${formatDuration(recordingDurationMs())}`);
}

function cloneCommand(command) {
  return JSON.parse(JSON.stringify(command));
}

function pluginCommandPayload(command) {
  const payload = cloneCommand(command);
  payload.direction_deg = compassToGazeboDegrees(payload.direction_deg || 0);
  return payload;
}

function recordCommand(command) {
  if (!recording || playing) return;
  recordedCommands.push({
    at_ms: Math.max(0, Math.round(performance.now() - recordStartedAt)),
    command: cloneCommand(command)
  });
  updateRecordingStatus();
}

function startRecording() {
  if (playing) {
    log("cannot record while scenario is playing");
    return;
  }
  recordedCommands = [];
  recordStartedAt = performance.now();
  recordTimer = setInterval(updateRecordingStatus, 250);
  recording = true;
  $("record").classList.add("recording");
  setButtonContent("record", "stop", "Stop");
  $("play").disabled = true;
  updateRecordingStatus();
  log("scenario recording started");
}

async function stopRecording() {
  const durationMs = recordingDurationMs();
  recording = false;
  clearInterval(recordTimer);
  recordTimer = null;
  $("record").classList.remove("recording");
  setButtonContent("record", "record", "Record");
  $("play").disabled = false;
  const scenario = {
    format: "wind-operator-scenario",
    version: 2,
    direction_frame: "compass",
    created_at: new Date().toISOString(),
    command_count: recordedCommands.length,
    duration_ms: durationMs,
    duration: formatDuration(durationMs),
    commands: recordedCommands
  };
  if (recordedCommands.length > 0) {
    const saved = await saveJsonFile(scenario, scenarioFilename());
    if (saved) {
      scenarioStatus(`Saved ${commandCountLabel(recordedCommands.length)}, duration ${formatDuration(durationMs)}`);
      log(`scenario saved with ${commandCountLabel(recordedCommands.length)}, duration ${formatDuration(durationMs)}`);
    } else {
      scenarioStatus("Save canceled");
      log("scenario save canceled");
    }
  } else {
    scenarioStatus("Recording discarded: no commands");
    log("scenario recording stopped with no commands");
  }
}

async function toggleRecording() {
  if (recording) {
    await stopRecording();
  } else {
    startRecording();
  }
}

function clearPlaybackTimers() {
  playbackTimers.forEach((timer) => clearTimeout(timer));
  playbackTimers = [];
}

function updatePlaybackButtons() {
  $("play").disabled = false;
  if (!playing) setButtonContent("play", "play", "Play");
  else if (playbackPaused) setButtonContent("play", "play", "Resume");
  else setButtonContent("play", "pause", "Pause");
  setButtonContent("stop-playback", "stop", "Stop");
  $("stop-playback").hidden = !playing;
  $("record").disabled = playing;
}

function setPlaying(value) {
  playing = value;
  if (!value) {
    playbackPaused = false;
    playbackElapsedMs = 0;
    playbackStartedAt = 0;
    playbackNextIndex = 0;
    playbackCommands = [];
    playbackDurationMs = 0;
  }
  updatePlaybackButtons();
}

function playbackElapsedNow() {
  if (!playing) return playbackElapsedMs;
  if (playbackPaused) return playbackElapsedMs;
  return Math.max(0, Math.round(performance.now() - playbackStartedAt));
}

function playbackProgressLabel(prefix) {
  return `${prefix} at ${formatDuration(playbackElapsedNow())} / ${formatDuration(playbackDurationMs)}`;
}

function schedulePlaybackFrom(elapsedMs) {
  clearPlaybackTimers();
  const runId = playbackRunId + 1;
  playbackRunId = runId;
  playbackStartedAt = performance.now() - elapsedMs;

  if (playbackNextIndex >= playbackCommands.length) {
    finishPlayback(runId);
    return;
  }

  playbackCommands.slice(playbackNextIndex).forEach((entry, offset) => {
    const index = playbackNextIndex + offset;
    const timer = setTimeout(() => {
      sendCommand(entry.command, {quiet: true, skipRecord: true})
        .then(() => {
          if (runId !== playbackRunId || !playing || playbackPaused) return;
          playbackNextIndex = Math.max(playbackNextIndex, index + 1);
          lastPlaybackCommand = cloneCommand(entry.command);
          log(`play ${index + 1}/${playbackCommands.length} wind=${entry.command.speed_knots}kt dir=${entry.command.direction_deg}deg`);
          if (index === playbackCommands.length - 1) {
            finishPlayback(runId);
          }
        })
        .catch((err) => {
          if (runId !== playbackRunId || !playing) return;
          clearPlaybackTimers();
          setPlaying(false);
          log(`playback error: ${err.message}`);
        });
    }, Math.max(0, entry.at_ms - elapsedMs));
    playbackTimers.push(timer);
  });
}

function finishPlayback(runId) {
  if (runId !== playbackRunId || !playing) return;
  clearPlaybackTimers();
  syncCommandFromCommand(playbackCommands.length > 0 ? playbackCommands[playbackCommands.length - 1].command : null);
  syncCommandWhenStatusUpdates = true;
  scenarioStatus(`Played ${commandCountLabel(playbackCommands.length)}, duration ${formatDuration(playbackDurationMs)}`);
  log("command controls synced from last scenario command");
  log("scenario playback complete");
  setPlaying(false);
}

function pausePlayback() {
  if (!playing || playbackPaused) return;
  playbackElapsedMs = Math.min(playbackDurationMs, playbackElapsedNow());
  playbackPaused = true;
  playbackRunId += 1;
  clearPlaybackTimers();
  updatePlaybackButtons();
  if (syncCommandFromCommand(lastPlaybackCommand) || syncCommandFromStatus(latestPluginStatus)) {
    syncCommandWhenStatusUpdates = true;
  }
  scenarioStatus(playbackProgressLabel("Paused"));
  log(`scenario playback paused at ${formatDuration(playbackElapsedMs)}`);
}

function resumePlayback() {
  if (!playing || !playbackPaused) return;
  playbackPaused = false;
  updatePlaybackButtons();
  scenarioStatus(playbackProgressLabel("Playing"));
  log(`scenario playback resumed at ${formatDuration(playbackElapsedMs)}`);
  schedulePlaybackFrom(playbackElapsedMs);
}

function stopPlayback() {
  if (!playing) return;
  playbackElapsedMs = Math.min(playbackDurationMs, playbackElapsedNow());
  playbackRunId += 1;
  clearPlaybackTimers();
  if (syncCommandFromCommand(lastPlaybackCommand) || syncCommandFromStatus(latestPluginStatus)) {
    syncCommandWhenStatusUpdates = true;
    log("command controls synced from stopped scenario state");
  }
  scenarioStatus(playbackProgressLabel("Stopped"));
  log("scenario playback stopped");
  setPlaying(false);
}

function validateScenario(scenario) {
  if (!scenario || !Array.isArray(scenario.commands)) {
    throw new Error("scenario file must contain a commands array");
  }
  const directionFrame = scenario.direction_frame || "gazebo";
  return scenario.commands.map((entry, index) => {
    const atMs = Number(entry.at_ms);
    if (!Number.isFinite(atMs) || atMs < 0) {
      throw new Error(`command ${index + 1} has an invalid at_ms`);
    }
    const command = cloneCommand(entry.command || {});
    if (directionFrame !== "compass") {
      command.direction_deg = gazeboToCompassDegrees(command.direction_deg || 0);
    }
    return {
      at_ms: atMs,
      command
    };
  }).sort((a, b) => a.at_ms - b.at_ms);
}

async function playScenario(scenario, filename = "selected scenario") {
  const commands = validateScenario(scenario);
  if (commands.length === 0) {
    log("scenario has no commands");
    return;
  }
  if (recording) {
    log("stop recording before playing a scenario");
    return;
  }
  clearPlaybackTimers();
  playbackCommands = commands;
  playbackDurationMs = scenarioDurationMs(commands, scenario.duration_ms);
  playbackElapsedMs = 0;
  playbackNextIndex = 0;
  lastPlaybackCommand = null;
  playbackPaused = false;
  playing = true;
  updatePlaybackButtons();
  scenarioStatus(`Playing ${commandCountLabel(commands.length)}, duration ${formatDuration(playbackDurationMs)}`);
  log(`playing file ${filename} with ${commandCountLabel(commands.length)}, duration ${formatDuration(playbackDurationMs)}`);
  schedulePlaybackFrom(0);
}

function openBrowserScenarioFile() {
  $("scenario-file").value = "";
  $("scenario-file").click();
}

async function openScenarioFile() {
  if (playing) {
    if (playbackPaused) resumePlayback();
    else pausePlayback();
    return;
  }
  if (recording) {
    log("stop recording before playing a scenario");
    return;
  }
  try {
    const response = await fetch("/api/scenario/open");
    const result = await response.json();
    if (response.ok && result.opened) {
      playScenario(result.scenario, result.filename || result.path || "selected scenario");
      return;
    }
    if (response.ok && result.canceled) return;
    if (result.error) log(`native open unavailable: ${result.error}`);
  } catch (err) {
    log(`native open unavailable: ${err.message}`);
  }
  openBrowserScenarioFile();
}

function readScenarioFile(file) {
  if (!file) return;
  const reader = new FileReader();
  reader.onload = () => {
    try {
      playScenario(JSON.parse(reader.result), file.name);
    } catch (err) {
      log(`scenario error: ${err.message}`);
      scenarioStatus("Could not load scenario");
    }
  };
  reader.onerror = () => {
    log("scenario error: could not read file");
    scenarioStatus("Could not read scenario");
  };
  reader.readAsText(file);
}

async function sendCommand(payload = commandPayload(), options = {}) {
  const pluginPayload = pluginCommandPayload(payload);
  const response = await fetch("/api/command", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(pluginPayload)
  });
  const result = await response.json();
  if (!response.ok) throw new Error(result.error || "command failed");
  if (!options.quiet) {
    log(`sent wind=${payload.speed_knots}kt dir=${payload.direction_deg}deg ramp=${payload.ramp_start_altitude}..${payload.ramp_end_altitude}m`);
  }
  if (!options.skipRecord) recordCommand(payload);
}

function scheduleLiveSend() {
  if (suppressLiveSend || !liveMode) return;
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

function setInputValue(id, value, digits = null) {
  if (typeof value !== "number" || !Number.isFinite(value)) return;
  $(id).value = digits === null ? value : Number(value.toFixed(digits));
}

function syncCommandFields(updateFn) {
  suppressLiveSend = true;
  try {
    updateFn();
  } finally {
    suppressLiveSend = false;
  }
}

function syncCommandFromCommand(command) {
  if (!command) return false;
  syncCommandFields(() => {
    setWind(command.speed_knots || 0);
    setDirection(command.direction_deg || 0);
    setInputValue("ramp-start", command.ramp_start_altitude, 1);
    setInputValue("ramp-end", command.ramp_end_altitude, 1);
    setInputValue("drag", command.drag_coefficient, 3);
    setInputValue("area", command.reference_area, 3);
    setInputValue("max-force", command.max_force, 1);
    updateCommandCda();
  });
  return true;
}

function syncCommandFromStatus(status) {
  if (!status) return false;
  syncCommandFields(() => {
    setWind(status.target_wind_knots || 0);
    setDirection(gazeboToCompassDegrees(status.direction_deg || 0));
    setInputValue("ramp-start", status.ramp_start_altitude, 1);
    setInputValue("ramp-end", status.ramp_end_altitude, 1);
    setInputValue("drag", status.drag_coefficient, 3);
    setInputValue("area", status.reference_area, 3);
    if (typeof status.max_force === "number") setInputValue("max-force", status.max_force, 1);
    updateCommandCda();
  });
  return true;
}

function updateDirectionDial(value) {
  const dial = $("direction-dial");
  const needle = $("dial-needle");
  const handle = $("dial-handle");
  if (!dial || !needle || !handle) return;
  const degrees = normalizeDegrees(value);
  const radians = degrees * Math.PI / 180;
  const radius = 70;
  const center = 84;
  const x = center + Math.sin(radians) * radius;
  const y = center - Math.cos(radians) * radius;
  needle.style.transform = `translate(-50%, -100%) rotate(${degrees}deg)`;
  handle.style.left = `${x}px`;
  handle.style.top = `${y}px`;
  dial.setAttribute("aria-valuenow", String(Math.round(degrees)));
}

function setDirection(value) {
  const normalized = normalizeDegrees(value);
  $("direction").value = normalized;
  $("direction-slider").value = normalized;
  updateDirectionDial(normalized);
  scheduleLiveSend();
}

function pointerPoint(event) {
  if (event.touches && event.touches.length > 0) return event.touches[0];
  if (event.changedTouches && event.changedTouches.length > 0) return event.changedTouches[0];
  return event;
}

function setDirectionFromPointer(event) {
  const point = pointerPoint(event);
  const dial = $("direction-dial");
  const rect = dial.getBoundingClientRect();
  const centerX = rect.left + rect.width / 2;
  const centerY = rect.top + rect.height / 2;
  const dx = point.clientX - centerX;
  const dy = point.clientY - centerY;
  setDirection(Math.round(normalizeDegrees(Math.atan2(dx, -dy) * 180 / Math.PI)));
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
    latestPluginStatus = d;
    if (syncCommandWhenStatusUpdates && !playing && !recording) {
      syncCommandWhenStatusUpdates = false;
      syncCommandFromStatus(d);
      log("command controls synced from current plugin status");
    }
    $("altitude").textContent = fmt(d.altitude_m, 1);
    $("actual-wind").textContent = fmt(d.actual_wind_knots, 1);
    $("target-wind").textContent = fmt(d.target_wind_knots, 1);
    $("force").textContent = fmt(d.force_n, 1);
    $("status-direction").textContent = fmt(gazeboToCompassDegrees(d.direction_deg), 0);
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
$("record").addEventListener("click", toggleRecording);
$("play").addEventListener("click", openScenarioFile);
$("stop-playback").addEventListener("click", stopPlayback);
$("scenario-file").addEventListener("change", (event) => readScenarioFile(event.target.files[0]));
$("calm").addEventListener("click", () => {
  setWind(0);
  setDirection(0);
  sendCommand().catch((err) => log(`error: ${err.message}`));
});
$("knots").addEventListener("input", (event) => setWind(event.target.value));
$("wind-slider").addEventListener("input", (event) => setWind(event.target.value));
$("direction").addEventListener("input", (event) => setDirection(event.target.value));
$("direction-slider").addEventListener("input", (event) => setDirection(event.target.value));
let draggingDirectionDial = false;
let activeDirectionPointerId = null;
let directionDragMoved = false;

function startDirectionDrag(event) {
  if (draggingDirectionDial && event.type === "mousedown") return;
  event.preventDefault();
  draggingDirectionDial = true;
  directionDragMoved = false;
  activeDirectionPointerId = event.pointerId ?? null;
  const dial = $("direction-dial");
  if (event.pointerId !== undefined && dial.setPointerCapture) {
    dial.setPointerCapture(event.pointerId);
  }
  setDirectionFromPointer(event);
}

function moveDirectionDrag(event) {
  if (!draggingDirectionDial) return;
  if (activeDirectionPointerId !== null && event.pointerId !== undefined && event.pointerId !== activeDirectionPointerId) return;
  event.preventDefault();
  directionDragMoved = true;
  setDirectionFromPointer(event);
}

function stopDirectionDrag(event) {
  if (event && activeDirectionPointerId !== null && event.pointerId !== undefined && event.pointerId !== activeDirectionPointerId) return;
  draggingDirectionDial = false;
  activeDirectionPointerId = null;
}

$("direction-dial").addEventListener("pointerdown", startDirectionDrag);
document.addEventListener("pointermove", moveDirectionDrag);
document.addEventListener("pointerup", stopDirectionDrag);
document.addEventListener("pointercancel", stopDirectionDrag);
$("direction-dial").addEventListener("mousedown", startDirectionDrag);
document.addEventListener("mousemove", moveDirectionDrag);
document.addEventListener("mouseup", stopDirectionDrag);
$("direction-dial").addEventListener("touchstart", startDirectionDrag, {passive: false});
document.addEventListener("touchmove", moveDirectionDrag, {passive: false});
document.addEventListener("touchend", stopDirectionDrag);
document.addEventListener("touchcancel", stopDirectionDrag);
$("direction-dial").addEventListener("keydown", (event) => {
  const current = numberValue("direction") || 0;
  if (event.key === "ArrowLeft" || event.key === "ArrowDown") {
    event.preventDefault();
    setDirection(current - 1);
  } else if (event.key === "ArrowRight" || event.key === "ArrowUp") {
    event.preventDefault();
    setDirection(current + 1);
  }
});
$("ramp-start").addEventListener("input", handleCommandInput);
$("ramp-end").addEventListener("input", handleCommandInput);
$("drag").addEventListener("input", updateCommandCda);
$("area").addEventListener("input", updateCommandCda);
$("max-force").addEventListener("input", handleCommandInput);
document.querySelectorAll("[data-dir]").forEach((button) => {
  button.addEventListener("click", (event) => {
    event.stopPropagation();
    if (directionDragMoved) {
      event.preventDefault();
      directionDragMoved = false;
      return;
    }
    setDirection(button.dataset.dir);
  });
});

setInterval(pollStatus, 500);
setButtonContent("calm", "windOff", "Zero Wind");
setButtonContent("record", "record", "Record");
setButtonContent("play", "play", "Play");
setButtonContent("stop-playback", "stop", "Stop");
updateCommandCda();
updateDirectionDial(numberValue("direction") || 0);
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
            elif path == "/api/scenario/open":
                try:
                    self._send_json(open_scenario_with_dialog())
                except Exception as exc:
                    self._send_json({"error": str(exc)}, 400)
            else:
                self._send_json({"error": "not found"}, 404)

        def do_POST(self):
            path = urlparse(self.path).path
            length = int(self.headers.get("Content-Length", "0"))
            try:
                data = json.loads(self.rfile.read(length).decode("utf-8"))
            except Exception as exc:
                self._send_json({"error": str(exc)}, 400)
                return

            if path == "/api/command":
                try:
                    bridge.send_command(validate_command(data))
                    self._send_json({"ok": True})
                except Exception as exc:
                    self._send_json({"error": str(exc)}, 400)
                return

            if path == "/api/scenario/save":
                try:
                    result = save_scenario_with_dialog(data)
                    self._send_json(result)
                except Exception as exc:
                    self._send_json({"error": str(exc)}, 400)
                return

            self._send_json({"error": "not found"}, 404)

    return Handler


def open_scenario_with_dialog():
    default_dir = Path("/tmp/wind_scenarii")
    default_dir.mkdir(parents=True, exist_ok=True)
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        try:
            root.attributes("-topmost", True)
            path = filedialog.askopenfilename(
                parent=root,
                title="Open wind scenario",
                initialdir=str(default_dir),
                filetypes=[("Wind scenario", "*.json"), ("All files", "*.*")],
            )
        finally:
            root.destroy()
        if not path:
            return {"opened": False, "canceled": True}
        with open(path) as handle:
            scenario = json.load(handle)
        return {
            "opened": True,
            "path": path,
            "filename": Path(path).name,
            "scenario": scenario,
        }
    except Exception as exc:
        return {"opened": False, "fallback": True, "error": str(exc)}


def save_scenario_with_dialog(data):
    filename = Path(str(data.get("filename") or "wind_scenario.json")).name
    scenario = data.get("scenario")
    if not isinstance(scenario, dict):
        raise ValueError("scenario must be a JSON object")
    content = json.dumps(scenario, indent=2, sort_keys=True) + "\n"
    default_dir = Path("/tmp/wind_scenarii")
    default_dir.mkdir(parents=True, exist_ok=True)
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        try:
            root.attributes("-topmost", True)
            path = filedialog.asksaveasfilename(
                parent=root,
                title="Save wind scenario",
                initialdir=str(default_dir),
                initialfile=filename,
                defaultextension=".json",
                filetypes=[("Wind scenario", "*.json"), ("All files", "*.*")],
            )
        finally:
            root.destroy()
        if not path:
            return {"saved": False, "canceled": True}
        with open(path, "w") as handle:
            handle.write(content)
        return {"saved": True, "path": path}
    except Exception as exc:
        fallback_path = default_dir / filename
        fallback_path.write_text(content)
        return {
            "saved": True,
            "path": str(fallback_path),
            "fallback": True,
            "warning": str(exc),
        }


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
    try:
        server = ThreadingHTTPServer((args.listen_host, args.listen_port), make_handler(bridge))
    except OSError as exc:
        bridge.close()
        if exc.errno == errno.EADDRINUSE:
            host = args.listen_host or "0.0.0.0"
            print(
                f"Address already in use: http://{host}:{args.listen_port}",
                file=sys.stderr,
            )
            print(
                f"Check the owning process with: lsof -iTCP:{args.listen_port} -sTCP:LISTEN",
                file=sys.stderr,
            )
            raise SystemExit(1)
        raise
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
