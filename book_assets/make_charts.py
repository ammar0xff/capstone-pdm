"""Regenerate the two charts that depend on the design numbers.

Run:  python3 book_assets/make_charts.py
Needs matplotlib (already used for the other charts).
"""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
NAVY, BLUE, AMBER, RED, TEAL, MUTED = "#0f2a44", "#2471a3", "#b9770e", "#922b21", "#117a65", "#5d6d7e"


def tc_curve():
    # NIST ITS-90 type-K reference values (mV) - table points, not a fitted guess
    t = np.array([0, 100, 200, 300, 400, 500], dtype=float)
    emf = np.array([0.000, 4.096, 8.138, 12.209, 16.397, 20.644])
    tt = np.linspace(0, 500, 400)
    ee = np.interp(tt, t, emf)

    fig, (a1, a2) = plt.subplots(1, 2, figsize=(12.4, 4.6), dpi=170)
    a1.plot(tt, ee, color=AMBER, lw=2.4)
    a1.plot(t, emf, "o", color=NAVY, ms=5)
    a1.axvspan(20, 90, color=TEAL, alpha=0.10)
    a1.text(55, 17.2, "motor band\n20-90 C", ha="center", color=TEAL, fontsize=8.5)
    a1.annotate("4.096 mV @ 100 C", xy=(100, 4.096), xytext=(150, 2.2),
                arrowprops=dict(arrowstyle="->", color=MUTED, lw=1), fontsize=9, color=NAVY)
    a1.set_xlabel("junction temperature (C)")
    a1.set_ylabel("thermocouple EMF (mV)")
    a1.set_title("Seebeck: V = S(T_hot - T_cold), S = 41 uV/C", color=NAVY, fontsize=11, weight="bold")
    a1.grid(alpha=0.25)
    a1.set_xlim(0, 500)

    # error envelope: RSS of the parts that do not cancel
    for label, probe, cj, lin, res, col, ls in [
        ("class 1 probe: RSS 1.68 C", 1.5, 0.5, 0.5, 0.25, TEAL, "-"),
        ("class 2 probe: RSS 2.62 C", 2.5, 0.5, 0.5, 0.25, RED, "--"),
    ]:
        env = np.sqrt(probe**2 + cj**2 + lin**2 + res**2)
        a2.axhline(env, color=col, ls=ls, lw=2, label=label)
    a2.axhline(2.0, color=AMBER, lw=1.2, ls=":", label="M4 restated = +/-2.0 C")
    a2.axhline(2.5, color=MUTED, lw=1.0, ls=":", label="M4 if a class-2 probe is used")
    a2.axvspan(20, 90, color=TEAL, alpha=0.10)
    a2.set_ylim(0, 3.2)
    a2.set_xlim(0, 500)
    a2.set_xlabel("junction temperature (C)")
    a2.set_ylabel("worst-case error (C)")
    a2.set_title("What the BOM can actually deliver", color=NAVY, fontsize=11, weight="bold")
    a2.legend(fontsize=8.2, loc="lower right", frameon=True)
    a2.grid(alpha=0.25)
    a2.text(10, 2.95, "the probe class, not the ADC, decides M4", fontsize=8.5, color=RED)

    fig.suptitle("K-type thermocouple + MAX6675 - signal size and honest error budget",
                 color=NAVY, fontsize=13, weight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(os.path.join(HERE, "tc_curve.png"), facecolor="white")
    plt.close(fig)


def budget():
    """Real 2026-10-25 quotes against the self-set 8240 target."""
    rows = [
        ("Compute (Pi 4 4GB + SD + PSU)", 7499.00, NAVY),
        ("Sensors (ADXL + K-type + mic)", 600.00, AMBER),
        ("Wiring + decoupling", 353.75, BLUE),
        ("Shipping (4 stores)", 220.00, MUTED),
        ("Enclosure + mounting", 215.50, TEAL),
    ]
    labels = [r[0] for r in rows]
    vals = [r[1] for r in rows]
    cols = [r[2] for r in rows]
    total = sum(vals)

    fig, ax = plt.subplots(figsize=(11.4, 4.9), dpi=170)
    y = np.arange(len(rows))[::-1]
    ax.barh(y, vals, color=cols, height=0.60)
    for yy, v in zip(y, vals):
        ax.text(v + 70, yy, f"{v:,.0f} EGP ({v / total * 100:.0f}%)", va="center",
                fontsize=9, color=NAVY)
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=9.5)
    ax.axvline(8240, color=RED, lw=2)
    ax.text(8240, len(rows) - 0.35, " self-set target 8240", color=RED,
            fontsize=9.5, weight="bold", va="center")
    ax.axvspan(8240, total, color=RED, alpha=0.07)
    ax.annotate(f"+{total - 8240:,.2f} EGP over\nbefore the MAX6675",
                xy=(total, 0.02), xytext=(total - 1500, 0.55),
                fontsize=9.5, color=RED, weight="bold",
                arrowprops=dict(arrowstyle="->", color=RED, lw=1.2))
    ax.text(120, -0.62, "MAX6675 has no quote yet - the real gap is larger than shown",
            fontsize=8.5, color=MUTED, va="center")
    ax.set_xlim(0, 9800)
    ax.set_ylim(-1.0, len(rows) - 0.2)
    ax.set_xlabel("EGP")
    ax.set_title(f"Real quotes {total:,.2f} EGP vs the 8240 target - the Pi is 77% of the spend",
                 color=NAVY, fontsize=12.2, weight="bold")
    ax.grid(axis="x", alpha=0.25)
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "budget.png"), facecolor="white")
    plt.close(fig)


if __name__ == "__main__":
    tc_curve()
    budget()
    print("wrote tc_curve.png and budget.png")
