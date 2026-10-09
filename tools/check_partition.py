"""Reads the ESP32 partition table and checks the firmware fits its slot.

The CYD build is close to the limit: the application slot is 1 MB and the image
has been creeping up with every feature added, so "does it still fit" is a
question worth answering from the actual artifacts instead of finding out from
a failed flash or, worse, a silently truncated write.

    python check_partition.py flash/marauder-cyd-custom/partitions.bin \\
                              flash/marauder-cyd-custom/firmware.bin
"""

import struct
import sys

MAGIC = 0x50AA
ENTRY = 32
APP_TYPES = {0x00: "app"}
APP_SUBTYPES = {0x10: "ota", 0x11: "ota_0", 0x12: "ota_1"}
DATA_TYPES = {0x01: "data", 0x03: "coredump"}
DATA_SUBTYPES = {0x00: "ota", 0x01: "phy", 0x02: "nvs", 0x82: "spiffs"}


def parse(data):
    entries = []
    offset = 0
    while offset + ENTRY <= len(data):
        mg, tp, st, off, sz, label, _ = struct.unpack_from(
            "<HBBII16sI", data, offset)
        if mg != MAGIC:
            break
        if tp in APP_TYPES:
            kind = "app/" + APP_SUBTYPES.get(st, hex(st))
        elif tp in DATA_TYPES:
            kind = "data/" + DATA_SUBTYPES.get(st, hex(st))
        else:
            kind = "%s/%s" % (hex(tp), hex(st))
        name = label.split(b"\x00", 1)[0].decode("utf-8", errors="replace")
        entries.append((name, kind, off, sz))
        offset += ENTRY
    return entries


def main():
    if len(sys.argv) < 3:
        sys.exit("kullanim: check_partition.py <partitions.bin> <firmware.bin>")

    with open(sys.argv[1], "rb") as handle:
        table = handle.read()
    fw = len(open(sys.argv[2], "rb").read())

    entries = parse(table)
    print("partition tablosu: %d bayt, %d giris"
          % (len(table), len(entries)))
    print("firmware.bin    : %d bayt (0x%X)" % (fw, fw))
    print()

    if not entries:
        sys.exit("UYARI: giris bulunamadi, tablo bozuk olabilir")

    for name, kind, off, sz in entries:
        print("  %-9s %-12s off=0x%06X  size=0x%06X (%7d bayt)"
              % (name, kind, off, sz, sz))
    print()

    over = 0
    for name, kind, off, sz in entries:
        if not kind.startswith("app/"):
            continue
        fits = fw <= sz
        if not fits:
            over += 1
        print("  %-9s slot @0x%06X: %s, bos alan %d bayt (%.1f%%)"
              % (name, off, "SIGER" if fits else "SIGMIYOR",
                 sz - fw, 100.0 * (sz - fw) / sz))

    if over:
        sys.exit("HATA: firmware %d uygulama slotuna siymiyor" % over)
    print("\nOK: firmware uygulama slotuna siyor")


if __name__ == "__main__":
    main()
