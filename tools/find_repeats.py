import io
import re
from collections import Counter

P = r"C:\Users\Admin\firmware\ESP32Marauder\esp32_marauder\lang\HelpLang_gen.h"
raw = io.open(P, "r", encoding="utf-8", newline="").read()

pool = re.findall(r'^\s*"((?:[^"\\]|\\.)*)\\0"', raw, re.M)

counts = Counter(pool)
dupes = {k: v for k, v in counts.items() if v > 1}

print("pool: %d strings, %d distinct" % (len(pool), len(counts)))
print()
if dupes:
    print("REPEATED LINES:")
    for text, n in sorted(dupes.items(), key=lambda kv: -kv[1]):
        print("  %dx  %s" % (n, text))
else:
    print("no byte-identical repeats")

# Repetitive phrasing is a separate smell: many entries opening the same way.
print()
print("OPENING PHRASES (top 8):")
openers = Counter()
for t in pool:
    w = t.split()
    if len(w) >= 2:
        openers[" ".join(w[:2])] += 1
for phrase, n in openers.most_common(8):
    print("  %-24s %d" % (phrase, n))

print()
print("SHARED TOKENS (appearing in many lines):")
tok = Counter()
for t in pool:
    for w in t.split():
        tok[w] += 1
for word, n in tok.most_common(10):
    print("  %-16s %d" % (word, n))