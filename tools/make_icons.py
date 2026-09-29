#!/usr/bin/env python3
"""生成 PWA 图标（纯标准库，不依赖图像库），图形与 public/favicon.svg 一致：
深色渐变圆角底 + 中心暖光，实心琥珀色圆角房子，中间深色圆窗里一盏亮着的灯。

输出到 public/：
- icons/icon-192.png、icons/icon-512.png：普通图标（圆角，四角透明）
- icons/maskable-512.png：Android 自适应图标（满版底色，图形缩在中间安全区）
- apple-touch-icon.png：180×180，满版底色（iOS 自己裁圆角，透明处会变黑）

做法：每个像素在 64×64 设计坐标里求各图形的有符号距离，按距离做 1 像素抗锯齿，逐层叠加。
用法：python3 tools/make_icons.py
"""

from __future__ import annotations

import math
import struct
import zlib
from pathlib import Path

PUBLIC = Path(__file__).resolve().parent.parent / "public"

Color = tuple[float, float, float]


def hex_color(value: str) -> Color:
    value = value.lstrip("#")
    return tuple(int(value[i:i + 2], 16) / 255 for i in (0, 2, 4))  # type: ignore[return-value]


BG_TOP, BG_BOTTOM = hex_color("#2a3036"), hex_color("#111417")
AMBER = hex_color("#f4b764")
HOUSE_TOP, HOUSE_BOTTOM = hex_color("#fbd495"), hex_color("#e5953c")
WINDOW = hex_color("#15181c")
LAMP = hex_color("#fff3dc")

# 房子：多边形向外扩 3（等于 SVG 中线宽 6 的圆角描边），得到圆角实心房子。
HOUSE = [(17.0, 31.0), (32.0, 17.5), (47.0, 31.0), (47.0, 48.0), (17.0, 48.0)]
HOUSE_ROUND = 3.0
CENTER = (32.0, 36.5)
WINDOW_R, LAMP_R = 7.0, 2.8
GLOW_CENTER, GLOW_R, GLOW_ALPHA = (32.0, 36.0), 28.0, 0.32


def lerp(a: Color, b: Color, t: float) -> Color:
    t = max(0.0, min(1.0, t))
    return tuple(x + (y - x) * t for x, y in zip(a, b))  # type: ignore[return-value]


def sd_polygon(px: float, py: float, points: list[tuple[float, float]]) -> float:
    """点到多边形边界的有符号距离（内部为负）。"""
    d = (px - points[0][0]) ** 2 + (py - points[0][1]) ** 2
    sign = 1.0
    count = len(points)
    for i in range(count):
        ax, ay = points[i]
        bx, by = points[i - 1]
        ex, ey = bx - ax, by - ay
        wx, wy = px - ax, py - ay
        t = max(0.0, min(1.0, (wx * ex + wy * ey) / (ex * ex + ey * ey)))
        d = min(d, (wx - ex * t) ** 2 + (wy - ey * t) ** 2)
        c1, c2, c3 = py >= ay, py < by, ex * wy > ey * wx
        if (c1 and c2 and c3) or (not c1 and not c2 and not c3):
            sign = -sign
    return sign * math.sqrt(d)


def sd_rounded_box(px: float, py: float, size: float, radius: float) -> float:
    half = size / 2
    qx = abs(px - half) - (half - radius)
    qy = abs(py - half) - (half - radius)
    return math.hypot(max(qx, 0), max(qy, 0)) + min(max(qx, qy), 0) - radius


def coverage(distance_px: float) -> float:
    """以像素为单位的有符号距离 → 覆盖率（1 像素抗锯齿）。"""
    return max(0.0, min(1.0, 0.5 - distance_px))


def over(base: Color, base_alpha: float, color: Color, alpha: float) -> tuple[Color, float]:
    """把 color（不透明度 alpha）叠在 base 上。"""
    out_alpha = alpha + base_alpha * (1 - alpha)
    if out_alpha <= 0:
        return (0.0, 0.0, 0.0), 0.0
    mixed = tuple((c * alpha + b * base_alpha * (1 - alpha)) / out_alpha for c, b in zip(color, base))
    return mixed, out_alpha  # type: ignore[return-value]


def render(size: int, rounded: bool, art_scale: float) -> bytes:
    """rounded：四角透明的圆角图标；否则满版底色。art_scale：图形（64 坐标系）占边长的比例，居中。"""
    unit = size * art_scale / 64  # 1 个设计单位对应的像素
    offset = size * (1 - art_scale) / 2
    radius = size * 15 / 64
    rows = []
    for y in range(size):
        row = bytearray([0])  # 每行的过滤类型：无
        py = y + 0.5
        for x in range(size):
            px = x + 0.5
            bg_alpha = coverage(sd_rounded_box(px, py, size, radius)) if rounded else 1.0
            if bg_alpha <= 0:
                row.extend((0, 0, 0, 0))
                continue
            color, alpha = lerp(BG_TOP, BG_BOTTOM, py / size), bg_alpha
            ux, uy = (px - offset) / unit, (py - offset) / unit
            # 中心暖光
            glow = GLOW_ALPHA * max(0.0, 1 - math.hypot(ux - GLOW_CENTER[0], uy - GLOW_CENTER[1]) / GLOW_R)
            color, _ = over(color, 1.0, AMBER, glow)
            # 房子（上浅下深的琥珀渐变）
            house = coverage((sd_polygon(ux, uy, HOUSE) - HOUSE_ROUND) * unit)
            if house > 0:
                color, _ = over(color, 1.0, lerp(HOUSE_TOP, HOUSE_BOTTOM, (uy - 14.5) / 36.5), house)
            # 圆窗、窗内暖光、灯
            to_center = math.hypot(ux - CENTER[0], uy - CENTER[1])
            window = coverage((to_center - WINDOW_R) * unit)
            if window > 0:
                color, _ = over(color, 1.0, WINDOW, window)
                color, _ = over(color, 1.0, AMBER, window * 0.55 * max(0.0, 1 - to_center / WINDOW_R))
                color, _ = over(color, 1.0, LAMP, coverage((to_center - LAMP_R) * unit))
            row.extend([round(c * 255) for c in color] + [round(alpha * 255)])
        rows.append(bytes(row))
    raw = b"".join(rows)

    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)

    header = struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0)  # RGBA 8 位
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")


def main() -> None:
    outputs = {
        "icons/icon-192.png": (192, True, 1.0),
        "icons/icon-512.png": (512, True, 1.0),
        "icons/maskable-512.png": (512, False, 0.78),  # Android 安全区为中间 80% 圆形
        "apple-touch-icon.png": (180, False, 0.9),
    }
    for name, (size, rounded, scale) in outputs.items():
        path = PUBLIC / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(render(size, rounded, scale))
        print(f"{name}  {size}×{size}  {path.stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
