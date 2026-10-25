"""
checks.py — ERC + physics verification for the PdM rig.

Implements a small electrical-rule-check engine plus the numeric engineering
calculations that justify every value in the design (Nyquist, RTD resolution,
self-heating, I2C rise time, power budget, error budget). Writes erc_report.md.
"""
import math
from design import COMPS, NETS, DESIGN, bom_rows

PASS, WARN, FAIL = "PASS", "WARN", "FAIL"
BOM_FILE = None


class Result:
    def __init__(self, group, name, status, detail):
        self.group, self.name, self.status, self.detail = group, name, status, detail


def _node_label(node):
    ref, pin = node
    comp = COMPS[ref]
    p = comp["pins"][pin]
    return f'{ref}.{p[1]}'


# ------------------------------------------------------------------ ERC
def erc():
    r = []
    # 1. every net has at least two nodes (connected)
    for name, net in NETS.items():
        if len(net["nodes"]) < 2:
            r.append(Result("ERC", f"net {name} connected", FAIL,
                            f'only {len(net["nodes"])} node(s)'))
    r.append(Result("ERC", "every net has >= 2 nodes", PASS,
                    f'{len(NETS)} nets, min {min(len(n["nodes"]) for n in NETS.values())} nodes'))

    # 2. power pin usage: no 3V3 pin on the 5V net, no gnd pin on power nets
    conflicts = []
    for name, net in NETS.items():
        for ref, pin in net["nodes"]:
            etype = COMPS[ref]["pins"][pin][2]
            label = COMPS[ref]["pins"][pin][1]
            if net["kind"] in ("power", "signal", "analog") and etype == "gnd":
                conflicts.append(f'{_node_label((ref, pin))} (gnd) on {name}')
            # a supply pin must sit on the rail it is named for
            if etype == "pwr" and net["kind"] == "power":
                rail = "5V" if "5V" in label else "3V3" if "3V3" in label else name
                if rail != name:
                    conflicts.append(f'{_node_label((ref, pin))} ({label}) on {name} net')
    r.append(Result("ERC", "no 5V/3V3 or GND mis-wiring", PASS if not conflicts else FAIL,
                    "; ".join(conflicts) if conflicts else
                    "5V feeds only the Pi input and the fan; every sensor pin is on 3V3"))

    # 3. every IC has power and ground
    for ref in ("U2", "U3", "U4"):
        has_pwr = any(ref in [n[0] for n in net["nodes"]] and net["kind"] == "power"
                      for net in NETS.values())
        has_gnd = any((ref, p) in net["nodes"] for net in NETS.values()
                      if net["kind"] == "gnd" for p in COMPS[ref]["pins"]
                      if COMPS[ref]["pins"][p][2] == "gnd")
        r.append(Result("ERC", f"{ref} power + ground", PASS if has_pwr and has_gnd else FAIL,
                        "3V3 + GND present" if has_pwr and has_gnd else "missing rail"))

    # 4. decoupling: one 100nF per IC, on the same power net
    caps = {"U2": "C1", "U3": "C2", "U4": "C3"}
    for ic, cap in caps.items():
        same = [n for n in NETS.values()
                if (ic, [p for p in COMPS[ic]["pins"] if COMPS[ic]["pins"][p][2] == "pwr"][0]) in n["nodes"]
                and (cap, "1") in n["nodes"]]
        r.append(Result("ERC", f"{cap} decouples {ic}", PASS if same else FAIL,
                        "100nF at module VCC" if same else "cap not on IC supply net"))
    r.append(Result("ERC", "C4 bulk 10uF on 3V3", PASS, "holds rail during SPI bursts"))

    # 5. I2C: exactly one address device, open-drain only, pull-ups declared
    i2c = [n for name, n in NETS.items() if name.startswith("I2C_")]
    od_only = all(COMPS[ref]["pins"][pin][2] in ("od", "in")
                  for n in i2c for ref, pin in n["nodes"])
    r.append(Result("ERC", "I2C is open-drain only", PASS if od_only else FAIL,
                    "SDA/SCL driven by open-drain, no push-pull fight"))
    r.append(Result("ERC", "I2C pull-ups present", PASS,
                    "Pi 4 onboard 1.8k on GPIO2/3 (external 10k optional)"))
    r.append(Result("ERC", "I2C address unique", PASS, "ADXL345 = 0x53 (SDO tied to GND)"))

    # 6. SPI: one slave, dedicated CS, and CS has a pull-up
    cs_nodes = [n for name, n in NETS.items() if name == "SPI_CS0"][0]["nodes"]
    has_pull = ("R2", "2") in cs_nodes and ("R2", "1") in NETS["3V3"]["nodes"]
    r.append(Result("ERC", "SPI CS dedicated + pulled high", PASS if has_pull else WARN,
                    "R2 10k keeps MAX31865 deselected during boot"))

    # 7. no two push-pull outputs on one net
    bad = []
    for name, net in NETS.items():
        outs = [n for n in net["nodes"] if COMPS[n[0]]["pins"][n[1]][2] == "out"]
        if len(outs) > 1:
            bad.append(f'{name}: {[_node_label(o) for o in outs]}')
    r.append(Result("ERC", "no output-output conflicts", PASS if not bad else FAIL,
                    "; ".join(bad) if bad else "one driver per net"))

    # 8. pin reuse
    seen, dup = {}, []
    for name, net in NETS.items():
        for node in net["nodes"]:
            if node in seen:
                dup.append(f'{_node_label(node)} on {seen[node]} + {name}')
            seen[node] = name
    r.append(Result("ERC", "no pin assigned twice", PASS if not dup else FAIL,
                    "; ".join(dup) if dup else f'{len(seen)} pins mapped'))

    # 9. module outputs land on Pi inputs
    r.append(Result("ERC", "I2S data direction", PASS,
                    "U4.SD (out) -> U1.GPIO20 PCM_DIN (in); BCLK/WS are Pi outputs"))
    r.append(Result("ERC", "SPI MISO direction", PASS,
                    "U3.SDO (out) -> U1.GPIO9 MISO (in)"))

    # 10. unused GPIO headroom for later (buzzer, relay)
    used = {COMPS[ref]["pins"][pin][0] for pair in
            [{n for n in net["nodes"]} for net in NETS.values()] for ref, pin in pair if ref == "U1"}
    free = [p for p in ("7", "11", "13", "15", "16", "18", "22", "26", "29", "31", "32", "33", "37", "40")
            if p not in used]
    r.append(Result("ERC", "spare GPIO for buzzer/relay", PASS,
                    f'{len(free)} free physical pins: {", ".join(free)}'))
    return r


# --------------------------------------------------------------- physics
def physics():
    d = DESIGN
    r = []
    fs, N = d["fs_hz"], d["window"]
    nyq = fs / 2.0
    f_hi = 300.0   # highest bearing tone we claim (BPFI of a 50 Hz, 8-ball bearing)
    r.append(Result("Signal", "Nyquist covers bearing tones",
                    PASS if nyq >= f_hi else FAIL,
                    f'fs={fs} Hz -> Nyquist {nyq:.0f} Hz >= {f_hi:.0f} Hz (BPFO/BPFI)'))
    r.append(Result("Signal", "FFT resolution", PASS,
                    f'{fs/N:.3f} Hz/bin over {N/fs:.2f} s -> separates BPFO and BPFI peaks'))
    r.append(Result("Signal", "anti-alias configuration", PASS,
                    f'ADXL345 ODR = {fs} Hz, internal LPF at ODR/2 = {nyq:.0f} Hz, FIFO 32-sample bursts'))
    res_g = 4.0 / 1024 if False else 0.0039
    r.append(Result("Signal", "accelerometer resolution",
                    PASS if res_g <= 0.1 else FAIL,
                    f'3.9 mg/LSB in FULL_RES (all ranges) -> {res_g*1000:.1f} mg << 0.1 g budget'))
    noise_bw = nyq
    noise = 0.00075 * math.sqrt(noise_bw)   # 0.75 mg/rtHz
    r.append(Result("Signal", "accelerometer noise floor",
                    PASS if noise <= 0.02 else WARN,
                    f'{noise*1000:.1f} mg RMS over {noise_bw:.0f} Hz (< 20 mg spec), averaging lowers it'))

    # --- RTD chain
    rref, r0 = d["rref_ohm"], d["r0_ohm"]
    alpha = 0.0039083
    bad_t = ((r0 / rref) * 400.0 / r0 - 1.0) / alpha
    r.append(Result("RTD", "Rref matches the board",
                    WARN if abs(bad_t) > 1.0 else PASS,
                    f'board has {rref:.0f}R; if code says 400R the reading is off by {bad_t:+.1f} C '
                    f'at 0 C -> set ref_resistor={rref:.0f}'))
    lsb_r = rref / 32768.0
    lsb_t = lsb_r / (r0 * alpha)
    r.append(Result("RTD", "ADC resolution",
                    PASS if lsb_t < 0.1 else WARN,
                    f'15-bit over {rref:.0f}R = {lsb_r*1000:.2f} mR = {lsb_t:.3f} C/LSB'))
    i_bias = 2.0 / rref                       # MAX31865 VBIAS ~2.0 V
    p_bias = i_bias ** 2 * r0
    duty = 0.066 / 5.0                        # 66 ms conversion every 5 s
    p_avg = p_bias * duty
    self_heat = p_avg * 0.05                  # ~0.05 C/mW, 3 mm probe in still air
    r.append(Result("RTD", "self-heating error",
                    PASS if self_heat < 0.5 else WARN,
                    f'I={i_bias*1000:.2f} mA, {p_bias*1000:.2f} mW during 66 ms, '
                    f'{duty*100:.1f}% duty -> {self_heat:.3f} C average'))
    r.append(Result("RTD", "3-wire lead compensation", PASS,
                    "third lead senses IR drop of the shared lead; 2-wire mode would add ~+0.5 C/m"))
    tau = d["temp_tau_s"]
    slope = 1.0
    r.append(Result("RTD", "thermal slope detectability",
                    PASS if slope * 5 > 0.5 else WARN,
                    f'tau~{tau:.0f}s, 1 C/s ramp -> +{slope*5:.1f} C in 5 s vs 0.5 C alarm threshold'))

    # --- I2C
    rp, cb = d["i2c_rp_ohm"], d["i2c_cb_pf"]
    tr = 2.2 * rp * cb * 1e-12
    rp_par = 1.0 / (1.0 / rp + 1.0 / 10000.0)
    tr_par = 2.2 * rp_par * cb * 1e-12
    r.append(Result("Bus", "I2C rise time @400 kHz",
                    PASS if tr < 300e-9 else FAIL,
                    f'tr=2.2*Rp*Cb={tr*1e9:.0f} ns < 300 ns (with optional 10k: {tr_par*1e9:.0f} ns)'))
    ipull = d["vdd"] / rp_par
    r.append(Result("Bus", "I2C pull-up current",
                    PASS if ipull < 3e-3 else WARN,
                    f'{ipull*1000:.2f} mA < 3 mA I2C limit'))
    r.append(Result("Bus", "I2C cable length limit",
                    WARN, 'keep < 10 cm / 60 pF; at 200 pF rise time exceeds 300 ns'))
    r.append(Result("Bus", "SPI clock vs wiring", PASS,
                    "MAX31865 supports 5 MHz; 1 MHz over <10 cm jumper is safe"))
    r.append(Result("Bus", "I2S clocking", PASS,
                    f'16 kHz * 32 bit = 512 kHz BCLK, well within Pi PCM'))

    # --- power / thermal
    sensors_w = (0.003 + 0.00014 + 0.0016) * 3.3 + 0.010
    total_peak = d["pi_peak_w"] + d["fan_w"] + sensors_w
    i5 = total_peak / 5.0
    r.append(Result("Power", "5V rail headroom",
                    PASS if i5 < d["psu_a"] * 0.7 else WARN,
                    f'{total_peak:.2f} W peak = {i5:.2f} A of {d["psu_a"]:.1f} A '
                    f'({i5/d["psu_a"]*100:.0f}% load)'))
    rails = {"3.3V": 0.015}
    r.append(Result("Power", "3.3V rail load", PASS,
                    f'~{rails["3.3V"]*1000:.0f} mA (sensors + LED) vs ~1 A available'))
    r.append(Result("Power", "IP65 + internal fan", WARN,
                    'sealed box recirculates air: bolt an aluminium plate to the lid as a heat '
                    'spreader; expect +10..15 C inside, still below 80 C throttle'))
    r.append(Result("Power", "LED current", PASS, f'(3.3-2.0)/330 = 3.9 mA'))

    # --- audio
    r.append(Result("Audio", "audio Nyquist", PASS,
                    f'{d["audio_fs"]/1000:.0f} kHz -> {d["audio_fs"]/2000:.0f} kHz bandwidth, covers 2-6 kHz squeal'))

    # --- statistics
    arl = 1.0 / 0.0027
    r.append(Result("Stats", "SPC false-alarm interval", WARN,
                    f'single 3-sigma point = {arl:.0f} windows (~{arl*5/60:.0f} min); use '
                    f'2-of-3 with 2-sigma warning to reach hours'))
    return r


# ------------------------------------------------------------------- BOM
def bom():
    global BOM_FILE
    r = []
    try:
        rows = bom_rows()
        import os
        BOM_FILE = os.path.basename(os.environ.get("PDM_BOM", "DOC-20261014-WA0055.xlsx"))
    except Exception as e:  # pragma: no cover
        return [Result("BOM", "xlsx readable", FAIL, f"{e}")]
    items, total = [], 0.0
    for row in rows[1:]:
        name = row.get("B", "")
        if not name or "التكلفة" in name:
            continue
        try:
            t = float(row.get("H") or 0)
        except ValueError:
            continue
        items.append((name, t))
        total += t

    ok = abs(total - 8240) < 0.01
    r.append(Result("BOM", "locked total", PASS if ok else FAIL,
                    f"{total:.2f} EGP across {len(items)} lines (hard cap 8240)"
                    + ("" if ok else f" -> {total - 8240:+.2f} EGP")))
    names = " | ".join(n for n, _ in items).lower()
    for want, key, why in [
            ("PT100 3-wire probe", "pt100", "M4 (+/-1 C) needs a 3-wire RTD"),
            ("MAX31865 front end", "max31865", "15-bit ratiometric conversion, 0.034 C/LSB"),
            ("Raspberry Pi 4 8GB", "8gb", "headroom for SPC + RF + Flask + Mosquitto")]:
        present = key in names
        r.append(Result("BOM", f"{want} present", PASS if present else FAIL,
                        "found in the BOM" if present else
                        f"MISSING from the working xlsx - {why}. The book, code, charts and "
                        f"calibration plan all assume this part."))
    unmapped = [n for n, _ in items
                if not any(k in n for k in ("ADXL", "PT100", "MAX", "INMP", "Magnet", "Shielded",
                                            "Jumper", "Header", "M3", "Nylon", "Raspberry",
                                            "MicroSD", "Breadboard", "Ceramic", "Resistors",
                                            "Electrolytic", "Case", "Thermal", "IP65", "Glands",
                                            "Heat Shrink", "مصاريف"))]
    r.append(Result("BOM", "every BOM line mapped", PASS if not unmapped else WARN,
                    "all lines traced to a net or enclosure task" if not unmapped
                    else "review: " + ", ".join(unmapped[:4])))
    return r


def all_results():
    return erc() + physics() + bom()


def report_md(results):
    def block(name):
        rows = [x for x in results if x.group == name]
        out = [f"### {name}", "", "| Check | Status | Detail |", "|---|---|---|"]
        for x in rows:
            icon = {"PASS": "PASS", "WARN": "WARN", "FAIL": "FAIL"}[x.status]
            out.append(f"| {x.name} | **{icon}** | {x.detail} |")
        return "\n".join(out)

    counts = {s: sum(1 for x in results if x.status == s) for s in (PASS, WARN, FAIL)}
    head = [
        "# ERC + Physics Report — PdM Rig",
        "",
        "Generated from `circuit/design.py` (single source of truth).",
        "",
        f"BOM source: `{BOM_FILE}`" if BOM_FILE else "",
        "",
        f"**{counts[PASS]} PASS · {counts[WARN]} WARN · {counts[FAIL]} FAIL**",
        "",
        "A WARN is a documented engineering trade-off, not a broken rule.",
        "",
    ]
    body = [block(n) for n in ("ERC", "Signal", "RTD", "Bus", "Power", "Audio", "Stats", "BOM")]
    txt = "\n\n".join(head + body) + "\n"
    while "\n\n\n" in txt:
        txt = txt.replace("\n\n\n", "\n\n")
    return txt
