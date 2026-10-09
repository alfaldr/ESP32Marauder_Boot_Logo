#!/usr/bin/env python3
"""Fails if any string literal in the firmware sources contains a non-ASCII byte.

The reason this exists: TFT_eSPI indexes its glyph table from a char without
bounds checking. A character outside the font's range -- U+015E for instance --
reads past the end of the table, so xAdvance and xHeight come out of whatever
happens to be in memory and the drawing loop walks off the end of the buffer.
That was a panic once, and it happened in the boot log text before anyone
thought to check what characters were in it.

So the rule is simple and absolute: string literals stay ASCII. Turkish is written
with the closest ASCII equivalents -- s for s, i for i, g for g, c for c, o for o,
u for u -- which is also what gets produced when someone types on a phone
keyboard without a Turkish layout.

What counts as a string literal is deliberately conservative. Char arrays used as
lookup tables are included, because they end up in drawString calls. Comments are
skipped: a Turkish comment is fine, only rendered text is a problem, and this
repository has plenty of correctly spelled Turkish in its notes.
"""

import os
import re
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                    "esp32_marauder")

SCAN = (".cpp", ".h", ".ino")

# A double-quoted run with no closing quote on the same line, or one with an odd
# number of backslashes before it, is escaped and not what this wants to catch.
STRING = re.compile(r'"((?:[^"\\\n]|\\.)*)"')


def check(path):
    problems = []
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        for lineno, line in enumerate(fh, 1):
            # Strip comments before looking at literals, so a quote inside a
            # comment is not read as one.
            code = re.sub(r"//.*$", "", line)
            code = re.sub(r"/\*.*?\*/", "", code)
            for m in STRING.finditer(code):
                for ch in m.group(1):
                    if ord(ch) > 126:
                        problems.append((lineno, ch, ord(ch), line.strip()))
                        break
    return problems


def main():
    files = []
    for base, _, names in os.walk(ROOT):
        for n in names:
            if n.endswith(SCAN):
                files.append(os.path.join(base, n))

    total = 0
    for path in sorted(files):
        rel = os.path.relpath(path, os.path.dirname(ROOT))
        for lineno, ch, code, text in check(path):
            print("%s:%d  U+%04X  %s" % (rel, lineno, code, text[:70]))
            total += 1

    print("scanned %d files under %s" % (len(files), ROOT))
    print()
    if total:
        print("HATA: %d non-ASCII string literal" % total)
        return 1
    print("OK: every string literal is ASCII")
    return 0


if __name__ == "__main__":
    sys.exit(main())
