"""setup_fz.py - install a sandbox copy of Fritzing 0.9.6 from Debian debs.

The .fzz audit needs the real Fritzing renderer (a headless ``-svg`` export),
so this helper downloads the official Debian binary packages and unpacks them
into ~/.cache/fzfz without touching the system.

    python3 setup_fz.py
"""
import os
import subprocess
import sys
import urllib.request

BASE = os.path.expanduser("~/.cache/fzfz")
DL = os.path.join(BASE, "dl")
DEBIAN = "https://deb.debian.org/debian/"

PKGS = (
    ("fritzing", "pool/main/f/fritzing/fritzing_0.9.6+dfsg-3_amd64.deb"),
    ("fritzing-data", "pool/main/f/fritzing/fritzing-data_0.9.6+dfsg-3_all.deb"),
    ("fritzing-parts", "pool/main/f/fritzing-parts/"
                       "fritzing-parts_0.9.6~unreleased-1_all.deb"),
    ("libssl1.1", "pool/main/o/openssl/libssl1.1_1.1.1w-0+deb11u1_amd64.deb"),
    ("libqt5serialport5", "pool/main/q/qtserialport-opensource-src/"
                          "libqt5serialport5_5.15.8-2_amd64.deb"),
    ("libgit2-1.5", "pool/main/libg/libgit2/"
                    "libgit2-1.5_1.5.1+ds-1+deb12u1_amd64.deb"),
    ("libmbedtls14", "pool/main/m/mbedtls/libmbedtls14_2.28.3-1_amd64.deb"),
    ("libmbedx509-1", "pool/main/m/mbedtls/libmbedx509-1_2.28.3-1_amd64.deb"),
    ("libmbedcrypto7", "pool/main/m/mbedtls/libmbedcrypto7_2.28.3-1_amd64.deb"),
    ("libhttp-parser2.9", "pool/main/h/http-parser/"
                          "libhttp-parser2.9_2.9.4-5_amd64.deb"),
)


def find_binary():
    prefs = [os.path.join(BASE, "usr", "bin", "fritzing.real")]
    found = []
    for root, _dirs, files in os.walk(BASE):
        for f in files:
            if f == "Fritzing" or f == "fritzing.real":
                found.append(os.path.join(root, f))
    for p in prefs:
        if os.path.exists(p):
            return p
    return found[0] if found else None


def main():
    os.makedirs(DL, exist_ok=True)
    for name, rel in PKGS:
        dest = os.path.join(DL, os.path.basename(rel))
        if not os.path.exists(dest) or os.path.getsize(dest) < 1024:
            url = DEBIAN + rel
            print("fetch", url, flush=True)
            urllib.request.urlretrieve(url, dest)
        subprocess.check_call(["dpkg-deb", "-x", dest, BASE])
    # locate the actual Qt binary; the package also ships a /usr/bin wrapper
    binary = find_binary()
    print("binary:", binary)
    if binary:
        proc = subprocess.run(["ldd", binary], capture_output=True, text=True)
        missing = [ln for ln in proc.stdout.splitlines() if "not found" in ln]
        print("missing libs:", missing or "none")
    print("installed to", BASE)


if __name__ == "__main__":
    sys.exit(main())
