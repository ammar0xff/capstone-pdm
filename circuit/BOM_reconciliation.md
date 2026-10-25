# BOM reconciliation — 2026-10-25

The supplier sheet is real. The 8240 was an estimate.

That single sentence is the whole document. Everything below is arithmetic on quotes that
exist, with no invented prices and no "if we re-quote the Pi" hand-waving.

---

## 1. The numbers as they stand

| | EGP |
|---|---|
| 20 priced lines (2026-10-25 quotes) | **8,888.25** |
| MAX6675 module | **not quoted** |
| Target | **8,240.00** |
| **Gap, before the missing part** | **+648.25** |

`circuit/bom_target.csv` is now these exact quotes, so `python3 circuit/build.py` fails three
BOM checks on purpose. The build reads the sheet, not our hopes.

**The gap cannot be closed by shopping.** Headroom for the MAX6675 is −648.25 EGP, i.e. the
priced lines are already over. No MAX6675 price, however low, makes the build legal.

## 2. The 8240 is self-imposed

`G12_27_ Capstone.pdf` contains the design requirements, the constraints (no Arduino, no lab
equipment removed, portable/testable), and **no budget rule at all**. The 8240 came from our
own first BOM. So restating it is allowed; overrunning it is a project risk, not a
disqualification. (The earlier claim in the book that spending more than 8240 "disqualifies"
was wrong and has been removed.)

## 3. Why cutting quantities does not work

Every cut available on this sheet, at these unit prices:

| Cut | Saves |
|---|---|
| Collect in person instead of paying 4-store shipping | −220.00 |
| DIY magnetic mount (bolt + epoxy + magnet) | −85.00 |
| One breadboard instead of two | −35.00 |
| One header strip instead of two | −7.00 |
| 20 shielded leads instead of 30 | −7.00 |
| 2 screws packs / 6 spacers instead of 3 / 10 | −14.50 |
| 3× 100 nF, 2× 10 uF, 2× 10k instead of 5 / 3 / 5 | −11.25 |
| **Maximum possible** | **−379.75** |

8,888.25 − 379.75 = **8,508.50**, still **+268.50** over, and the MAX6675 is still unpriced.
Quantity trimming cannot reach 8240 while keeping vibration + temperature + sound.

## 4. The three closures that can

### A — restate the ceiling to 9,090 EGP  (no scope change)

8,888.25 + 200 (a realistic MAX6675) = **9,088.25** → round to **9,090**, leaving ~2 EGP.

If the enclosure stays sealed and IP65, add the fan, glands and heat-shrink that this sheet
dropped: 240 + 30 + 10 = **9,368.25** → **9,370**.

| | |
|---|---|
| Cost | +648 to +1,128 over the old number |
| Scope | unchanged: all three sensor modalities, Pi 4 4 GB, sealed box |
| Risk | none technical; it is a budget restatement, permitted because the paper sets none |
| Needs | a written sign-off on the new ceiling, and the MAX6675 quote |

This is the recommended path **if the Pi 4 has already been bought** — nothing else is large
enough to matter.

### B — change the compute board  (the only real lever)

The Pi 4 4 GB is **6,850 of the 8,888 = 77 %** of the spend. Board price, not sensor choice,
decides whether this project fits.

| Board | Non-compute BOM | Board (needs quote) | Total + 200 MAX6675 |
|---|---|---|---|
| Pi 4 4 GB (current) | 2,038.25 | 6,850 | **9,088** |
| Pi 4 2 GB | 2,038.25 | ~5,000? | **~7,238** |
| Pi Zero 2 W | 2,038.25 | ~2,800? | **~5,038** |

A Zero 2 W also draws ~0.7 A instead of 1.5 A: the sealed-box fan (240) and the throttling
WARN both disappear. Training moves to a laptop; only RF/SPC inference runs on the device,
which is still edge AI and still satisfies the challenge.

**The two board prices above are placeholders, not quotes.** This path cannot be booked until
one of them is confirmed. Do not put an invented number in the BOM.

### C — cut scope  (does not close it)

Even at the maximum −379.75 above the build is ~470 over with the converter. Reaching 8240
this way means deleting a sensing modality, which breaks the brief. **Rejected.**

## 5. What is still missing from the sheet, whatever we choose

1. **MAX6675 price** — without it no total is final. Expect 150–250 EGP.
2. **Fan, glands, heat-shrink** — only if the box stays sealed (+280). If the project moves to
   a vented frame, the IP65 claim must be deleted from the book with it.
3. **Class-1 probe** — the 250 EGP K-type must be ±1.5 °C, or M4 becomes ±2.5 °C. This is a
   purchasing rule, not a price.

## 6. What does not change

The electrical design, the netlist, the three schematics, the 1.68 °C error budget and the AI
pipeline are independent of price. They are generated and checked. Only the purchasing plan
is open — and it is open for one reason: the board is 77 % of the budget.

## 7. Actions

1. Decide **A or B**, in writing, before the next purchase.
2. If **A**: sign the new ceiling, quote the MAX6675, add the fan/glands if sealed, update
   `bom_target.csv` and re-run `build.py` — the gate goes green on its own.
3. If **B**: get a real board quote first, then swap the board line; the circuit does not change
   (same GPIO, same buses), only the compute and thermal sections of the book.
4. Never enter a price you have not been quoted. The gate is designed to catch it.
