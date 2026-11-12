"""Render the original Lunar Systems GitHub header, without network access.

Requirements: Python 3.10+, Pillow, NumPy, FFmpeg on PATH and Manrope variable
font (or pass --font PATH). No assets are downloaded and no secrets are read.
Run: python scripts/render_header.py
The deterministic procedural lunar surface is original; it uses no photographs.
GIF encoding follows https://ffmpeg.org/ffmpeg-filters.html#palettegen and
https://pillow.readthedocs.io/en/stable/handbook/image-file-formats.html#gif .
"""

from __future__ import annotations

import argparse
import math
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
WIDTH, HEIGHT, SCALE = 1280, 400, 2
FPS, SECONDS = 20, 8
BG = (21, 22, 25)
TEXT = (242, 240, 237)
ORBIT = (86, 83, 88)
PEACH = (230, 184, 162)
RESAMPLE = Image.Resampling.LANCZOS


def find_font(explicit: str | None) -> Path:
    candidates = [Path(explicit)] if explicit else [
        ROOT / "assets" / "Manrope.ttf",
        Path.home() / "AppData/Local/Microsoft/Windows/Fonts/Manrope.ttf",
        Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts/Manrope.ttf",
        Path.home() / ".local/share/fonts/Manrope.ttf",
        Path("/usr/share/fonts/truetype/manrope/Manrope.ttf"),
    ]
    for path in candidates:
        if path.is_file():
            return path
    raise SystemExit("Manrope was not found. Pass --font PATH to an available font.")


def font_at(path: Path, size: int, weight: int) -> ImageFont.FreeTypeFont:
    font = ImageFont.truetype(str(path), size * SCALE)
    try:
        axes = font.get_variation_axes()
        font.set_variation_by_axes([
            weight if axis["name"] == b"Weight" else axis["default"]
            for axis in axes
        ])
    except OSError:
        pass  # Explicit static font supplied by the caller.
    return font


def tracked(draw, text, xy, font, tracking):
    x, baseline = (v * SCALE for v in xy)
    for index, char in enumerate(text):
        draw.text((x, baseline), char, font=font, fill=TEXT, anchor="ls")
        # Preserve native pair kerning while adding deliberate letterspacing.
        advance = font.getlength(text[:index + 1]) - font.getlength(text[:index])
        x += advance + tracking * SCALE


def text_layer(font_path: Path) -> Image.Image:
    image = Image.new("RGB", (WIDTH * SCALE, HEIGHT * SCALE), BG)
    draw = ImageDraw.Draw(image)
    title = font_at(font_path, 142, 800)
    # Align the visible cap height at y=72, independent of font ascent metadata.
    baseline = 72 - title.getbbox("G0d0v", anchor="ls")[1] / SCALE
    tracked(draw, "G0d0v", (76, baseline), title, -142 * 0.045)
    body = font_at(font_path, 44, 500)
    tracked(draw, "From idea to", (80, 259), body, -44 * 0.015)
    tracked(draw, "working product.", (80, 311), body, -44 * 0.015)
    draw.rectangle((80*SCALE, 337*SCALE, 128*SCALE-1, 340*SCALE-1), fill=PEACH)
    return image


def noise(rng, n, size):
    field = rng.integers(0, 256, (n, n), dtype=np.uint8)
    return np.asarray(Image.fromarray(field).resize((size, size), Image.Resampling.BICUBIC),
                      dtype=np.float32) / 255 - 0.5


def lunar_surface() -> Image.Image:
    """Multi-scale terrain, irregular lava basins and locally lit impact relief."""
    rng = np.random.default_rng(76035)
    size = 244 * SCALE
    yy, xx = np.mgrid[:size, :size].astype(np.float32)
    x = (xx + .5 - size/2) / (size/2)
    y = (yy + .5 - size/2) / (size/2)
    radius = np.sqrt(x*x + y*y)
    z = np.sqrt(np.maximum(0, 1-radius*radius))
    n1, n2 = noise(rng, 18, size), noise(rng, 57, size)
    fine = noise(rng, 180, size)
    albedo = 0.83 + .13*n1 + .12*n2 + .09*fine
    terrain = .010*n2 + .001*fine
    # Offset and overlapping basins keep the maria organic rather than circular.
    for cx, cy, rx, ry, darkness in [
        (-.33,-.18,.35,.42,.25), (-.05,-.43,.25,.22,.18),
        (.28,-.25,.28,.33,.23), (.44,.04,.22,.25,.20),
        (-.50,.15,.24,.24,.19), (-.12,.11,.20,.20,.12),
    ]:
        r = ((x-cx)/rx)**2 + ((y-cy)/ry)**2
        basin = 1 / (1 + np.exp(np.clip((r - 1 - n1*.8 - n2*.22)*7, -30, 30)))
        albedo -= darkness * basin
        terrain *= 1 - basin*.25

    # Foreshortened crater profiles: central bowl, elevated rim, scattered ejecta.
    for index in range(400):
        cx, cy = rng.uniform(-.97, .97, 2)
        distance = cx*cx + cy*cy
        if distance > .96:
            continue
        r = rng.uniform(.018, .07) if index < 85 else rng.uniform(.004, .018)
        if index < 7:
            r = rng.uniform(.075, .13)
        center_z = math.sqrt(1-distance)
        pad = r * 1.6
        x0, x1 = max(0, int((cx-pad+1)*size/2)), min(size, int((cx+pad+1)*size/2)+1)
        y0, y1 = max(0, int((cy-pad+1)*size/2)), min(size, int((cy+pad+1)*size/2)+1)
        dx, dy = x[y0:y1,x0:x1]-cx, y[y0:y1,x0:x1]-cy
        # Radial component compresses as the crater approaches the limb.
        angle = math.atan2(cy, cx)
        u = (dx*math.cos(angle)+dy*math.sin(angle)) / max(.28, center_z)
        v = -dx*math.sin(angle)+dy*math.cos(angle)
        q = np.sqrt(u*u+v*v) / r
        rim = np.exp(-((q-.96)/.16)**2)
        bowl = np.exp(-(q/.67)**4)
        profile = .85*rim - .60*bowl
        terrain[y0:y1,x0:x1] += profile * (r*.35)
        albedo[y0:y1,x0:x1] += .037*rim - .018*bowl

    gy, gx = np.gradient(terrain, 2/size)
    # Broad directional light plus fine relief. Illumination stays fixed in time.
    light = np.maximum(0, -.39*x -.43*y + .815*z)
    relief = np.clip(-gx*.14 - gy*.16, -.22, .22)
    brightness = np.clip(albedo*(.37+.69*light) + relief, .10, .95)
    rgb = np.stack([brightness*235, brightness*239, brightness*244], axis=-1)
    alpha = np.clip((1-radius)*size/2 + .5, 0, 1) * 255
    rgba = np.dstack([rgb, alpha]).clip(0, 255).astype(np.uint8)
    return Image.fromarray(rgba)


def orbit_point(theta, a, b, angle, center):
    c, s = math.cos(angle), math.sin(angle)
    u, v = a*math.cos(theta), b*math.sin(theta)
    return center[0] + c*u-s*v, center[1] + s*u+c*v


def draw_orbit(layer, a, b, degrees, center, width, front=False):
    start, stop = (0, math.pi) if front else (0, math.tau)
    points = [orbit_point(start+(stop-start)*i/600, a, b,
                          math.radians(degrees), center) for i in range(601)]
    ImageDraw.Draw(layer).line([(x*SCALE, y*SCALE) for x,y in points],
                              fill=ORBIT+(255,), width=round(width*SCALE))


def graphic_layers(moon):
    size = (WIDTH*SCALE, HEIGHT*SCALE)
    back = Image.new("RGBA", size)
    draw_orbit(back, 245, 78, -18, (1035,201), 1.5)
    draw_orbit(back, 280, 110, 24, (1045,205), 1.2)
    front = Image.new("RGBA", size)
    draw_orbit(front, 245, 78, -18, (1035,201), 1.5, True)
    draw_orbit(front, 280, 110, 24, (1045,205), 1.2, True)
    disc = Image.new("RGBA", size)
    disc.paste(moon, (913*SCALE,79*SCALE))
    # Only the parts crossing the lunar disc need a separate foreground arc.
    mask = np.asarray(disc.getchannel("A"), dtype=np.uint16)
    alpha = np.asarray(front.getchannel("A"), dtype=np.uint16)
    front.putalpha(Image.fromarray((alpha*mask//255*.22).astype(np.uint8)))
    return back, disc, front


def frame_at(t, static, layers):
    theta = math.tau*t + .08*math.sin(math.tau*t) + 2.65
    point = orbit_point(theta, 245, 78, math.radians(-18), (1035,201))
    satellite = Image.new("RGBA", static.size)
    d = ImageDraw.Draw(satellite)
    r = 4.5 + .5*math.sin(theta)
    px, py = point
    d.ellipse(((px-r)*SCALE, (py-r)*SCALE, (px+r)*SCALE, (py+r)*SCALE), fill=PEACH+(255,))
    back, disc, front = layers
    group = back.copy()
    if math.sin(theta) < 0:
        group.alpha_composite(satellite)
    group.alpha_composite(disc)
    group.alpha_composite(front)
    if math.sin(theta) >= 0:
        group.alpha_composite(satellite)
    # One smooth periodic displacement; negative source offset moves the group down.
    dy = 2*math.sin(math.tau*t)*SCALE
    group = group.transform(group.size, Image.Transform.AFFINE, (1,0,0,0,1,-dy),
                            resample=Image.Resampling.BICUBIC)
    result = static.convert("RGBA")
    result.alpha_composite(group)
    return result.convert("RGB").resize((WIDTH, HEIGHT), RESAMPLE)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--font", help="Path to an installed Manrope variable font")
    parser.add_argument("--static-only", action="store_true", help="Render PNG preview only")
    args = parser.parse_args()
    font_path = find_font(args.font)
    out = ROOT / "assets"
    out.mkdir(exist_ok=True)
    static = text_layer(font_path)
    layers = graphic_layers(lunar_surface())
    first = frame_at(0, static, layers)
    first.save(out / "header-static.png", optimize=True)
    if args.static_only:
        return
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise SystemExit("FFmpeg must be available on PATH to encode header.gif.")
    with tempfile.TemporaryDirectory(prefix=".header-render-", dir=out) as temp:
        temp = Path(temp)
        for index in range(FPS*SECONDS):
            frame_at(index/(FPS*SECONDS), static, layers).save(temp / f"{index:03d}.png")
        subprocess.run([
            ffmpeg, "-hide_banner", "-loglevel", "warning", "-y",
            "-framerate", str(FPS), "-i", str(temp / "%03d.png"),
            "-filter_complex", "[0:v]split[a][b];[a]palettegen=max_colors=128:stats_mode=full[p];"
            "[b][p]paletteuse=dither=none:diff_mode=rectangle",
            "-loop", "0", "-gifflags", "+offsetting+transdiff",
            str(out / "header.gif"),
        ], check=True)
    with Image.open(out / "header.gif") as gif:
        assert gif.size == (WIDTH, HEIGHT)
        assert gif.info["loop"] == 0
        assert gif.n_frames == FPS*SECONDS
        duration = sum(gif.seek(i) or gif.info["duration"] for i in range(gif.n_frames))
        assert duration == SECONDS*1000
    assert (out / "header.gif").stat().st_size < 8_000_000
    print(f"header.gif: {WIDTH}x{HEIGHT}, {FPS*SECONDS} frames, {duration} ms, "
          f"{(out / 'header.gif').stat().st_size:,} bytes, loop=0")
    print("Font:", font_path.name, "(variable weight 800 / 500 when available)")


if __name__ == "__main__":
    main()
