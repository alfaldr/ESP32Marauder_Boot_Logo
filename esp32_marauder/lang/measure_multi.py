"""Birden fazla GIF'in gercek flash maliyetini RLE ile olcer."""

import os
import sys
from PIL import Image, ImageSequence

BUDGET = 240 * 1024


def varint(value):
    out = bytearray()
    while True:
        byte = value & 0x7F
        value >>= 7
        if value:
            out.append(byte | 0x80)
        else:
            out.append(byte)
            return bytes(out)


def rle_row(data, width, start):
    out = bytearray()
    previous = -1
    run = 0
    for index in range(start, start + width):
        value = data[index]
        if value == previous:
            run += 1
            if run == 255:
                out.append(previous)
                out += varint(255)
                previous, run = -1, 0
            continue
        if previous >= 0:
            out.append(previous)
            out += varint(run)
        previous, run = value, 1
    if previous >= 0:
        out.append(previous)
        out += varint(run)
    return bytes(out)


def nearest_map(rgb_image, palette_rgb):
    pixels = rgb_image.load()
    width, height = rgb_image.size
    cache = {}
    out = bytearray(width * height)
    for y in range(height):
        base = y * width
        for x in range(width):
            key = pixels[x, y]
            index = cache.get(key)
            if index is None:
                best, best_d = 0, None
                for i, (pr, pg, pb) in enumerate(palette_rgb):
                    d = (key[0] - pr) ** 2 + (key[1] - pg) ** 2 + (key[2] - pb) ** 2
                    if best_d is None or d < best_d:
                        best, best_d = i, d
                index = best
                cache[key] = index
            out[base + x] = index
    return bytes(out)


def analyse(path):
    image = Image.open(path)
    palette = image.getpalette() or []
    colors = max(1, len(palette) // 3)
    palette_rgb = [tuple(palette[i * 3:i * 3 + 3]) for i in range(colors)]
    width, height = image.size

    frames, durations = [], []
    for frame in ImageSequence.Iterator(image):
        if frame.mode == "P":
            frames.append(bytes(frame.getdata()))
        else:
            frames.append(nearest_map(frame.convert("RGB"), palette_rgb))
        durations.append(frame.info.get("duration", 0) or 66)

    sizes = [sum(len(rle_row(f, width, r * width)) for r in range(height)) for f in frames]
    return {
        "path": path,
        "name": os.path.basename(path),
        "width": width, "height": height,
        "frames": len(frames),
        "colors": colors,
        "sizes": sizes,
        "durations": durations,
        "total": sum(sizes),
    }


def main():
    paths = sys.argv[1:]
    print("%-24s %6s %8s %10s %10s %s" % ("gif", "kare", "renk", "kare/KB", "toplam", "not"))
    print("-" * 84)
    for path in paths:
        info = analyse(path)
        fits = "SIGAR" if info["total"] <= BUDGET else "sigmiyor (%.0f KB)" % (info["total"] / 1024)
        print("%-24s %6d %8d %10.1f %7.0f KB %s"
              % (info["name"], info["frames"], info["colors"],
                 info["total"] / info["frames"], info["total"] / 1024, fits))
    print()
    print("butce: %d bayt (%.0f KB)" % (BUDGET, BUDGET / 1024))
    print()
    for path in paths:
        info = analyse(path)
        sizes = info["sizes"]
        count = len(sizes)
        # kareleri esit aralikla seyrelt
        best = None
        for step in (1, 2, 3, 4, 5, 6):
            picked = sizes[::step]
            total = sum(picked)
            if total <= BUDGET:
                fps = 1000.0 / (sum(info["durations"][::step]) / len(picked))
                if best is None or len(picked) > best[1]:
                    best = (step, len(picked), total, fps)
        if best:
            step, count2, total, fps = best
            loop = sum(info["durations"][::step]) / 1000.0
            print("%-24s seyreltme 1/%d -> %2d kare, %6.0f KB, ~%.1f fps, dongu %.2f sn"
                  % (info["name"], step, count2, total / 1024, fps, loop))


if __name__ == "__main__":
    main()