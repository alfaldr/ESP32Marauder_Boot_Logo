"""BootSplashAnim.h dosyasini cozer ve kareleri PNG olarak geri yazar.

C tarafindaki decoder ile ayni algoritma: renk indeksi + varint uzunluk,
satirlar icinde RLE; 0. kare tam, digerleri delta.
Boylece ureticinin cikardigi format gercekten cozulebiliyor mu dogrulanir.
"""

import re
import sys
from PIL import Image


def parse_header(path):
    text = open(path, encoding="ascii").read()

    def numbers(name):
        match = re.search(r"%s\[[^\]]*\]\s*=\s*\{([^}]*)\}" % re.escape(name), text, re.S)
        if not match:
            return None
        return [int(value, 0) for value in re.findall(r"0x[0-9A-Fa-f]+|\d+", match.group(1))]

    def scalar(name):
        match = re.search(r"%s\s*=\s*(\d+)" % re.escape(name), text)
        return int(match.group(1)) if match else None

    return {
        "width": scalar("BOOT_ANIM_WIDTH"),
        "height": scalar("BOOT_ANIM_HEIGHT"),
        "count": scalar("BOOT_ANIM_FRAME_COUNT"),
        "delay": scalar("BOOT_ANIM_FRAME_DELAY_MS"),
        "row_end": scalar("BOOT_ANIM_ROW_END"),
        "palette": numbers("BOOT_ANIM_PALETTE"),
        "offsets": numbers("BOOT_ANIM_OFFSET"),
        "data": numbers("BOOT_ANIM_DATA"),
    }


def read_varint(data, pos):
    value = 0
    shift = 0
    while True:
        byte = data[pos]
        pos += 1
        value |= (byte & 0x7F) << shift
        shift += 7
        if not (byte & 0x80):
            return value, pos


def decode(info):
    width, height = info["width"], info["height"]
    row_end = info["row_end"]
    palette = []
    for value in info["palette"][:8]:
        red = (value >> 11 & 0x1F) << 3
        green = (value >> 5 & 0x3F) << 2
        blue = (value & 0x1F) << 3
        palette.append((red, green, blue))

    data = info["data"]
    frames = []
    current = None
    pos = 0

    for index in range(info["count"]):
        limit = info["offsets"][index + 1]
        if index == 0:
            current = [[0] * width for _ in range(height)]
            rows = range(height)
            while pos < limit:
                row = 0
                filled = 0
                while filled < width:
                    colour = data[pos]
                    pos += 1
                    count, pos = read_varint(data, pos)
                    for _ in range(count):
                        current[row][filled] = colour
                        filled += 1
                row += 1
        else:
            while pos < limit:
                row, pos = read_varint(data, pos)
                if row == row_end:
                    break
                filled = 0
                while filled < width:
                    colour = data[pos]
                    pos += 1
                    count, pos = read_varint(data, pos)
                    for _ in range(count):
                        current[row][filled] = colour
                        filled += 1
        if pos != limit:
            raise SystemExit("kare %d: veri sonu uyusmadi (%d != %d)" % (index, pos, limit))
        image = Image.new("RGB", (width, height))
        pixels = image.load()
        for y in range(height):
            for x in range(width):
                pixels[x, y] = palette[current[y][x]]
        frames.append(image)

    return frames, palette


def main():
    info = parse_header(sys.argv[1])
    out_dir = sys.argv[2]
    wanted = [int(value) for value in sys.argv[3:]] or [0, 13, 27, 41, 53]

    print("cozulen: %dx%d, %d kare, %d ms, satir sonlandirici %d"
          % (info["width"], info["height"], info["count"], info["delay"], info["row_end"]))
    frames, palette = decode(info)
    print("veri tuketildi: %d / %d bayt" % (info["offsets"][-1], len(info["data"])))
    print("palet:", ", ".join("#%02X%02X%02X" % c for c in palette[:6]))
    print()

    for index in wanted:
        if index < len(frames):
            path = "%s\\decoded_%02d.png" % (out_dir, index)
            frames[index].save(path)
            print("yazildi: %s" % path)

    print()
    print("kare 0 ve kare 1 farkli mi:", "evet" if frames[0].tobytes() != frames[1].tobytes() else "hayir")
    print("son kare cozuldu mu        :", len(frames) == info["count"])


if __name__ == "__main__":
    main()