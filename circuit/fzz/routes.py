"""routes.py - every wire, net by net.

All on-board endpoints are **holes**, not part pins: a pin that is plugged into
a hole is connected to that hole by an explicit `<connect>` edge, so the wire
only has to reach the hole.  That also keeps the routes on the 9-unit grid.

Routing rules used here
-----------------------
* signals leave a row-J pin downwards to a private lane in the free band
  between the Z rail (y=180) and the Pi header (y=258), using a mid-gap
  column (x = hole + 4.5) so the vertical never runs through a rail hole;
* a rail tap drops to y=175.5 (between Y and Z) before crossing to the target
  rail hole, so a GND wire never grazes a 3V3 hole;
* the two rail pairs are bridged once, 3V3 on the left edge and GND on the
  right edge, outside the hole columns.
"""
from __future__ import annotations

import re


def build(lay):
    H = lay.hole
    V = lay.views
    R = {}

    def add(net, *pts):
        R.setdefault(net, []).append([(round(x, 4), round(y, 4)) for x, y in pts])

    def pin(ref, name):
        v = V[ref]
        cid = v.pinmap[name]
        hid = v.holes.get(cid)
        if hid:
            m = re.fullmatch(r"([A-Z]+)(\d+)", hid)
            return H(m.group(1), int(m.group(2)))
        return v.tip(cid)

    def mid(x):
        return round(x + 4.5, 4)

    # ---- power taps ---------------------------------------------------
    def tap_y(net, p, ycol):
        x, y = p
        target = H("Y", ycol)
        if abs(target[0] - x) < 0.01:
            add(net, p, target)
        else:
            add(net, p, (x, 160), (target[0], 160), target)

    def tap_z(net, p, zcol):
        x, y = p
        xm = mid(x)
        target = H("Z", zcol)
        add(net, p, (x, 160), (xm, 160), (xm, 175.5), (target[0], 175.5), target)

    def cap_tap(net, p, rail, col, side):
        """Cap leg -> under the cap -> up a lane beside the cap body/label.

        ``side`` is -1 for the left leg and +1 for the right leg.  The lane is
        half a pitch outside the leg, so the vertical clears both the cap body
        and the label printed above the cap.
        """
        x, y = p
        xm = round(x + side * 4.5, 4)
        target = H(rail, col)
        add(net, p, (x, 84), (xm, 84), (xm, target[1]), target)

    # ---- signals ------------------------------------------------------
    def signal(net, src, exit_x, lane_y, dst, odd_off=4.5):
        """source row-J pin -> lane -> Pi header pin (odd pins enter from the side)."""
        sx, sy = src
        dx, dy = dst
        if abs(dst[1] - 257.904) < 0.01:      # even header row
            add(net, src, (sx, 150), (exit_x, 150), (exit_x, lane_y),
                (dx, lane_y), dst)
        else:                                  # odd header row
            xm = round(dx + odd_off, 4)
            add(net, src, (sx, 150), (exit_x, 150), (exit_x, lane_y),
                (xm, lane_y), (xm, dy), dst)

    # ==================================================================
    # 3V3
    # ==================================================================
    tap_y("3V3", pin("U2", "VCC"), 4)
    tap_y("3V3", pin("U2", "CS"), 5)
    tap_y("3V3", pin("U3", "VIN"), 23)
    tap_y("3V3", pin("U4", "VDD"), 15)
    cap_tap("3V3", pin("C1", "1"), "W", 4, -1)
    cap_tap("3V3", pin("C2", "1"), "W", 7, -1)
    cap_tap("3V3", pin("C3", "1"), "W", 10, -1)
    cap_tap("3V3", pin("C4", "1"), "W", 14, +1)
    tap_y("3V3", pin("R2", "1"), 38)
    # Pi 3V3 pins are on the odd header row; cross the GND rail in a gap
    p = pin("U1", "3V3_A")
    add("3V3", p, (mid(p[0]), p[1]), (mid(p[0]), 175.5), (p[0], 175.5), H("Y", 21))
    p = pin("U1", "3V3_B")
    add("3V3", p, (mid(p[0]), p[1]), (mid(p[0]), 175.5), (p[0], 175.5), H("Y", 29))
    # 3V3 bridges: left edge W<->Y, plus the mid-board gap in both rails
    add("3V3", H("W", 1), (27, H("W", 1)[1]), (27, H("Y", 1)[1]), H("Y", 1))
    add("3V3", H("W", 29), H("W", 32))
    add("3V3", H("Y", 29), H("Y", 32))

    # ==================================================================
    # GND
    # ==================================================================
    tap_z("GND", pin("U2", "GND"), 3)
    tap_z("GND", pin("U2", "SDO"), 8)
    tap_z("GND", pin("U3", "GND"), 23)
    tap_z("GND", pin("U4", "GND"), 16)
    tap_z("GND", pin("U4", "LR"), 17)
    cap_tap("GND", pin("C1", "2"), "X", 5, +1)
    cap_tap("GND", pin("C2", "2"), "X", 8, +1)
    cap_tap("GND", pin("C3", "2"), "X", 11, +1)
    cap_tap("GND", pin("C4", "2"), "X", 13, -1)
    tap_z("GND", pin("D1", "K"), 42)
    # Pi GND, even pins: straight up to the Z rail
    for name, col in (("GND_6", 23), ("GND_14", 27)):
        add("GND", pin("U1", name), H("Z", col))
    # Pi GND, odd pins: enter between the columns, then tap the rail
    for name, zcol in (("GND_9", 26), ("GND_25", 34), ("GND_39", 41)):
        p = pin("U1", name)
        add("GND", p, (mid(p[0]), p[1]), (mid(p[0]), 180), H("Z", zcol))
    # fan return: straight left from the lead, then up to the nearest rail hole
    add("GND", pin("F1", "N"), (H("Z", 58)[0], pin("F1", "N")[1]), H("Z", 58))
    # GND bridges: right edge X<->Z, plus the mid-board gap in both rails.
    # The bridge runs just outside the board's right edge so the printed row
    # letters A..J (x=586..589) next to the rail holes stay readable.
    add("GND", H("X", 60), (604, H("X", 60)[1]), (604, H("Z", 60)[1]), H("Z", 60))
    add("GND", H("X", 29), H("X", 32))
    add("GND", H("Z", 29), H("Z", 32))

    # ==================================================================
    # 5V - direct Pi pin 4 to the fan, no rail
    # ==================================================================
    add("5V", pin("U1", "5V"), (pin("U1", "5V")[0], 246), (610, 246),
        (610, 215), pin("F1", "P"))

    # ==================================================================
    # signals
    # ==================================================================
    signal("I2C_SDA", pin("U2", "SDA"), mid(pin("U2", "SDA")[0]), 190, pin("U1", "SDA"))
    signal("I2C_SCL", pin("U2", "SCL"), mid(pin("U2", "SCL")[0]), 194.5, pin("U1", "SCL"))
    signal("I2S_BCLK", pin("U4", "BCLK"), mid(pin("U4", "BCLK")[0]), 199, pin("U1", "BCLK"))
    signal("SPI_MISO", pin("U3", "SO"), mid(pin("U3", "SO")[0]), 203.5, pin("U1", "MISO"))
    signal("SPI_SCLK", pin("U3", "SCLK"), mid(pin("U3", "SCLK")[0]), 208, pin("U1", "SCLK"))
    signal("I2S_WS", pin("U4", "WS"), mid(pin("U4", "WS")[0]), 217, pin("U1", "WS"))
    signal("I2S_SD", pin("U4", "SD"), mid(pin("U4", "SD")[0]), 226, pin("U1", "DIN"))

    # SPI_CS0: U3.CS -> CE0, with the 10k pull-up branching off the same net.
    cs = pin("U3", "CS")
    ce0 = pin("U1", "CE0")
    add("SPI_CS0", cs, (cs[0], 150), (mid(cs[0]), 150), (mid(cs[0]), 212.5),
        (ce0[0], 212.5), ce0)
    r2 = pin("R2", "2")
    add("SPI_CS0", r2, (r2[0], 150), (mid(r2[0]), 150), (mid(r2[0]), 212.5),
        (ce0[0], 212.5))

    # LED: GPIO16 -> R4.1 -> R4.2 -> D1.A ; D1.K -> GND
    r41 = pin("R4", "1")
    led = pin("U1", "LED")
    add("LED_A", r41, (r41[0], 150), (mid(r41[0]), 150), (mid(r41[0]), 242),
        (led[0], 242), led)
    r42 = pin("R4", "2")
    da = pin("D1", "A")
    add("LED_K", r42, (r42[0], 150), (da[0], 150), da)

    # ==================================================================
    # thermocouple
    # ==================================================================
    add("TC_P", pin("U3", "TP"), pin("R1", "P"))
    # TC_N drops to y=128.5 (between the printed G and H row letters) so it
    # never runs through the "G" leg-end text on the right edge.
    tn = pin("U3", "TN")
    add("TC_N", tn, (tn[0] + 6.65, tn[1]), (tn[0] + 6.65, 128.5),
        (pin("R1", "N")[0], 128.5), pin("R1", "N"))

    return R


if __name__ == "__main__":
    from layout import Layout
    lay = Layout()
    r = build(lay)
    for net, segs in r.items():
        print(net, len(segs), "segments")
