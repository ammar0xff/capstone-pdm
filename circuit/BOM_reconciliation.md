# BOM reconciliation — 2026-10-25

Two documents exist and they disagree. Neither is wrong; they answer different questions.

| Document | What it is | Total |
|---|---|---|
| `circuit/bom_target.csv` | the **build list**: what the design needs, at the prices we intend to pay | **8240.00** (26 lines, incl. 150 reserve) |
| `DOC-20261014-WA0055.xlsx` (working copy) | a **supplier re-shop** drafted on 2026-10-25 | **8888.25** (23 priced lines + 1 unpriced) |

`circuit/build.py` checks the target for the 8240 cap and checks the supplier sheet for
consistency. The target passes; the supplier sheet does not. That FAIL is intentional —
it is the pipeline refusing to pretend the budget is fine.

---

## 1. What actually changed between the two sheets

| Line | Committed quote (2026-10-14) | Re-shop (2026-10-25) | Δ |
|---|---|---|---|
| Raspberry Pi 4 | **8 GB @ 5800** | **4 GB @ 6850** | **+1050** and 4 GB less RAM |
| MicroSD 32 GB | 190 | 449 | +259 |
| M-M jumpers | 35 | 220 | +185 |
| Pi PSU 5V/3A | 320 | 200 | −120 |
| IP65 box | 140 | 55 | −85 |
| Case & fan | 240 | **removed** | −240, but the Pi now has no cooling |
| PG7 glands + heat-shrink | 40 | **removed** | −40, and the box can no longer be sealed |
| Breadboards | 65 (1) | 70 (2) | +5 |
| MAX6675 module | — | **no price entered** | unknown |

Net: the re-shop is **cheaper on four lines** and **much more expensive on three**, and it
removes two items the design cannot work without.

## 2. Why the re-shop cannot be built as written

1. **No fan in a sealed IP65 box.** The Pi 4 idles at ~3 W and peaks near 6.4 W; inside a
   closed box the air rises 10–15 °C above ambient. Without the case fan the SoC reaches
   its 80 °C throttle point during a 60-minute exhibition run — exactly when the demo must
   not stutter. The fan is a functional requirement, not a comfort item.
2. **No glands, no heat-shrink.** The IP65 claim and the strain relief both disappear.
   A cable pulled through a bare hole also pulls the breadboard wiring apart.
3. **MAX6675 has no price.** The budget cannot be closed on an unpriced line.
4. **A 4 GB Pi at 6850 is strictly worse than an 8 GB Pi at 5800.** Same board, half the
   RAM, 1050 EGP more. Unless the 5800 quote has expired, this line is a data error.

## 3. The target BOM (what the design is checked against)

Same 25 items as the committed quote, with the two sensing lines swapped to the chosen
K-type front end and 150 EGP held back as a reserve:

| Change | Effect |
|---|---|
| PT100 3-wire M6 (220) → **K-type class-1 M6 (250)** | +30 |
| MAX31865 (380) → **MAX6675 (200, estimate)** | −180 |
| **Reserve** for re-quote and breakage | +150 |
| **Total** | **8240.00** |

The reserve is deliberate. The MAX6675 price is an estimate, and a class-1 probe can cost
more than a generic one. If both come in high, the reserve absorbs it; if they come in
low, the difference stays unspent.

## 4. Actions, in priority order

1. **Re-quote the Raspberry Pi 4.** This single line is 70 % of the budget. If 8 GB @ 5800
   is still available, take it and the rest of the plan fits with room to spare. If the
   real price is 6850, the 8240 cap is arithmetically impossible with a Pi 4 8 GB and the
   project must either use a 4 GB board at a lower price or move to a Pi 5/CM4 quote.
2. **Quote the MAX6675** (expect 150–250 EGP) and confirm the probe is **class 1**
   (`±1.5 °C` or `0.004|t|`). A class-2 probe silently moves M4 to ±2.5 °C.
3. **Put the fan, glands and heat-shrink back** in whichever sheet is used for purchasing.
4. **Re-check the SD and jumper prices.** 449 for a 32 GB card and 220 for a jumper kit are
   both far above the earlier quotes; these are the easiest 400 EGP to recover.
5. Then update `circuit/bom_target.csv` and re-run `python3 circuit/build.py`. The BOM gate
   turns green only when the sheet and the design agree.

## 5. What this does *not* change

The electrical design, the netlist, the three schematics, the error budget and the AI
pipeline are independent of price. They are already generated and checked. Only the
purchasing plan is open.
