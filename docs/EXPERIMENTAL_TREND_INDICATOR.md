# Experimental remaining-time indicator (not a validated RUL)

Shown on the local Pi dashboard (AI card) and the hosted dashboard (above the evidence panel). Computed in the browser only. No daq, mirror, threshold or sensing change.

## Method
- Input: vibration RMS (`vibration.rms_dyn`) from packets that are not Unknown and have `input_valid` not false, one per new `seq`.
- Samples are binned to 10 s medians. A straight line is fitted to the bins.
- A time estimate is given only when all hold: at least 60 bins over at least 15 min in this page session; slope positive; R squared at least 0.6; fitted rise at least 3 residual SD and at least 10% of the mean.
- Estimate = time for the fitted line to reach the existing fault limit (UCL 0.155 g, read only). A 95% slope range is shown. If the time is more than 2x the observed span the page says the trend is too slow to extrapolate.
- States: Insufficient data, No upward trend, At the fault limit, Trend too slow to extrapolate, about X (with range), Waiting for live data (no valid packet for 30 s).

## What it cannot claim
- It is not a validated RUL. There is no run-to-failure data for this rig, and the vibration fault limit is a rule threshold, not a measured failure point.
- It resets when the page reloads and uses only this session.
- It says nothing about the real remaining life of the motor. Rising RMS from a moved sensor, speed change or noise would also produce a rise.

## Tests
`pi_deployed/tests/rul_trend_test.js` (synthetic series: short data, flat noisy, falling, rising to the limit, at limit, too slow, NaN samples, Unknown/invalid/duplicate packets). Rendered in headless Chrome with synthetic series on the hosted page: rising gives "about 33 min", flat gives "No upward trend", live feed gives "Insufficient data".

## Rollback
Pi: `~/stat_stage/rul/rollback.sh`. Hosted: redeploy `backups/pre-rul-trend/public_index.html` as `public/index.html`.
