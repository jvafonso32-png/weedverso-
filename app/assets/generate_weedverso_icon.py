from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont


ROOT = Path(__file__).resolve().parent
PNG_PATH = ROOT / "weedverso-icon-preview.png"
ICO_PATH = ROOT / "weedverso-icon.ico"

SIZE = 1024
TEXT = "#e8f4ed"
MUTED = "#99aca0"
GREEN = "#39ff8f"
BLUE = "#26c8ff"
HOT = "#ff5f70"
GRID = (255, 255, 255, 10)


def load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = []
    if bold:
        candidates.extend(
            [
                r"C:\Windows\Fonts\bahnschrift.ttf",
                r"C:\Windows\Fonts\segoeuib.ttf",
                r"C:\Windows\Fonts\arialbd.ttf",
            ]
        )
    else:
        candidates.extend(
            [
                r"C:\Windows\Fonts\bahnschrift.ttf",
                r"C:\Windows\Fonts\segoeui.ttf",
                r"C:\Windows\Fonts\arial.ttf",
            ]
        )
    for candidate in candidates:
        path = Path(candidate)
        if path.exists():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


def vertical_gradient(size: int, top_rgb: tuple[int, int, int], bottom_rgb: tuple[int, int, int]) -> Image.Image:
    base = Image.new("RGBA", (size, size))
    draw = ImageDraw.Draw(base)
    for y in range(size):
        t = y / max(1, size - 1)
        color = tuple(int(top_rgb[i] * (1 - t) + bottom_rgb[i] * t) for i in range(3)) + (255,)
        draw.line((0, y, size, y), fill=color)
    return base


def add_radial_glow(target: Image.Image, center: tuple[int, int], radius: int, color: tuple[int, int, int, int]) -> None:
    layer = Image.new("RGBA", target.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    x, y = center
    for ring in range(radius, 0, -8):
        alpha = int(color[3] * (ring / radius) ** 1.9)
        fill = (color[0], color[1], color[2], alpha)
        draw.ellipse((x - ring, y - ring, x + ring, y + ring), fill=fill)
    target.alpha_composite(layer)


def make_panel() -> Image.Image:
    canvas = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    panel = vertical_gradient(SIZE, (15, 22, 19), (6, 10, 8))

    add_radial_glow(panel, (808, 170), 320, (57, 255, 143, 36))
    add_radial_glow(panel, (190, 820), 280, (38, 200, 255, 32))
    add_radial_glow(panel, (858, 760), 170, (255, 95, 112, 26))

    grid = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    grid_draw = ImageDraw.Draw(grid)
    step = 64
    for x in range(step, SIZE, step):
        grid_draw.line((x, 0, x, SIZE), fill=GRID, width=1)
    for y in range(step, SIZE, step):
        grid_draw.line((0, y, SIZE, y), fill=GRID, width=1)
    panel.alpha_composite(grid)

    border = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    border_draw = ImageDraw.Draw(border)
    border_draw.rounded_rectangle((18, 18, SIZE - 18, SIZE - 18), radius=230, outline=(57, 255, 143, 70), width=8)
    border_draw.rounded_rectangle((38, 38, SIZE - 38, SIZE - 38), radius=210, outline=(255, 255, 255, 20), width=2)
    panel.alpha_composite(border)

    mask = Image.new("L", (SIZE, SIZE), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, SIZE - 1, SIZE - 1), radius=240, fill=255)

    shadow = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle((42, 58, SIZE - 24, SIZE - 10), radius=240, fill=(0, 0, 0, 180))
    shadow = shadow.filter(ImageFilter.GaussianBlur(28))
    canvas.alpha_composite(shadow)

    panel.putalpha(mask)
    canvas.alpha_composite(panel)
    return canvas


def draw_badge(target: Image.Image) -> None:
    badge = Image.new("RGBA", target.size, (0, 0, 0, 0))
    badge_draw = ImageDraw.Draw(badge)
    badge_draw.rounded_rectangle(
        (120, 128, SIZE - 120, 752),
        radius=122,
        fill=(10, 18, 14, 216),
        outline=(57, 255, 143, 68),
        width=4,
    )
    badge_draw.rounded_rectangle(
        (156, 164, SIZE - 156, 716),
        radius=94,
        outline=(255, 255, 255, 18),
        width=2,
    )
    target.alpha_composite(badge)


def draw_wv(target: Image.Image) -> None:
    draw = ImageDraw.Draw(target)
    font = load_font(426, bold=True)
    y = 196

    w_bbox = draw.textbbox((0, 0), "W", font=font)
    v_bbox = draw.textbbox((0, 0), "V", font=font)
    w_width = w_bbox[2] - w_bbox[0]
    v_width = v_bbox[2] - v_bbox[0]
    spacing = 18
    total_width = w_width + v_width + spacing
    start_x = int((SIZE - total_width) / 2)

    positions = {
        "W": (start_x, y),
        "V": (start_x + w_width + spacing, y),
    }

    glow = Image.new("RGBA", target.size, (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)
    glow_draw.text(
        positions["W"],
        "W",
        font=font,
        fill=(57, 255, 143, 168),
        stroke_width=12,
        stroke_fill=(57, 255, 143, 110),
    )
    glow_draw.text(
        positions["V"],
        "V",
        font=font,
        fill=(38, 200, 255, 96),
        stroke_width=12,
        stroke_fill=(38, 200, 255, 84),
    )
    glow = glow.filter(ImageFilter.GaussianBlur(22))
    target.alpha_composite(glow)

    shadow = Image.new("RGBA", target.size, (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow)
    shadow_draw.text((positions["W"][0], positions["W"][1] + 16), "W", font=font, fill=(0, 0, 0, 140))
    shadow_draw.text((positions["V"][0], positions["V"][1] + 16), "V", font=font, fill=(0, 0, 0, 120))
    shadow = shadow.filter(ImageFilter.GaussianBlur(8))
    target.alpha_composite(shadow)

    draw.text(
        positions["W"],
        "W",
        font=font,
        fill=GREEN,
        stroke_width=10,
        stroke_fill=(232, 255, 240, 170),
    )
    draw.text(
        positions["V"],
        "V",
        font=font,
        fill=(214, 255, 235, 236),
        stroke_width=10,
        stroke_fill=(57, 255, 143, 172),
    )

    draw.rounded_rectangle((182, 212, 304, 236), radius=13, fill=(57, 255, 143, 214))
    draw.rounded_rectangle((182, 212, 244, 236), radius=13, fill=(232, 244, 237, 230))
    draw.rounded_rectangle((718, 668, 840, 690), radius=12, fill=(38, 200, 255, 100))
    draw.line((768, 244, 836, 182), fill=HOT, width=14)


def draw_wordmark(target: Image.Image) -> None:
    draw = ImageDraw.Draw(target)
    display_font = load_font(90, bold=True)
    sub_font = load_font(30, bold=False)

    title = "WEEDVERSO"
    subtitle = "wv cloud sync"

    title_bbox = draw.textbbox((0, 0), title, font=display_font)
    title_w = title_bbox[2] - title_bbox[0]
    title_h = title_bbox[3] - title_bbox[1]
    subtitle_bbox = draw.textbbox((0, 0), subtitle, font=sub_font)
    subtitle_w = subtitle_bbox[2] - subtitle_bbox[0]

    title_x = (SIZE - title_w) / 2
    title_y = 804
    sub_x = (SIZE - subtitle_w) / 2
    sub_y = title_y + title_h + 3

    plate = Image.new("RGBA", target.size, (0, 0, 0, 0))
    plate_draw = ImageDraw.Draw(plate)
    plate_draw.rounded_rectangle(
        (154, 770, SIZE - 154, 946),
        radius=38,
        fill=(10, 16, 13, 210),
        outline=(57, 255, 143, 54),
        width=3,
    )
    target.alpha_composite(plate)

    draw.text((title_x, title_y), title, font=display_font, fill=TEXT)
    draw.text((title_x, title_y - 2), title, font=display_font, fill=(57, 255, 143, 46))
    draw.text((sub_x, sub_y), subtitle, font=sub_font, fill=MUTED)


def add_scanline(target: Image.Image) -> None:
    layer = Image.new("RGBA", target.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    for y in range(70, SIZE - 70, 10):
        draw.line((80, y, SIZE - 80, y), fill=(255, 255, 255, 4), width=1)
    target.alpha_composite(layer)


def build_icon() -> Image.Image:
    canvas = make_panel()
    draw_badge(canvas)
    draw_wv(canvas)
    draw_wordmark(canvas)
    add_scanline(canvas)
    return canvas


def save_outputs(image: Image.Image) -> None:
    image.save(PNG_PATH)
    sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (24, 24), (16, 16)]
    image.save(ICO_PATH, sizes=sizes)


if __name__ == "__main__":
    ROOT.mkdir(parents=True, exist_ok=True)
    final_image = build_icon()
    save_outputs(final_image)
    print(PNG_PATH)
    print(ICO_PATH)
