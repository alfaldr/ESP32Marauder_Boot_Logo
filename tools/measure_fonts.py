#!/usr/bin/env python3
"""
Measures how much text actually fits in a CYD menu button.

TFT_eSPI stores each glyph as
  { bitmapOffset, width, height, advanceWidth, leftSideBearing, topSideBearing }
so the real rendered width of a string is the sum of its advances. This pulls
the four candidate fonts out of the TFT_eSPI tree and reports that number for
strings the reference actually uses, rather than guessing from the point size.

CYD geometry: TFT_WIDTH 240, BUTTON_PADDING 22 each side -> 196 px usable.
"""

import re
import sys
import urllib.request

AVAILABLE_WIDTH = 240 - 2 * 22

FONTS = ["FreeMono9pt7b", "FreeSans9pt7b", "FreeSansBold9pt7b", "FreeSerif9pt7b"]

SAMPLES = [
    "WiFi>Sniffers>",
    "EAPOL/PMKID Scan",
    "Beacon Tarama",
    "Lists nearby access points",
    "Dort yonlu anahtari kaydeder",
]

BASE = "https://raw.githubusercontent.com/Bodmer/TFT_eSPI/master/Fonts/GFXFF/%s.h"


def fetch(name):
    url = BASE % name
    req = urllib.request.Request(url, headers={"User-Agent": "opencode"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("utf-8", "replace")


def parse_glyphs(text):
    i = text.find("Glyphs[]")
    if i < 0:
        return None
    seg = text[i:]
    out = {}
    # Trailing // 0xNN 'c' comment gives us the code point directly.
    for m in re.finditer(
            r"\{\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,[^}]*\}\s*,\s*"
            r"//\s*(0x[0-9A-Fa-f]+)", seg):
        out[int(m.group(5), 16)] = int(m.group(4))
    return out


def text_width(glyphs, s):
    total = 0
    for ch in s:
        adv = glyphs.get(ord(ch))
        if adv is None:
            adv = glyphs.get(ord("?"), 0)
        total += adv
    return total


def main():
    print("CYD menu button: %d px usable (KEY_W 240 - 2 x BUTTON_PADDING 22)"
          % AVAILABLE_WIDTH)
    print()
    table = {}

    for name in FONTS:
        try:
            glyphs = parse_glyphs(fetch(name))
        except Exception as exc:                       # network, 404, ...
            print("%-20s ALINAMADI (%s)" % (name, exc))
            continue
        if not glyphs:
            print("%-20s metrik cozulemedi" % name)
            continue
        table[name] = glyphs

    if not table:
        sys.exit("no font metrics could be read")

    for name, glyphs in table.items():
        advs = [glyphs[c] for c in glyphs if 97 <= c <= 122]  # a-z
        advs.sort()
        print("%-20s kucuk harf ilerleme: medyan %d px" % (name, advs[len(advs) // 2]))

    print()
    header = "%-26s" % "ornek metin" + "".join("%22s" % n[:14] for n in table)
    print(header)
    print("-" * len(header))
    for s in SAMPLES:
        row = "%-26s" % ("\"" + s + "\"")
        for name in table:
            w = text_width(table[name], s)
            fits = w <= AVAILABLE_WIDTH
            row += "%16d px%s" % (w, " ok" if fits else " TASMA")
        print(row)

    print()
    for name in table:
        # How many of the longest realistic line fit?
        n = 0
        w = 0
        for ch in "WiFi>Sniffers>EAPOL/PMKID Tarama":
            adv = table[name].get(ord(ch), 0)
            if w + adv > AVAILABLE_WIDTH:
                break
            w += adv
            n += 1
        print("%-20s sabit 9pt yukseklikte kalan karakter: %d" % (name, n))


if __name__ == "__main__":
    main()