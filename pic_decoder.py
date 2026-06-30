from pathlib import Path
import pygame

SCREEN_W = 320
SCREEN_H = 200
PLANE_SIZE = 8000


def ega_color(value):
    base = value & 0x07
    bright = value & 0x10

    r = 170 if base & 0x04 else 0
    g = 170 if base & 0x02 else 0
    b = 170 if base & 0x01 else 0

    # CGA/EGA-specialfall: mörkgul blir brun.
    if base == 0x06 and not bright:
        return (170, 85, 0)

    if bright:
        r = min(255, r + 85)
        g = min(255, g + 85)
        b = min(255, b + 85)

    return (r, g, b)


def decode_rle_block(data):
    out = bytearray()
    i = 0

    while len(out) < PLANE_SIZE and i < len(data):
        b = data[i]
        i += 1

        if b == 0x7F:
            count = data[i]
            i += 1

            if count == 0:
                out.append(0x7F)
            else:
                value = data[i]
                i += 1
                out.extend([value] * count)
        else:
            out.append(b)

    if len(out) < PLANE_SIZE:
        out.extend([0] * (PLANE_SIZE - len(out)))

    return out[:PLANE_SIZE]


def load_pic_surface(path):
    data = Path(path).read_bytes()

    mode = data[0]
    if mode != 0x0D:
        raise ValueError(f"Fel .PIC-läge: {mode:#x}")

    palette_regs = data[1:17]
    palette = [ega_color(v) for v in palette_regs]

    pos = 17
    planes = []

    for _ in range(4):
        block_len = int.from_bytes(data[pos:pos + 2], "little")
        pos += 2

        block = data[pos:pos + block_len]
        pos += block_len

        planes.append(decode_rle_block(block))

    surface = pygame.Surface((SCREEN_W, SCREEN_H))
    pixels = pygame.PixelArray(surface)

    for y in range(SCREEN_H):
        row = y * 40

        for x in range(SCREEN_W):
            byte_index = row + (x // 8)
            bit = 7 - (x % 8)

            color_index = 0

            for plane in range(4):
                if planes[plane][byte_index] & (1 << bit):
                    color_index |= 1 << plane

            pixels[x, y] = palette[color_index]

    del pixels
    return surface


def save_pic_as_png(pic_path, png_path):
    pygame.init()
    surface = load_pic_surface(pic_path)
    pygame.image.save(surface, png_path)
    pygame.quit()


if __name__ == "__main__":
    save_pic_as_png("OBJECTS.PIC", "OBJECTS_debug.png")
    save_pic_as_png("INTRO.PIC", "INTRO_debug.png")
    save_pic_as_png("3DTOP.PIC", "3DTOP_debug.png")
    print("Klart.")