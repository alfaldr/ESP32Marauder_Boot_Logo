"""Prints the ESP32 application descriptor embedded in a firmware image.

The descriptor is what tells you which build a .bin actually is: the project
name, the IDF version and the compile timestamp. That matters here because the
CI artifacts for successive commits look identical from the outside, so "is the
device running the build I think it is?" needs an answer that does not depend on
file size alone.

Layout follows esp_app_desc_t from esp_app_desc.h:

    uint32_t magic_word;
    uint32_t secure_version;
    uint32_t reserv1[2];
    char     version[32];
    char     project_name[32];
    char     time[16];
    char     date[16];
    char     idf_ver[32];
    uint8_t  app_elf_sha256[32];
    ...

So version sits at 16, not 32. An earlier version of this script assumed a
different order and printed the firmware filename in the project_name field and
the project name in the idf_ver field, which looked plausible enough to go
unnoticed until the console failed on a non-ASCII build timestamp.

The magic word is searched for rather than assumed at a fixed offset, because
the descriptor is referenced from the image header and its position depends on
how many segments the build emitted.
"""

import struct
import sys

MAGIC = 0xABCD5432
DESC_LEN = 256


def field(raw):
    """NUL-terminated fixed-width field, printable, trimmed."""
    text = raw.split(b"\x00", 1)[0].decode("utf-8", errors="replace")
    return "".join(c for c in text if c.isprintable()).strip()


def main():
    if len(sys.argv) < 2:
        sys.exit("kullanim: read_appdesc.py <firmware.bin>")
    with open(sys.argv[1], "rb") as handle:
        data = handle.read()

    if len(data) < DESC_LEN:
        sys.exit("dosya cok kucuk: %d bayt" % len(data))

    needle = struct.pack("<I", MAGIC)
    offset = data.find(needle)
    if offset < 0:
        sys.exit("app descriptor bulunamadi (magic 0x%08X)" % MAGIC)

    d = data[offset:offset + DESC_LEN]
    magic, secure = struct.unpack_from("<II", d, 0)

    print("descriptor ofseti : 0x%X" % offset)
    print("magic word        : 0x%08X %s"
          % (magic, "(gecerli)" if magic == MAGIC else "(gecersiz)"))
    print("secure version    : %d" % secure)
    print("version           : %s" % field(d[16:48]))
    print("project name      : %s" % field(d[48:80]))
    print("build time        : %s" % field(d[80:96]))
    print("build date        : %s" % field(d[96:112]))
    print("idf ver           : %s" % field(d[112:144]))
    print("elf sha256        : %s" % d[144:176].hex())


if __name__ == "__main__":
    main()
