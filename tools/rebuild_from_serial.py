#!/usr/bin/env python3
"""
Rebuilds the capture file out of a raw serial stream.

Buffer::saveSerial() wraps each flush in [BUF/BEGIN] ... [BUF/CLOSE] markers,
with the pcapng bytes in between. Concatenating those regions gives back the
file the device would have written to the SD card.

Writes both the .pcapng and a short report: how many flushes were found, how
much survived, and whether the result looks like a well-formed pcapng.
"""

import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "serial_capture.bin")
OUT_DIR = HERE

BEGIN = b"[BUF/BEGIN]"
CLOSE = b"[BUF/CLOSE]"

# pcapng block types we care about when validating.
SHB = 0x0A0D0D0A
EPB = 0x00000006


def extract(data):
    blocks = []
    i = 0
    while True:
        s = data.find(BEGIN, i)
        if s < 0:
            break
        s += len(BEGIN)
        # Nothing between the marker and the payload may be trimmed. The
        # Section Header Block type is 0x0A0D0D0A, which is four newline
        # bytes, so any "skip leading CR/LF" logic silently eats the block
        # type and the file stops being a pcapng. That is exactly what the
        # first attempt at this script did.
        e = data.find(CLOSE, s)
        if e < 0:
            break
        blocks.append(data[s:e])
        i = e + len(CLOSE)
    return blocks


def walk_pcapng(blob):
    """Walks the block chain and reports what it finds."""
    off = 0
    blocks = []
    while off + 12 <= len(blob):
        btype = struct.unpack_from("<I", blob, off)[0]
        blen = struct.unpack_from("<I", blob, off + 4)[0]
        if blen < 12 or off + blen > len(blob):
            break
        trail = struct.unpack_from("<I", blob, off + blen - 4)[0]
        if trail != blen:
            print("  !! block at %d: trailing length %d != %d"
                  % (off, trail, blen))
            break
        blocks.append((btype, blen))
        off += blen
    return blocks, off


def main():
    if not os.path.exists(SRC):
        sys.exit("missing %s -- run grab_serial_capture.ps1 first" % SRC)

    data = open(SRC, "rb").read()
    print("raw stream: %d bytes" % len(data))
    print("markers: %d BEGIN, %d CLOSE"
          % (data.count(BEGIN), data.count(CLOSE)))

    blocks = extract(data)
    if not blocks:
        print("\nno capture blocks found; the scan may not have flushed, or")
        print("serial output was not enabled")
        return 1

    blob = b"".join(blocks)
    print("\nflushes found: %d" % len(blocks))
    for i, b in enumerate(blocks):
        print("  #%d %6d bayt" % (i, len(b)))
    print("concatenated: %d bayt" % len(blob))

    parsed, consumed = walk_pcapng(blob)
    print("\npcapng block walk: %d blok, %d bayt ayristirildi"
          % (len(parsed), consumed))
    counts = {}
    for t, _ in parsed:
        counts[t] = counts.get(t, 0) + 1
    names = {SHB: "SectionHeader", EPB: "EnhancedPacket"}
    for t, n in sorted(counts.items()):
        print("  %-16s (%#010x): %d" % (names.get(t, "bilinmeyen"), t, n))

    if consumed != len(blob):
        print("\nUYARI: yalnizca %d / %d bayt ayristirildi; dosya eksik"
              % (consumed, len(blob)))

    out = os.path.join(OUT_DIR, "serial_capture.pcapng")
    with open(out, "wb") as fh:
        fh.write(blob)
    print("\nyazildi: %s" % out)
    return 0


if __name__ == "__main__":
    sys.exit(main())