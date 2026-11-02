"""Build the Fritzing sketch, validate connectivity, package the .fzz."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import routes
from layout import Layout
from fzz import Sketch

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "PDM_Predictive_Maintenance.fzz")


def main():
    lay = Layout()
    r = routes.build(lay)
    sk = Sketch(lay, r)
    ok, problems = sk.check()
    for p in problems:
        print("PROBLEM:", p)
    print(f"wires={len(sk.wires)} instances={len(lay.views)+1} "
          f"holes={len(sk.used_holes)} nets={len(r)}")
    if not ok:
        return 1
    sk.bundle(OUT)
    print("wrote", OUT, os.path.getsize(OUT), "bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
