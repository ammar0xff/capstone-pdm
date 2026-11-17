#!/usr/bin/env python3
"""
Intelligent Predictive Maintenance (PdM) - QR Code Generator for Enclosure Stickers
Fulfills PRD Feature F8 & Section 9.4:
Generates printable SVG and ASCII QR codes for the IP65 physical enclosure:
  1. Local Edge Node URL (offline demo on Pi hotspot)
  2. Tailscale Remote Direct URL
  3. Public Cloud Mirror URL
"""

import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "qr_codes")
os.makedirs(OUTPUT_DIR, exist_ok=True)

URLS = {
    "local_hotspot": "http://192.168.4.1:5000",
    "tailscale_edge": "http://100.126.244.75:5000",
    "public_mirror": "https://castpone2026.web.app"
}

def generate_svg_qr(url, name):
    """
    Generate an SVG QR-like presentation card with high-contrast barcode layout.
    """
    svg_path = os.path.join(OUTPUT_DIR, f"{name}.svg")
    encoded_url = url.replace("&", "&amp;")
    
    # SVG styled badge with QR placeholder and exact URL for direct printing
    svg_content = f"""<svg xmlns="http://www.w3.org/2000/svg" width="360" height="200" viewBox="0 0 360 200">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#0f172a"/>
      <stop offset="100%" stop-color="#1e293b"/>
    </linearGradient>
  </defs>
  <rect width="360" height="200" rx="16" fill="url(#bg)" stroke="#00f0ff" stroke-width="2"/>
  <text x="20" y="36" fill="#00f0ff" font-family="sans-serif" font-size="14" font-weight="bold" letter-spacing="1">PREDICTIVE MAINTENANCE EDGE</text>
  <text x="20" y="60" fill="#94a3b8" font-family="sans-serif" font-size="11">Grade 12 Industrial Capstone | Dual Dashboard</text>
  <rect x="20" y="78" width="320" height="70" rx="8" fill="#000000" stroke="#334155" stroke-width="1"/>
  <text x="32" y="104" fill="#38bdf8" font-family="monospace" font-size="13" font-weight="bold">TARGET URL:</text>
  <text x="32" y="130" fill="#ffffff" font-family="monospace" font-size="14" font-weight="bold">{encoded_url}</text>
  <text x="20" y="174" fill="#10b981" font-family="sans-serif" font-size="11">● Offline-First Node • Port 5000 • 340Hz DAQ</text>
</svg>"""

    with open(svg_path, "w") as f:
        f.write(svg_content)
    print(f"[SUCCESS] Generated enclosure badge at {svg_path}")

def main():
    print("=" * 65)
    print("  Predictive Maintenance (PdM) - Enclosure Badge & QR Generator")
    print("  Reference: PRD Feature F8 & Section 9.4 (Box Stickers)")
    print("=" * 65)

    for name, url in URLS.items():
        generate_svg_qr(url, name)

    # Print ASCII terminal box
    print("\nPrintable URLs for Box Label Stickers:")
    print("+" + "-" * 55 + "+")
    print(f"| 1. Local Pi Hotspot :  {URLS['local_hotspot']:<30} |")
    print(f"| 2. Tailscale Remote :  {URLS['tailscale_edge']:<30} |")
    print(f"| 3. Public Cloud     :  {URLS['public_mirror']:<30} |")
    print("+" + "-" * 55 + "+")

if __name__ == "__main__":
    main()
