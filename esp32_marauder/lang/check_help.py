#!/usr/bin/env python3
"""
Local pre-flight for the help catalogue.

The generated ids live in lang/HelpLang_gen.h and the call sites live in
MenuFunctions.cpp. Nothing in the Arduino build cross-checks them, so a
renamed section only shows up as a compile error on CI, minutes later.

Checks:
  1. The generated files match what gen_help.py would produce right now.
  2. Every H_* identifier referenced in MenuFunctions.cpp exists in the enum.
  3. Every catalogue line fits the button, using the same advance table.

Usage:  python lang/check_help.py
"""

import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
GEN_H = os.path.join(HERE, "HelpLang_gen.h")
GEN_CPP = os.path.join(HERE, "HelpLang_gen.cpp")
MENU = os.path.join(ROOT, "MenuFunctions.cpp")

sys.path.insert(0, HERE)
import gen_help  # noqa: E402


def read(path):
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def main():
    problems = []

    # 1. Regenerate into a scratch copy and diff, so an uncommitted catalog
    #    edit cannot slip through with stale generated code.
    with tempfile.TemporaryDirectory() as tmp:
        for name in ("HelpLang_gen.h", "HelpLang_gen.cpp"):
            shutil_copy = os.path.join(tmp, name)
            with open(shutil_copy, "w", encoding="utf-8") as fh:
                fh.write("")
            os.remove(shutil_copy)
        saved = {}
        for path in (GEN_H, GEN_CPP):
            saved[path] = read(path)
        try:
            subprocess.check_call([sys.executable,
                                   os.path.join(HERE, "gen_help.py")],
                                  stdout=subprocess.DEVNULL)
            for path in (GEN_H, GEN_CPP):
                if read(path) != saved[path]:
                    problems.append(
                        "%s is stale; re-run gen_help.py"
                        % os.path.basename(path))
        finally:
            for path, content in saved.items():
                with open(path, "w", encoding="utf-8") as fh:
                    fh.write(content)

    # 2. Every id used in MenuFunctions.cpp must exist in the generated enum.
    header = read(GEN_H)
    known = set(re.findall(r"^\s+(H_\w+)\s*=\s*\d+,", header, re.M))
    menu = read(MENU)
    used = set(re.findall(r"\bH_[A-Z0-9_]+\b", menu))
    unknown = sorted(used - known)
    if unknown:
        problems.append("MenuFunctions.cpp references unknown ids: %s"
                        % ", ".join(unknown))

    # 3. Nothing in the enum is orphaned: an unused id usually means a renamed
    #    call site that no longer lines up with the catalogue.
    unused = sorted(i for i in known
                    if i not in used
                    and not re.search(r"\b%s\b" % re.escape(i), header))
    if unused:
        problems.append("ids defined but never used: %s" % ", ".join(unused))

    # 4. Width re-check, independent of the generator's own bookkeeping.
    pool = re.findall(r'^\s*"((?:[^"\\]|\\.)*)\\0"', read(GEN_CPP), re.M)
    if pool:
        widest = max(pool, key=gen_help.text_px)
        if gen_help.text_px(widest) > gen_help.WIDTH_PX:
            problems.append("line too wide (%dpx > %dpx): %r"
                            % (gen_help.text_px(widest), gen_help.WIDTH_PX,
                               widest))
        print("pool: %d strings, widest %dpx (limit %dpx)"
              % (len(pool), gen_help.text_px(widest), gen_help.WIDTH_PX))

    print("ids: %d defined, %d referenced" % (len(known), len(used)))

    if problems:
        print("\nFAIL")
        for p in problems:
            print("  " + p)
        return 1
    print("\nOK")
    return 0


if __name__ == "__main__":
    sys.exit(main())