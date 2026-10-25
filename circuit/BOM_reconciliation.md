# BOM reconciliation — decision record, 2026-10-25

## Decision

**The ceiling is restated to 9,370 EGP. Every part stays. The Pi 4 4 GB is already bought.**

| | EGP |
|---|---|
| 2026-10-25 supplier quotes, 20 priced lines | 8,888.25 |
| Fan + glands + heat-shrink (re-added, 2026-10-14 quotes) | 280.00 |
| MAX6675 — **allowance, not a quote** | 200.00 |
| **Planned total** | **9,368.25** |
| **Signed ceiling** | **9,370.00** |
| Headroom | **1.75** |

Two things make this legitimate rather than a fudge:

1. **The challenge paper sets no budget.** `G12_27_ Capstone.pdf` requires ≥4 measurable
   requirements, ≥80 % AI accuracy, documented calibration, ICT/IoT/AI, a hardware prototype,
   portable/testable/reliable, and no Arduino. It mentions money nowhere. The 8240 was our own
   estimate, so restating it is a decision, not a violation.
2. **The Pi is sunk.** It was bought at 6,850 before the quotes were reconciled. Changing the
   board is no longer available as a lever, and the remaining parts cannot absorb 648.25.

## Why this and not the alternatives

| Option | Outcome | Verdict |
|---|---|---|
| **A. Restate the ceiling (chosen)** | 9,368.25 planned, 9,370 signed | Keeps all three sensor modalities, the sealed IP65 box, and the Pi that is already paid for |
| B. Change the compute board | ~5,000–7,250 if a smaller board could be quoted | **Impossible now** — the Pi is bought. Was the only lever big enough before that |
| C. Cut quantities | Max −379.75 (self-pickup −220, DIY magnet −85, one breadboard −35, trims −44.75) | Still ~268 over *before* the converter, and it deletes no requirement, so it cannot close the gap. Rejected |

The 280 EGP that the 2026-10-25 re-shop had silently dropped is back in on purpose: without the
fan, a Pi 4 in a sealed IP65 box reaches its 80 °C throttle point during a 60-minute exhibition
run. Without the glands and heat-shrink there is no IP65 claim and no strain relief.

## The one rule that is still open

**The MAX6675 must be quoted at or below 201.75 EGP.** The 200 in the table is an allowance so
the plan can be closed; it is not a quote, and the build marks it WARN until it is real.

If the shop quotes more than 201.75, the fallback is **collect the order in person (−220
shipping)** — not another ceiling change. Photograph the receipt either way.

## What the numbers say about the design

- The Pi is **6,850 of 9,368 = 73 %** of the spend, and it is already paid for.
- The complete sensing stack — ADXL345, class-1 K-type probe, MAX6675, INMP441 — is **800 EGP,
  8.5 %**. Sensor choice was never the budget problem.
- 0 EGP cloud is untouched: Firebase Spark, Grafana Cloud free, local Mosquitto + Flask.

## Record of the earlier attempt (kept for the logbook)

The first plan used a PT100 + MAX31865 at 220 + 380 and an 8 GB Pi at a 5,800 quote, and totalled
8,240. When the school-adjacent shops were re-quoted on 2026-10-25, the real prices were:
Pi 4 4 GB 6,850 (the 8 GB was not available at 5,800), microSD 449, M-M jumpers 220, and no
price at all for the MAX6675, while the fan, glands and heat-shrink had been dropped from the
line list. The old total was therefore an estimate that could not be reproduced, which is why
the ceiling moved rather than the parts.

## Checklist before ordering

- [ ] Quote the MAX6675; record the number in `circuit/bom_target.csv` (replace the allowance).
- [ ] Confirm the K-type probe is **class 1** (±1.5 °C or 0.004|t|), not class 2.
- [ ] Buy fan + glands + heat-shrink with the order; they are in the plan, not optional.
- [ ] Photograph every receipt into `budget/`.
- [ ] Re-run `python3 circuit/build.py`; the BOM group must stay green (0 FAIL).
