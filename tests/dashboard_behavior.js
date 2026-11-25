// Runs the dashboard script against a stub DOM and checks what a viewer would see.
const fs = require("fs"), path = require("path"), assert = require("assert");
const html = fs.readFileSync(path.join(__dirname, "..", "public", "index.html"), "utf8");
const script = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].pop()[1];
function makeEl() {
  const cls = new Set();
  return { innerText: "", innerHTML: "", className: "", dataset: {}, style: { removeProperty() {}, setProperty() {} },
    classList: { add: (c) => cls.add(c), remove: (c) => cls.delete(c), toggle: (c, on) => (on ? cls.add(c) : cls.delete(c)), contains: (c) => cls.has(c) } };
}
function run(packet, nowSec) {
  const els = {}; const ids = [...html.matchAll(/id="([^"]+)"/g)].map((m) => m[1]);
  ids.forEach((i) => (els[i] = makeEl()));
  const layout = makeEl();
  const doc = { getElementById: (i) => { if (!els[i]) throw new Error("missing id " + i); return els[i]; },
    querySelector: () => layout, querySelectorAll: () => [], addEventListener() {} };
  const realNow = Date.now; Date.now = () => nowSec * 1000;
  const sandbox = new Function("document", "window", "Chart", "EventSource", "fetch", "setInterval", script + "\nreturn {updateDashboard, updateHardwareStatus};");
  const api = sandbox(doc, { addEventListener() {} }, undefined, undefined, () => Promise.reject(), () => 0);
  api.updateDashboard(packet); api.updateHardwareStatus(packet);
  Date.now = realNow; return { els, layout };
}
const base = { state: "Healthy", fault: "Normal Operation", rms: 0.0134, peak: 0.036, kurt: 3.88, cf: 2.69, temp: 22.25, slope: -0.29,
  sound_db: 63.3, zcr: 0, seq: 10, uptime_s: 100, proba: 0.05,
  ai: { gate_status: "Stage 1 Gated (Shewhart Normal)", predicted_class: "Normal Operation" },
  system: { max6675_ok: true, adxl_ok: true, acoustic_ok: true }, vibration: { fs_hz: 30.1 }, ts: 1000 };
let n = 0; const t = (name, fn) => { fn(); n++; console.log("ok", name); };

t("fresh healthy packet shows state, age, no confidence", () => {
  const { els } = run(base, 1005);
  assert.strictEqual(els["status-title"].innerText, "Normal Operation");
  assert.match(els["txt-cloud-status"].innerText, /STREAMING/);
  assert.strictEqual(els["badge-age"].innerText, "5s ago");
  assert.strictEqual(els["pill-stage2"].innerText, "NOT RUN");
  assert.match(els["txt-rf"].innerText, /was not run/);
  assert.ok(!("badge-ai-conf" in els));
});
t("same packet 30 s later is stale and never shows a health state", () => {
  const { els } = run(base, 1030);
  assert.strictEqual(els["status-title"].innerText, "No live data");
  assert.match(els["txt-cloud-status"].innerText, /STALE/);
  assert.ok(!els["lamp-icon"].className.includes("fa-check"));
  assert.strictEqual(els["main-status-card"].className, "scada-hero-panel awaiting");
  assert.strictEqual(els["pill-stage1"].innerText, "OLD PACKET");
});
t("same packet 5 min later is offline", () => {
  const { els } = run(base, 1300);
  assert.match(els["txt-cloud-status"].innerText, /OFFLINE/);
  assert.strictEqual(els["status-title"].innerText, "No live data");
});
t("fresh fault packet is flagged as rules, not as a model result", () => {
  const { els } = run({ ...base, state: "Fault", fault: "Bearing Defect", ai: { gate_status: "Stage 2 Active", predicted_class: "Bearing Defect" } }, 1002);
  assert.match(els["status-title"].innerText, /^Fault flagged/);
  assert.match(els["status-sub"].innerText, /threshold rules/);
  assert.strictEqual(els["pill-stage2"].innerText, "UNVALIDATED");
});
t("missing fields stay NO DATA; nothing invented", () => {
  const { els } = run({ state: "Healthy", fault: "Normal Operation", ts: 1000, seq: 1 }, 1002);
  for (const id of ["val-rms", "val-temp", "val-sound-db", "val-tc", "val-mic"]) assert.strictEqual(els[id].innerText || els[id].innerHTML, "NO DATA", id);
});
t("unknown state does not light the lamp", () => {
  const { els } = run({ ...base, state: "Excellent" }, 1002);
  assert.strictEqual(els["status-title"].innerText, "Awaiting telemetry");
});
t("sensor faults and open thermocouple are shown", () => {
  const { els } = run({ ...base, system: { max6675_ok: false, adxl_ok: true, acoustic_ok: true }, temperature: { open_tc: 1 } }, 1002);
  assert.strictEqual(els["val-tc"].innerText, "FAULT"); assert.strictEqual(els["val-open"].innerText, "OPEN");
});
console.log(n + " behaviour checks passed");
