#!/usr/bin/env python3
"""
Finds string literals that contain characters the menu font cannot draw.

TFT_eSPI's packed fonts cover 0x20..0x7E. For a code point outside that range
drawChar computes the glyph index as (uniCode - font->first) and indexes the
glyph table with no bounds check, so anything above 0x7E reads past the end of
the table. The xAdvance and xHeight it then picks up are whatever bytes
happened to be there, and the draw loop runs for that many rows -- enough to
hang a frame, overrun a buffer, or panic.

The reference catalogue is generated and already rejects non-ASCII, but text
hand-written elsewhere in the firmware is not covered by that check, so this
sweeps the whole sketch.

Usage:  python tools/check_ascii_strings.py [sketch_dir]
"""

import os
import re
import sys

SKETCH = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "esp32_marauder")

SKIP_DIRS = {".git", "__pycache__"}
# The generated catalogue is validated by gen_help.py against the same rule,
# and these are serial-only or comment text.
COMMENT = re.compile(r"^\s*(//|\*|/\*|#)")

LITERAL = re.compile(r'"((?:[^"\\]|\\.)*)"')


def main():
    root = os.path.abspath(SKETCH)
    hits = []
    scanned = 0

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in sorted(filenames):
            if not name.endswith((".cpp", ".h", ".ino")):
                continue
            path = os.path.join(dirpath, name)
            rel = os.path.relpath(path, root)
            scanned += 1
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                for lineno, line in enumerate(fh, 1):
                    if COMMENT.match(line):
                        continue
                    for m in LITERAL.finditer(line):
                        body = m.group(1)
                        bad = sorted({c for c in body if ord(c) > 0x7E})
                        if bad:
                            # Decode the C escapes we might have mangled.
                            shown = "".join(
                                "\\x%02x" % ord(c) if ord(c) > 0x7F else c
                                for c in body)
                            hits.append((rel, lineno, shown,
                                         "".join(bad)))
                            break

    print("scanned %d files under %s" % (scanned, root))
    if not hits:
        print("\nOK: every string literal is ASCII")
        return 0

    print("\n%d string literal(s) the menu font cannot draw:\n" % len(hits))
    for rel, lineno, shown, bad in hits:
        print("  %s:%d" % (rel, lineno))
        print("      %s" % shown)
        print("      offending: %s\n" % " ".join("U+%04X" % ord(c) for c in bad))
    print("These reach the display through addNodes or tft.print. Replace them")
    print("with a plain ASCII transliteration; the font has no glyph above 0x7E")
    print("and TFT_eSPI indexes its glyph table without a bounds check.")
    return 1


if __name__ == "__main__":
    sys.exit(main())