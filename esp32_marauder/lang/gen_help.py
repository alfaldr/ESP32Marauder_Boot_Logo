#!/usr/bin/env python3
"""
Generates the help catalogue from the per-language source files in this folder.

Each language is one plain-text file a translator can edit without touching
code:

    [sniffers]
    title = WiFi > Koklayicilar

    [sniffers.beacon]
    name  = Beacon Tarama
    what  = Cevredeki tum erisim noktalarini listeler ve birer beacon saklar.
    when  = Once hedef BSSID'i bulmak icin kullanilir.

Full sentences go in; this script wraps them to fixed-width lines, because the
menu clips anything wider than HELP_LINE_MAX and scrolls it sideways. Hand
wrapping silently regresses the moment a sentence is edited, so it happens here
and CI fails the build if anything cannot fit.

Every wrapped line gets its own id (H_X, H_X_2, H_X_3, ...) so the menu adds
one node per line and nothing ever scrolls.

Outputs HelpLang_gen.h (enum + helpLines) and HelpLang_gen.cpp (pool + table).

The menu font is ASCII-only, so non-ASCII in a source file is a hard error
rather than a surprise on screen.
"""

import os
import sys
from collections import OrderedDict

HERE = os.path.dirname(os.path.abspath(__file__))

# Usable width inside a CYD menu button: KEY_W 240 - 2 x BUTTON_PADDING 22.
# Changing either constant in configs.h means changing this.
WIDTH_PX = 196

# Advance width per glyph, in pixels, for the menu font (FreeSans9pt7b).
# Read straight out of the font's Glyphs table in Bodmer/TFT_eSPI. Wrapping by
# character count would be wrong: 'W' costs 17px while 'i' costs 4px, so the
# same line length can overflow or waste most of the row depending on the
# letters in it.
ADVANCE = {}
for _pair in (
        "20:5,21:6,22:6,23:10,24:10,25:16,26:12,27:4,28:6,29:6,2A:7,2B:11,2C:5,"
        "2D:6,2E:5,2F:5,30:10,31:10,32:10,33:10,34:10,35:10,36:10,37:10,38:10,"
        "39:10,3A:5,3B:5,3C:11,3D:11,3E:11,3F:10,40:18,41:12,42:12,43:13,44:13,"
        "45:11,46:11,47:14,48:13,49:5,4A:10,4B:12,4C:10,4D:15,4E:13,4F:14,50:12,"
        "51:14,52:13,53:12,54:11,55:13,56:12,57:17,58:12,59:12,5A:11,5B:5,5C:5,"
        "5D:5,5E:8,5F:10,60:5,61:10,62:10,63:9,64:10,65:10,66:5,67:10,68:10,69:4,"
        "6A:4,6B:9,6C:4,6D:15,6E:10,6F:10,70:10,71:10,72:6,73:9,74:5,75:10,76:9,"
        "77:13,78:9,79:9,7A:9,7B:6,7C:4,7D:6").split(","):
    _c, _w = _pair.split(":")
    ADVANCE[int(_c, 16)] = int(_w)

DEFAULT_ADVANCE = ADVANCE[ord("?")]


def text_px(s):
    return sum(ADVANCE.get(ord(c), DEFAULT_ADVANCE) for c in s)

LANGS = OrderedDict([
    ("LANG_EN", "help.en.txt"),
    ("LANG_TR", "help.tr.txt"),
])

LANG_LABEL = {"LANG_EN": "English", "LANG_TR": "Turkce"}


def split_path(word, width):
    """Breaks an over-long token at '>' boundaries, keeping the '>' attached.

    Menu paths are written without spaces ('WiFi>Sniffers>EAPOL/PMKID'), so
    greedy wrapping cannot touch them. Splitting after each '>' gives the same
    result a person would: the path continues on the next line.
    """
    pieces = word.split(">")
    out = []
    cur = ""
    for i, p in enumerate(pieces):
        piece = p + ">" if i < len(pieces) - 1 else p
        if text_px(piece) > width:
            return None
        if not cur:
            cur = piece
        elif text_px(cur + piece) <= width:
            cur += piece
        else:
            out.append(cur)
            cur = piece
    if cur:
        out.append(cur)
    return out


def wrap(text, width):
    """Greedy wrap on rendered pixel width. Returns lines, or None if a word
    cannot fit on a line of its own."""
    words = text.split()
    if not words:
        return []

    # Pre-split any over-long token that can be broken at '>'.
    tokens = []
    for w in words:
        if text_px(w) > width:
            pieces = split_path(w, width)
            if pieces is None:
                return None
            tokens.extend(pieces)
        else:
            tokens.append(w)

    lines, cur = [], ""
    for w in tokens:
        if not cur:
            if text_px(w) > width:
                return None
            cur = w
        elif text_px(cur + " " + w) <= width:
            cur += " " + w
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def parse(path):
    """key -> list of sentences."""
    out = OrderedDict()
    section = None
    field = None
    with open(path, "r", encoding="utf-8") as fh:
        for lineno, raw in enumerate(fh, 1):
            stripped = raw.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if stripped.startswith("[") and stripped.endswith("]"):
                section = stripped[1:-1]
                field = None
                continue
            if "=" not in stripped or section is None:
                sys.exit("%s:%d: expected 'key = value' inside a [section]"
                         % (path, lineno))
            key, _, value = stripped.partition("=")
            key, value = key.strip(), value.strip()
            full = "%s.%s" % (section, key)
            if not value:
                field = key
                out.setdefault(full, [])
                continue
            if field is None:
                out[full] = [value]
            else:
                out.setdefault(full, []).append(value)
    return out


def main():
    problems = []
    parsed = OrderedDict()
    for lang, fname in LANGS.items():
        path = os.path.join(HERE, fname)
        if not os.path.exists(path):
            sys.exit("missing source file: %s" % path)
        parsed[lang] = parse(path)

        # ASCII-only: the menu font has no Turkish glyphs.
        for key, sentences in parsed[lang].items():
            for s in sentences:
                bad = [c for c in s if ord(c) > 127]
                if bad:
                    problems.append(
                        "%s %s: non-ASCII %r -- FreeMono9pt7b has no glyph for it, "
                        "write 'i' not 'ı', 's' not 'ş', etc."
                        % (lang, key, "".join(sorted(set(bad)))))

    # Assign ids in first-seen order so both languages agree.
    ids = OrderedDict()
    for entries in parsed.values():
        for key in entries:
            if key not in ids:
                ids[key] = "H_" + key.replace(".", "_").upper()

    # Expand into lines, one id per line.
    expanded = OrderedDict()
    field_lines = OrderedDict()
    for lang, entries in parsed.items():
        rows = {}
        for key, sentences in entries.items():
            lines = []
            for s in sentences:
                wrapped = wrap(s, WIDTH_PX)
                if wrapped is None:
                    problems.append("%s %s: a word cannot fit in %d pixels"
                                    % (lang, key, WIDTH_PX))
                    wrapped = [s]
                lines.extend(wrapped)
            rows[key] = lines
            field_lines[key] = len(lines)
        expanded[lang] = rows

    ref = set(expanded["LANG_EN"].keys())
    for lang in expanded:
        if lang == "LANG_EN":
            continue
        missing = ref - set(expanded[lang].keys())
        if missing:
            problems.append("%s missing: %s" % (lang, ", ".join(sorted(missing))))
        extra = set(expanded[lang].keys()) - ref
        if extra:
            problems.append("%s unknown: %s" % (lang, ", ".join(sorted(extra))))

    if problems:
        sys.exit("catalogue problems:\n  " + "\n  ".join(problems))

    # Flat id list: base id then continuations, grouped per field.
    flat = []
    for key, name in ids.items():
        n = field_lines[key]
        for i in range(n):
            ident = name if i == 0 else "%s_%d" % (name, i + 1)
            flat.append((ident, key, i))

    # Intern lines into one pool, dedup across languages.
    pool_index, pool = {}, []

    def intern(text):
        if text not in pool_index:
            pool_index[text] = sum(len(p) + 1 for p in pool)
            pool.append(text)
        return pool_index[text]

    table = {}
    for lang in expanded:
        offsets = []
        for ident, key, i in flat:
            lines = expanded[lang].get(key, [])
            offsets.append(intern(lines[i] if i < len(lines) else ""))
        table[lang] = offsets

    # ---- header (single file, header-only) ----
    #
    # Header-only on purpose. The Arduino sketch builder does not reliably
    # pick up .cpp sources in subfolders, so the catalogue lives in a header
    # with inline functions instead: one definition however many translation
    # units include it, and no dependency on the builder's file discovery.

    pool_index, pool = {}, []

    def intern(text):
        if text not in pool_index:
            pool_index[text] = sum(len(p) + 1 for p in pool)
            pool.append(text)
        return pool_index[text]

    table = OrderedDict()
    for lang in expanded:
        table[lang] = []
        for ident, key, i in flat:
            lines = expanded[lang].get(key, [])
            table[lang].append(intern(lines[i] if i < len(lines) else ""))

    h = []
    h.append("#pragma once")
    h.append("")
    h.append("// GENERATED by lang/gen_help.py -- do not edit by hand.")
    h.append("// Edit help.<lang>.txt in this folder and re-run the generator.")
    h.append("//")
    h.append("// Included from the bottom of HelpLang.h, so HelpLang must not")
    h.append("// include this file back.")
    h.append("")
    h.append("#include <pgmspace.h>")
    h.append("#include <stdint.h>")
    h.append("")
    h.append("enum HelpId : uint16_t {")
    for n, (ident, _, _) in enumerate(flat):
        h.append("  %s = %d," % (ident, n))
    h.append("  HELP_ID_MAX = %d" % len(flat))
    h.append("};")
    h.append("")
    h.append("namespace help_gen {")
    h.append("")
    h.append("// One flat blob of NUL-separated strings. Offsets are uint16 rather")
    h.append("// than const char* so each index cell costs 2 bytes instead of 4 and")
    h.append("// the table needs no relocations.")
    h.append("inline const char kPool[] PROGMEM =")
    for text in pool:
        esc = text.replace("\\", "\\\\").replace('"', '\\"')
        h.append('  "%s\\0"' % esc)
    h.append("  ;")
    h.append("")
    h.append("inline const uint16_t kOffsets[LANG_COUNT][%d] PROGMEM = {" % len(flat))
    for lang in table:
        h.append("  [%s] = {" % lang)
        h.append("    " + ", ".join(str(o) for o in table[lang]))
        h.append("  },")
    h.append("};")
    h.append("")
    h.append("}  // namespace help_gen")
    h.append("")
    h.append("inline const char *helpText(HelpId id) {")
    h.append("  if (id >= HELP_ID_MAX) return \"\";")
    h.append("  return &help_gen::kPool[pgm_read_word(")
    h.append("      &help_gen::kOffsets[helpGetLang()][id])];")
    h.append("}")
    h.append("")
    h.append("// Collects the wrapped lines of one field, starting at `base`.")
    h.append("// Continuation ids are allocated contiguously, so this walks")
    h.append("// forward and stops at the first empty one.")
    h.append("inline uint8_t helpLines(HelpId base, const char **out, uint8_t max) {")
    h.append("  uint8_t n = 0;")
    h.append("  for (HelpId id = base; id < HELP_ID_MAX && n < max; ++id, ++n) {")
    h.append("    const char *s = helpText(id);")
    h.append("    if (s == nullptr || s[0] == '\\0') break;")
    h.append("    out[n] = s;")
    h.append("  }")
    h.append("  return n;")
    h.append("}")
    h.append("")
    with open(os.path.join(HERE, "HelpLang_gen.h"), "w",
              encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(h))

    stale = os.path.join(HERE, "HelpLang_gen.cpp")
    if os.path.exists(stale):
        os.remove(stale)
        print("removed stale HelpLang_gen.cpp")

    print("HelpLang_gen.h: %d ids, %d strings, %d bytes of pool"
          % (len(flat), len(pool), sum(len(p) + 1 for p in pool)))
    print("width limit %d px" % WIDTH_PX)
    for lang in table:
        widest = max((text_px(l) for rows in expanded[lang].values()
                      for l in rows), default=0)
        print("  %-8s widest line %d px" % (lang, widest))

if __name__ == "__main__":
    main()