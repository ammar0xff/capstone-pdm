/* Experimental trend estimate (not validated). Browser-side, from this session's valid packets only. */
const RulTrend = (function () {
  const O = { binS: 10, minSpanS: 900, minBins: 60, ucl: 0.155, r2Min: 0.6, riseSdMin: 3, riseFracMin: 0.10, maxFutureSpanRatio: 2 };
  function median(a) { const s = a.slice().sort((x, y) => x - y); const m = s.length >> 1; return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2; }
  function estimate(samples, opt) {
    const o = Object.assign({}, O, opt || {});
    const bins = new Map();
    for (const p of samples) {
      if (!Number.isFinite(p.t) || !Number.isFinite(p.v)) continue;
      const k = Math.floor(p.t / o.binS);
      if (!bins.has(k)) bins.set(k, []);
      bins.get(k).push(p.v);
    }
    const pts = [...bins.entries()].sort((a, b) => a[0] - b[0]).map(([k, v]) => ({ t: (k + 0.5) * o.binS, v: median(v) }));
    const span = pts.length ? pts[pts.length - 1].t - pts[0].t : 0;
    if (pts.length < o.minBins || span < o.minSpanS) return { status: "insufficient", bins: pts.length, spanS: span, needBins: o.minBins, needSpanS: o.minSpanS };
    const n = pts.length, mt = pts.reduce((s, p) => s + p.t, 0) / n, mv = pts.reduce((s, p) => s + p.v, 0) / n;
    let sxx = 0, sxy = 0, syy = 0;
    for (const p of pts) { sxx += (p.t - mt) ** 2; sxy += (p.t - mt) * (p.v - mv); syy += (p.v - mv) ** 2; }
    const slope = sxy / sxx, icpt = mv - slope * mt;
    let sse = 0; for (const p of pts) sse += (p.v - (icpt + slope * p.t)) ** 2;
    const r2 = syy > 0 ? 1 - sse / syy : 0, resSd = Math.sqrt(sse / (n - 2)), se = resSd / Math.sqrt(sxx);
    const rise = slope * span, base = { slopePerHour: slope * 3600, r2, spanS: span, bins: n };
    if (!(slope > 0) || r2 < o.r2Min || rise < o.riseSdMin * resSd || rise < o.riseFracMin * Math.abs(mv)) return Object.assign({ status: "no_trend" }, base);
    const cur = icpt + slope * pts[n - 1].t;
    if (cur >= o.ucl) return Object.assign({ status: "at_limit", current: cur }, base);
    const hrs = (o.ucl - cur) / slope / 3600;
    if (hrs * 3600 > o.maxFutureSpanRatio * span) return Object.assign({ status: "too_far", current: cur }, base);
    const sHi = slope + 1.96 * se, sLo = slope - 1.96 * se;
    return Object.assign({ status: "estimate", current: cur, hours: hrs, hoursLow: (o.ucl - cur) / sHi / 3600, hoursHigh: sLo > 0 ? (o.ucl - cur) / sLo / 3600 : null }, base);
  }
  const buf = []; let lastSeq = null;
  function observe(data, nowS) {
    const v = data && data.vibration ? data.vibration.rms_dyn : null;
    const ok = data && data.state !== "Unknown" && data.input_valid !== false && Number.isFinite(v);
    if (!ok) return;
    if (data.seq !== undefined && data.seq === lastSeq) return;
    lastSeq = data.seq; buf.push({ t: nowS, v }); if (buf.length > 20000) buf.shift();
  }
  function text(r) {
    const mins = (h) => h * 60;
    const fmt = (h) => h < 1 ? Math.round(mins(h)) + " min" : h.toFixed(1) + " h";
    if (r.status === "insufficient") return { head: "Insufficient data", body: "Needs about " + Math.round(r.needSpanS / 60) + " min of valid readings in this session (have " + Math.round(r.spanS / 60) + " min)." };
    if (r.status === "no_trend") return { head: "No upward trend", body: "Vibration RMS shows no clear rise in this session, so no time estimate is given." };
    if (r.status === "at_limit") return { head: "At the fault limit", body: "The fitted vibration RMS trend is at or above the fault limit. Inspect the machine." };
    if (r.status === "too_far") return { head: "Trend too slow to extrapolate", body: "The rise is too slow to project beyond what this session observed." };
    return { head: "about " + fmt(r.hours), body: "Time for the fitted vibration RMS trend to reach the fault limit" + (r.hoursHigh ? " (95% range " + fmt(r.hoursLow) + " to " + fmt(r.hoursHigh) + ")" : " (upper bound open)") + "." };
  }
  return { estimate, observe, text, buf, O };
})();
if (typeof module !== "undefined") module.exports = RulTrend;
