#!/usr/bin/env python3
"""Compiles the syntax/ samples with the PlatformIO xtensa g++, without linking.

Two things this replaces:

* CI as the first place a C++ mistake surfaces. HELP_ROW kept two parameters
  while every call passed three, and nothing local noticed for a whole round
  trip. -fsyntax-only catches that in seconds, without needing the Arduino
  core that is not installed here.
* The belief that there was no local compiler at all. The toolchain is
  installed; it was just not on the PATH, and it targets xtensa, so a full
  link produces _close_r is not implemented warnings and a .exe that will not
  run. Syntax checking is the part that matters.

Run:  python tools/check_syntax.py
"""

import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Samples live next to the other scratch artefacts rather than in the repo:
# they are stand-ins for firmware code, not part of the firmware build.
SYNTAX = r"C:\Users\Admin\Desktop\marauder_boot\syntax"

GXX_CANDIDATES = [
    r"C:\Users\Admin\.platformio\packages\toolchain-xtensa-esp32\bin"
    r"\xtensa-esp32-elf-g++.exe",
]


def find_gxx():
    for path in GXX_CANDIDATES:
        if os.path.exists(path):
            return path
    return None


def main():
    gxx = find_gxx()
    if not gxx:
        print("UYARI: xtensa g++ bulunamadi, sozdizimi kontrolu atlandi")
        print("  aranan: %s" % GXX_CANDIDATES[0])
        return 0

    if not os.path.isdir(SYNTAX):
        print("sozdizimi ornegi yok: %s" % SYNTAX)
        return 0

    sources = sorted(f for f in os.listdir(SYNTAX) if f.endswith(".cpp"))
    if not sources:
        print("ornek yok")
        return 0

    failed = 0
    for name in sources:
        src = os.path.join(SYNTAX, name)
        proc = subprocess.run([gxx, "-std=c++11", "-fsyntax-only", src],
                              capture_output=True, text=True)
        ok = proc.returncode == 0
        print("  %-28s %s" % (name, "ok" if ok else "FAIL"))
        if not ok:
            failed += 1
            for line in proc.stderr.splitlines()[:6]:
                print("      " + line)

    print()
    if failed:
        print("HATA: %d / %d ornek derlenmedi" % (failed, len(sources)))
        return 1
    print("OK: %d ornek sozdizimini gecti" % len(sources))
    return 0


if __name__ == "__main__":
    sys.exit(main())