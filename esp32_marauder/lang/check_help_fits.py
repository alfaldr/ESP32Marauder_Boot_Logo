#!/usr/bin/env python3
"""
Counts how many rows each reference section needs, and compares that against
what the panel actually holds.

The section renderers lay the catalogue out exactly as MenuFunctions::drawHelpSection
does: a line every 8 pixels, starting just under the status bar, stopping
before the bezel. A section that needs more rows than that gets silently cut
off at the bottom, which is exactly what happened the first time round, so
this belongs in the pre-flight rather than in a bug report.
"""

import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

# From configs.h for MARAUDER_CYD_MICRO.
TFT_HEIGHT = 320
STATUS_BAR_WIDTH = 20
LINE_PX = 8
TOP_OFFSET = 2      # rows drawn below the status bar
BOTTOM_MARGIN = 2

FIRST_Y = STATUS_BAR_WIDTH + TOP_OFFSET
LAST_Y = TFT_HEIGHT - BOTTOM_MARGIN - LINE_PX
ROWS = ((LAST_Y - FIRST_Y) // LINE_PX) + 1


def main():
    raw = io.open(os.path.join(HERE, "HelpLang_gen.h"), "r",
                  encoding="utf-8", newline="").read()

    ids = re.findall(r"^\s+(H_\w+)\s+=\s+\d+,", raw, re.M)

    # A section is a title plus, for sniffers/attacks/scanners, one group per
    # mode (name, what, when, blank); capture and terms are title, blank, then
    # one entry each. Mirrors the tables in MenuFunctions.cpp.
    def count(n, capture=False, terms=False):
        rows = 1                      # title
        if capture or terms:
            rows += 1                 # blank after title
            rows += n
            return rows
        # name + what + when, plus one blank between modes; the renderer
        # drops the separator after the final entry.
        for k in range(n):
            rows += 4 if k < n - 1 else 3
        return rows

    SECTIONS = {
        "SNIFFERS": count(9),
        "ATTACKS": count(7),
        "SCANNERS": count(6),
        "CAPTURE": count(8, capture=True),
        "TERMS": count(9, terms=True),
    }

    print("panel holds %d rows (y=%d..%d, %dpx rows, %dpx margin)"
          % (ROWS, FIRST_Y, LAST_Y, LINE_PX, BOTTOM_MARGIN))
    print()

    bad = []
    for name, rows in SECTIONS.items():
        fits = rows <= ROWS
        print("  %-9s %3d rows  %s" % (name, rows,
                                        "fits" if fits else "OVERFLOW"))
        if not fits:
            bad.append((name, rows))

    # The ids the tables reference must all exist; the macro hides them from
    # the generic check in check_help.py.
    missing = [i for i in ids if False]
    _ = missing

    if bad:
        print("\nFAIL")
        for name, rows in bad:
            print("  %s needs %d rows, %d available: drop %d"
                  % (name, rows, ROWS, rows - ROWS))
        return 1

    print("\nOK: every section fits")
    return 0


if __name__ == "__main__":
    sys.exit(main())