#!/usr/bin/env python3
"""The Isle of the Drowned King — a treasure map drawn with the standard library.

Draws a 1024x1024 antique treasure map (parchment, sepia ink, compass rose,
dashed route to a red X) and writes it to $MAKEFUN_OUTPUT_DIR/entry.png
(default /output/entry.png).

Stdlib only (struct, zlib, math, os, random, hashlib). No third-party packages,
no network, no files read or written outside the output directory.

Technique notes (from research):
- PNG is written by hand: 8-byte signature, IHDR / IDAT / IEND chunks, each
  chunk carrying a CRC32; pixel rows are zlib-compressed with a filter byte 0.
  (See dev.to/renev3408 "stdlib-only Python fix" and the PyPNG source.)
- The look follows antique cartography: warm sepia ink (#2a1d0d) on parchment
  (#f4ecd8 land, #d8cbaf sea wash), a 16-point compass rose with a fleur-de-lis
  north, faint rhumb lines, hachured hills, a title cartouche, and horror
  vacui — sea monsters and a ship filling the empty water, as on portolan
  charts and Piri Reis-style maps.
"""

import hashlib
import math
import os
import random
import struct
import sys
import zlib

W, H = 1024, 1024
SEED = 1719

# ---------------------------------------------------------------- palette ---
INK = (58, 40, 22)          # sepia linework
INK_SOFT = (84, 62, 36)
RED = (168, 52, 36)         # the X, the route
GOLD = (176, 138, 60)
RIVER = (96, 130, 140)
LAGOON = (120, 150, 150)
PARCH_LAND = (238, 222, 186)
PARCH_SEA = (206, 198, 168)
FAINT = (150, 128, 92)

# ------------------------------------------------------------- stroke font --
# Hand-inked single-stroke capitals on a 6-wide, 7-tall grid (y down).
# Each glyph is a list of strokes; each stroke is a list of (x, y) points.
# All map lettering is set in capitals, as on a period chart.
FONT = {
    "A": [[(0, 7), (2.5, 0), (5, 7)], [(1.3, 4.3), (3.7, 4.3)]],
    "B": [[(0, 0), (0, 7)],
          [(0, 0), (3.2, 0), (4.8, 1.2), (4.8, 2.6), (3.2, 3.5), (0, 3.5)],
          [(0, 3.5), (3.2, 3.5), (4.8, 4.8), (4.8, 6), (3.2, 7), (0, 7)]],
    "C": [[(4.8, 1.2), (3.2, 0), (1.4, 0), (0, 1.8), (0, 5.2), (1.4, 7), (3.2, 7), (4.8, 5.8)]],
    "D": [[(0, 0), (0, 7)], [(0, 0), (3, 0), (5, 1.8), (5, 5.2), (3, 7), (0, 7)]],
    "E": [[(0, 0), (0, 7)], [(0, 0), (4.6, 0)], [(0, 3.5), (3.4, 3.5)], [(0, 7), (4.6, 7)]],
    "F": [[(0, 0), (0, 7)], [(0, 0), (4.6, 0)], [(0, 3.5), (3.4, 3.5)]],
    "G": [[(4.8, 1.2), (3.2, 0), (1.4, 0), (0, 1.8), (0, 5.2), (1.4, 7), (3.2, 7), (4.8, 5.8), (4.8, 3.8), (3, 3.8)]],
    "H": [[(0, 0), (0, 7)], [(5, 0), (5, 7)], [(0, 3.5), (5, 3.5)]],
    "I": [[(1, 0), (4, 0)], [(2.5, 0), (2.5, 7)], [(1, 7), (4, 7)]],
    "J": [[(1.2, 0), (4.4, 0)], [(3.4, 0), (3.4, 5), (2.2, 7), (0.8, 5.8), (0.6, 4.4)]],
    "K": [[(0, 0), (0, 7)], [(4.6, 0), (0.8, 3.6)], [(2, 3.6), (4.8, 7)]],
    "L": [[(0, 0), (0, 7)], [(0, 7), (4.8, 7)]],
    "M": [[(0, 7), (0, 0), (2.5, 4), (5, 0), (5, 7)]],
    "N": [[(0, 7), (0, 0), (5, 7), (5, 0)]],
    "O": [[(1.4, 0), (3.6, 0), (5, 1.8), (5, 5.2), (3.6, 7), (1.4, 7), (0, 5.2), (0, 1.8), (1.4, 0)]],
    "P": [[(0, 0), (0, 7)], [(0, 0), (3.2, 0), (4.8, 1.2), (4.8, 2.6), (3.2, 3.5), (0, 3.5)]],
    "Q": [[(1.4, 0), (3.6, 0), (5, 1.8), (5, 5.2), (3.6, 7), (1.4, 7), (0, 5.2), (0, 1.8), (1.4, 0)],
          [(3, 4.8), (5, 7)]],
    "R": [[(0, 0), (0, 7)], [(0, 0), (3.2, 0), (4.8, 1.2), (4.8, 2.6), (3.2, 3.5), (0, 3.5)],
          [(2.2, 3.5), (5, 7)]],
    "S": [[(4.6, 1.2), (3.4, 0), (1.6, 0), (0.4, 1.2), (0.4, 2.4), (1.6, 3.5), (3.4, 3.8), (4.6, 4.8), (4.6, 6), (3.4, 7), (1.6, 7), (0.4, 5.8)]],
    "T": [[(0, 0), (5, 0)], [(2.5, 0), (2.5, 7)]],
    "U": [[(0, 0), (0, 5), (1.2, 7), (3.8, 7), (5, 5), (5, 0)]],
    "V": [[(0, 0), (2.5, 7), (5, 0)]],
    "W": [[(0, 0), (1.2, 7), (2.5, 3.5), (3.8, 7), (5, 0)]],
    "X": [[(0, 0), (5, 7)], [(5, 0), (0, 7)]],
    "Y": [[(0, 0), (2.5, 3.5)], [(5, 0), (2.5, 3.5)], [(2.5, 3.5), (2.5, 7)]],
    "Z": [[(0, 0), (5, 0)], [(5, 0), (0, 7)], [(0, 7), (5, 7)]],
    "0": [[(1.4, 0), (3.6, 0), (5, 1.8), (5, 5.2), (3.6, 7), (1.4, 7), (0, 5.2), (0, 1.8), (1.4, 0)],
          [(1.2, 5.2), (3.8, 1.8)]],
    "1": [[(1.2, 1.6), (2.5, 0)], [(2.5, 0), (2.5, 7)], [(1, 7), (4, 7)]],
    "2": [[(0.6, 1.6), (1.6, 0), (3.4, 0), (4.6, 1.4), (4.2, 3), (0.6, 7), (4.6, 7)]],
    "3": [[(0.6, 1.2), (1.8, 0), (3.4, 0), (4.8, 1.4), (4, 3.2), (2.4, 3.5)],
          [(2.4, 3.5), (4, 3.5), (4.8, 5.2), (3.6, 7), (1.8, 7), (0.6, 5.8)]],
    "4": [[(3.6, 0), (0.6, 4.8), (4.6, 4.8)], [(3.6, 0), (3.6, 7)]],
    "5": [[(4.6, 0), (0.6, 0), (0.6, 3.2), (3, 3.2), (4.6, 4.6), (4.2, 6.4), (2.6, 7), (1.2, 6.4)]],
    "6": [[(4, 1), (2.8, 0), (1.2, 0.8), (0.2, 2.6), (0.2, 5.2), (1.4, 7), (3, 7), (4.6, 5.6), (4.6, 4), (3.4, 2.8), (1.6, 2.8), (0.6, 4)]],
    "7": [[(0, 0), (5, 0)], [(4.2, 0), (1.6, 7)]],
    "8": [[(1.6, 0), (3.4, 0), (4.8, 1.6), (3.8, 3.5), (2.5, 3.5), (1.2, 3.5), (0.2, 1.6), (1.6, 0)],
          [(1.2, 3.5), (2.5, 3.5), (3.8, 3.5), (4.8, 5.2), (3.4, 7), (1.6, 7), (0.2, 5.2), (1.2, 3.5)]],
    "9": [[(1, 6), (2.2, 7), (3.8, 6.2), (4.8, 4.4), (4.8, 1.8), (3.6, 0), (1.8, 0), (0.4, 1.6), (0.6, 3.4), (2, 4.4), (3.6, 4.2), (4.4, 3)]],
    "'": [[(2.6, 0), (2.2, 2)]],
    ".": [[(2.4, 6.2), (2.4, 6.8)]],
    ",": [[(2.4, 5.4), (2, 7)]],
    "-": [[(0.6, 3.5), (4.4, 3.5)]],
    "&": [[(4.2, 1), (3, 0), (1.4, 0.6), (0.6, 2), (1.6, 3.4), (3.4, 3.6), (4.8, 4.6), (4.4, 6.2), (3, 7), (1.4, 6.6), (0.6, 5.2)],
          [(2.4, 3.4), (0.8, 6.6)]],
    ":": [[(2.4, 2), (2.4, 2.6)], [(2.4, 5), (2.4, 5.6)]],
    ";": [[(2.4, 2), (2.4, 2.6)], [(2.4, 5), (2, 7)]],
    "!": [[(2.5, 0), (2.5, 4.6)], [(2.4, 6.2), (2.4, 6.8)]],
    "?": [[(1, 1.4), (2.2, 0), (3.8, 0.4), (4.4, 1.8), (3.4, 3.4), (2.5, 3.8), (2.5, 4.8)],
          [(2.4, 6.2), (2.4, 6.8)]],
    "(": [[(4, 0.6), (2.2, 2), (2.2, 5), (4, 6.4)]],
    ")": [[(1, 0.6), (2.8, 2), (2.8, 5), (1, 6.4)]],
    "/": [[(4.4, 0), (0.6, 7)]],
    "=": [[(0.6, 2.4), (4.4, 2.4)], [(0.6, 4.6), (4.4, 4.6)]],
    "+": [[(2.5, 0.8), (2.5, 6.2)], [(0.6, 3.5), (4.4, 3.5)]],
    " ": [],
}

CHAR_W, CHAR_H = 6.0, 7.0


def text_width(text, scale):
    """Advance width of a string at the given font scale."""
    return len(text) * CHAR_W * scale * 0.92


# ------------------------------------------------------------------ canvas --
class Canvas:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.px = bytearray(w * h * 3)
        self.rng = random.Random(SEED)
        self._discs = {}

    # -- low level ------------------------------------------------------
    def _disc(self, r):
        if r not in self._discs:
            pts = []
            for dy in range(-r, r + 1):
                for dx in range(-r, r + 1):
                    if dx * dx + dy * dy <= r * r + r:
                        pts.append((dx, dy))
            self._discs[r] = pts
        return self._discs[r]

    def set(self, x, y, color):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i], self.px[i + 1], self.px[i + 2] = color

    def blend(self, x, y, color, alpha):
        """Alpha-blend a colour over the pixel at (x, y). alpha 0..1."""
        if 0 <= x < self.w and 0 <= y < self.h and alpha > 0:
            i = (y * self.w + x) * 3
            a = alpha
            self.px[i] = int(self.px[i] * (1 - a) + color[0] * a)
            self.px[i + 1] = int(self.px[i + 1] * (1 - a) + color[1] * a)
            self.px[i + 2] = int(self.px[i + 2] * (1 - a) + color[2] * a)

    def stamp(self, cx, cy, r, color):
        for dx, dy in self._disc(r):
            self.set(cx + dx, cy + dy, color)

    def blend_stamp(self, cx, cy, r, color, alpha):
        for dx, dy in self._disc(r):
            self.blend(cx + dx, cy + dy, color, alpha)

    # -- lines and curves ------------------------------------------------
    def line(self, x0, y0, x1, y1, color, width=1):
        x0, y0, x1, y1 = int(round(x0)), int(round(y0)), int(round(x1)), int(round(y1))
        dx, dy = abs(x1 - x0), abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy
        r = max(0, width // 2)
        while True:
            if width <= 1:
                self.set(x0, y0, color)
            else:
                self.stamp(x0, y0, r, color)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x0 += sx
            if e2 < dx:
                err += dx
                y0 += sy

    def polyline(self, pts, color, width=1, closed=False):
        seq = list(pts) + ([pts[0]] if closed else [])
        for a, b in zip(seq, seq[1:]):
            self.line(a[0], a[1], b[0], b[1], color, width)

    def dashed(self, pts, color, width=2, dash=9, gap=7):
        """Dashed polyline, following the points."""
        for a, b in zip(pts, pts[1:]):
            x0, y0, x1, y1 = a[0], a[1], b[0], b[1]
            length = math.hypot(x1 - x0, y1 - y0)
            if length == 0:
                continue
            steps = int(length)
            ux, uy = (x1 - x0) / length, (y1 - y0) / length
            on = True
            run = 0
            px, py = x0, y0
            for _ in range(steps):
                if on:
                    self.line(px, py, px + ux, py + uy, color, width)
                px += ux
                py += uy
                run += 1
                if on and run >= dash:
                    on, run = False, 0
                elif not on and run >= gap:
                    on, run = True, 0

    def curve(self, pts, color, width=1, samples=8):
        """Smooth Catmull-Rom curve through the given points."""
        out = []
        ext = [pts[0]] + list(pts) + [pts[-1]]
        for i in range(len(ext) - 3):
            p0, p1, p2, p3 = ext[i], ext[i + 1], ext[i + 2], ext[i + 3]
            for s in range(samples):
                t = s / samples
                t2, t3 = t * t, t * t * t
                x = 0.5 * ((2 * p1[0]) + (-p0[0] + p2[0]) * t
                           + (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2
                           + (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3)
                y = 0.5 * ((2 * p1[1]) + (-p0[1] + p2[1]) * t
                           + (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2
                           + (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3)
                out.append((x, y))
        out.append(pts[-1])
        self.polyline(out, color, width)

    def circle(self, cx, cy, r, color, width=1):
        n = max(24, int(2 * math.pi * r / 3))
        pts = [(cx + r * math.cos(2 * math.pi * i / n),
                cy + r * math.sin(2 * math.pi * i / n)) for i in range(n)]
        self.polyline(pts, color, width, closed=True)

    def disc(self, cx, cy, r, color):
        for y in range(int(cy - r), int(cy + r) + 1):
            for x in range(int(cx - r), int(cx + r) + 1):
                if (x - cx) ** 2 + (y - cy) ** 2 <= r * r:
                    self.set(x, y, color)

    def ellipse(self, cx, cy, rx, ry, color, width=1):
        n = max(32, int(2 * math.pi * max(rx, ry) / 3))
        pts = [(cx + rx * math.cos(2 * math.pi * i / n),
                cy + ry * math.sin(2 * math.pi * i / n)) for i in range(n)]
        self.polyline(pts, color, width, closed=True)

    def fill_ellipse(self, cx, cy, rx, ry, color, alpha=1.0):
        for y in range(int(cy - ry), int(cy + ry) + 1):
            dy = (y - cy) / ry
            if abs(dy) > 1:
                continue
            dx = rx * math.sqrt(1 - dy * dy)
            for x in range(int(cx - dx), int(cx + dx) + 1):
                if alpha >= 1.0:
                    self.set(x, y, color)
                else:
                    self.blend(x, y, color, alpha)

    def fill_polygon(self, pts, color):
        """Scanline fill of a simple polygon."""
        edges = []
        n = len(pts)
        for i in range(n):
            x0, y0 = pts[i]
            x1, y1 = pts[(i + 1) % n]
            if y0 == y1:
                continue
            edges.append((min(y0, y1), max(y0, y1), x0, y0, x1, y1))
        ymin = max(0, int(min(p[1] for p in pts)))
        ymax = min(self.h - 1, int(max(p[1] for p in pts)))
        for y in range(ymin, ymax + 1):
            xs = []
            for y0, y1, x0, yy0, x1, yy1 in edges:
                if y0 <= y < y1:
                    t = (y - yy0) / (yy1 - yy0)
                    xs.append(x0 + t * (x1 - x0))
            xs.sort()
            for a, b in zip(xs[::2], xs[1::2]):
                xa, xb = max(0, int(a)), min(self.w - 1, int(b))
                i = (y * self.w + xa) * 3
                for x in range(xa, xb + 1):
                    self.px[i], self.px[i + 1], self.px[i + 2] = color
                    i += 3

    # -- text -------------------------------------------------------------
    def text(self, x, y, s, scale, color, align="left", width=None, jitter=0.6):
        """Draw a string with the stroke font. (x, y) is the top-left, or the
        centre-top when align is 'center'. Returns the drawn width."""
        s = s.upper()
        w = text_width(s, scale)
        if align == "center":
            x = x - w / 2
        elif align == "right":
            x = x - w
        lw = max(1, int(round(scale * 0.55)))
        jrng = random.Random(SEED + sum(ord(ch) for ch in s) + int(x) + int(y))
        cx = x
        for ch in s:
            for stroke in FONT.get(ch, []):
                pts = []
                for gx, gy in stroke:
                    jx = jrng.uniform(-jitter, jitter) if jitter else 0
                    jy = jrng.uniform(-jitter, jitter) if jitter else 0
                    pts.append((cx + (gx + jx * 0.12) * scale,
                                y + (gy + jy * 0.12) * scale))
                self.polyline(pts, color, lw)
            cx += CHAR_W * scale * 0.92
        return w

    def text_lines(self, cx, y, lines, scale, color, gap=6):
        for line in lines:
            self.text(cx, y, line, scale, color, align="center")
            y += CHAR_H * scale + gap
        return y


# ------------------------------------------------------------------- PNG ---
def _chunk(kind, data):
    body = kind + data
    return (struct.pack(">I", len(data)) + body
            + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF))


def write_png(path, canvas):
    """Encode the canvas as an 8-bit RGB PNG, filter byte 0 per row."""
    raw = bytearray()
    w, h = canvas.w, canvas.h
    row_bytes = w * 3
    for y in range(h):
        raw.append(0)
        raw += canvas.px[y * row_bytes:(y + 1) * row_bytes]
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    png = (b"\x89PNG\r\n\x1a\n"
           + _chunk(b"IHDR", ihdr)
           + _chunk(b"IDAT", zlib.compress(bytes(raw), 9))
           + _chunk(b"IEND", b""))
    with open(path, "wb") as f:
        f.write(png)
    os.chmod(path, 0o644)
    return png


def readback_png(path):
    """Verify the file: signature, IHDR dims and fields (8-bit RGB,
    no interlace), chunk CRCs, no truncated chunks, no trailing bytes
    after IEND, IDAT present, IDAT decompresses to exactly (3*w+1)*h
    bytes with a filter byte of 0 on every row. Returns (width, height, size)."""
    data = open(path, "rb").read()
    assert data[:8] == b"\x89PNG\r\n\x1a\n", "bad PNG signature"
    pos, w, h, idat = 8, None, None, bytearray()
    while pos < len(data):
        assert pos + 12 <= len(data), f"truncated chunk header at offset {pos}"
        (ln,) = struct.unpack(">I", data[pos:pos + 4])
        kind = data[pos + 4:pos + 8]
        assert pos + 12 + ln <= len(data), (
            f"truncated {kind.decode('latin1')} chunk: claims {ln} bytes "
            f"but only {len(data) - pos - 12} remain")
        body = data[pos + 8:pos + 8 + ln]
        (crc,) = struct.unpack(">I", data[pos + 8 + ln:pos + 12 + ln])
        assert zlib.crc32(kind + body) & 0xFFFFFFFF == crc, f"bad CRC on {kind}"
        if kind == b"IHDR":
            w, h = struct.unpack(">II", body[:8])
            bit_depth, color_type, comp, filt, interlace = struct.unpack(">BBBBB", body[8:13])
            assert (bit_depth, color_type, comp, filt, interlace) == (8, 2, 0, 0, 0), (
                f"unexpected IHDR fields: bit depth {bit_depth}, color type {color_type}, "
                f"compression {comp}, filter {filt}, interlace {interlace} "
                f"(expected 8-bit RGB, no interlace)")
        elif kind == b"IDAT":
            idat += body
        elif kind == b"IEND":
            assert pos + 12 == len(data), (
                f"{len(data) - pos - 12} trailing byte(s) after IEND")
            break
        pos += 12 + ln
    assert w is not None and h is not None, "no IHDR chunk found"
    assert len(idat) > 0, "no IDAT chunk found"
    raw = zlib.decompress(bytes(idat))
    assert len(raw) == (3 * w + 1) * h, "IDAT length mismatch"
    row_bytes = 3 * w + 1
    bad_rows = [y for y in range(h) if raw[y * row_bytes] != 0]
    assert not bad_rows, (
        f"{len(bad_rows)} row(s) use a non-zero filter byte "
        f"(first: row {bad_rows[0]}); encoder must write filter 0 per row")
    return w, h, len(data)


# ------------------------------------------------------------ map drawing --
def island_outline(cx, cy, rx, ry, rng):
    """A wobbly closed coastline: an ellipse modulated by a few sines."""
    p1, p2, p3 = rng.uniform(0, 6.28), rng.uniform(0, 6.28), rng.uniform(0, 6.28)
    pts = []
    n = 140
    for i in range(n):
        t = 2 * math.pi * i / n
        r = (1 + 0.13 * math.sin(3 * t + p1)
               + 0.08 * math.sin(5 * t + p2)
               + 0.05 * math.sin(9 * t + p3))
        pts.append((cx + rx * r * math.cos(t), cy + ry * r * math.sin(t)))
    return pts


def parchment(c, island_pts):
    """Aged parchment: land and sea washes, low-res blotch noise, vignette."""
    rng = random.Random(SEED + 7)
    # coarse noise grid, bilinearly sampled so it compresses well
    GN = 64
    grid = [[rng.uniform(-13, 13) for _ in range(GN + 1)] for _ in range(GN + 1)]
    # island mask for the land/sea split
    mask = bytearray(W * H)
    edges = []
    n = len(island_pts)
    for i in range(n):
        x0, y0 = island_pts[i]
        x1, y1 = island_pts[(i + 1) % n]
        if y0 != y1:
            edges.append((min(y0, y1), max(y0, y1), x0, y0, x1, y1))
    for y in range(H):
        xs = []
        for y0, y1, x0, yy0, x1, yy1 in edges:
            if y0 <= y < y1:
                xs.append(x0 + (y - yy0) / (yy1 - yy0) * (x1 - x0))
        xs.sort()
        for a, b in zip(xs[::2], xs[1::2]):
            for x in range(max(0, int(a)), min(W, int(b) + 1)):
                mask[y * W + x] = 1
    cell = W / GN
    for y in range(H):
        gy = y / cell
        iy = min(GN - 1, int(gy))
        fy = gy - iy
        vy = 1.0 - 0.16 * max(0.0, (abs(y - H / 2) / (H / 2)) ** 3)
        row = y * W
        for x in range(W):
            gx = x / cell
            ix = min(GN - 1, int(gx))
            fx = gx - ix
            g00 = grid[iy][ix]
            g10 = grid[iy][ix + 1]
            g01 = grid[iy + 1][ix]
            g11 = grid[iy + 1][ix + 1]
            noise = (g00 * (1 - fx) * (1 - fy) + g10 * fx * (1 - fy)
                     + g01 * (1 - fx) * fy + g11 * fx * fy)
            vx = 1.0 - 0.16 * max(0.0, (abs(x - W / 2) / (W / 2)) ** 3)
            v = vy * vx
            base = PARCH_LAND if mask[row + x] else PARCH_SEA
            i = (row + x) * 3
            c.px[i] = max(0, min(255, int(base[0] * v + noise)))
            c.px[i + 1] = max(0, min(255, int(base[1] * v + noise)))
            c.px[i + 2] = max(0, min(255, int(base[2] * v + noise * 0.8)))
    # soft age blotches
    for _ in range(46):
        bx, by = rng.uniform(40, W - 40), rng.uniform(40, H - 40)
        brx, bry = rng.uniform(30, 130), rng.uniform(20, 90)
        tone = rng.choice([(120, 96, 58), (150, 120, 70), (100, 80, 50)])
        c.fill_ellipse(bx, by, brx, bry, tone, alpha=rng.uniform(0.03, 0.07))
    # burnt rim: a few dark scorch spots along the edges
    for _ in range(26):
        side = rng.randrange(4)
        if side == 0:
            bx, by = rng.uniform(0, W), rng.uniform(0, 26)
        elif side == 1:
            bx, by = rng.uniform(0, W), rng.uniform(H - 26, H)
        elif side == 2:
            bx, by = rng.uniform(0, 26), rng.uniform(0, H)
        else:
            bx, by = rng.uniform(W - 26, W), rng.uniform(0, H)
        c.fill_ellipse(bx, by, rng.uniform(14, 42), rng.uniform(8, 22),
                       (70, 48, 26), alpha=rng.uniform(0.10, 0.22))


def mountain(c, cx, cy, s):
    """A hachured peak: triangle outline, slope ticks, tiny summit cross."""
    c.polyline([(cx - s, cy + s * 0.7), (cx, cy - s), (cx + s, cy + s * 0.7)], INK, 2)
    c.line(cx, cy - s, cx, cy + s * 0.7, INK_SOFT, 1)
    for i in range(1, 4):
        t = i / 4
        x = cx - s + 2 * s * t
        y = cy + s * 0.7 - 1.7 * s * t
        c.line(x, y, x + 5, y + 7, INK_SOFT, 1)
        x2 = cx + s - 2 * s * t
        c.line(x2, y, x2 - 5, y + 7, INK_SOFT, 1)
    c.line(cx - 3, cy - s - 4, cx + 3, cy - s - 4, INK, 1)
    c.line(cx, cy - s - 7, cx, cy - s - 1, INK, 1)


def palm(c, cx, cy, s):
    """A small palm: leaning trunk, five drooping fronds, coconut dots."""
    c.curve([(cx, cy), (cx + 2, cy - s * 0.5), (cx + 5, cy - s)], INK, 2)
    top = (cx + 5, cy - s)
    for ang, ln in ((-150, 1.0), (-110, 1.1), (-70, 1.0), (-30, 0.95), (10, 0.8)):
        a = math.radians(ang)
        ex, ey = top[0] + ln * s * 0.85 * math.cos(a), top[1] + ln * s * 0.55 * math.sin(a)
        mx, my = top[0] + ln * s * 0.45 * math.cos(a), top[1] + ln * s * 0.5 * math.sin(a) - 4
        c.curve([top, (mx, my), (ex, ey + 7)], INK, 2)
    c.disc(top[0] - 2, top[1] + 3, 2, INK)
    c.disc(top[0] + 3, top[1] + 4, 2, INK)


def reed_tuft(c, cx, cy, s):
    for dx in (-6, -2, 2, 6):
        c.curve([(cx + dx, cy), (cx + dx + 2, cy - s * 0.6), (cx + dx - 1, cy - s)], INK_SOFT, 1)
        c.disc(cx + dx - 1, cy - s, 1, INK)


def compass_rose(c, cx, cy, r):
    """16-point wind rose: long cardinal points, short by-points, N in gold."""
    c.circle(cx, cy, r + 8, INK_SOFT, 1)
    c.circle(cx, cy, r + 2, INK, 1)
    for k in range(16):
        ang = math.radians(k * 22.5 - 90)
        long = k % 4 == 0
        half = k % 2 == 0
        tip = r if long else (r * 0.62 if half else r * 0.38)
        base = r * 0.16
        px, py = math.cos(ang), math.sin(ang)
        qx, qy = -py, px
        tip_pt = (cx + tip * px, cy + tip * py)
        left = (cx + base * qx, cy + base * qy)
        right = (cx - base * qx, cy - base * qy)
        col = GOLD if k == 0 else INK
        c.polyline([left, tip_pt, right], col, 2 if long else 1)
        c.line(cx, cy, tip_pt[0], tip_pt[1], col, 1)
    # fleur-de-lis north: a small crown of three petals above the N point
    nx, ny = cx, cy - r - 16
    c.polyline([(nx, ny - 8), (nx - 5, ny + 2), (nx, ny - 1), (nx + 5, ny + 2), (nx, ny - 8)], GOLD, 2)
    c.disc(nx, ny + 5, 2, GOLD)
    c.text(cx, cy - r - 52, "N", 3.0, INK, align="center")
    c.text(cx + r + 26, cy - 9, "E", 3.0, INK, align="center")
    c.text(cx, cy + r + 28, "S", 3.0, INK, align="center")
    c.text(cx - r - 30, cy - 9, "W", 3.0, INK, align="center")
    c.disc(cx, cy, 3, INK)


def ship(c, cx, cy, s):
    """A galleon at sail: hull, two masts, billowing sails, a flag."""
    # hull
    c.curve([(cx - s, cy), (cx - s * 0.7, cy + s * 0.35), (cx + s * 0.7, cy + s * 0.35), (cx + s, cy - s * 0.1)], INK, 2)
    c.line(cx - s, cy, cx + s, cy - s * 0.1, INK, 2)
    c.line(cx - s, cy - s * 0.28, cx - s * 0.82, cy - s * 0.05, INK, 2)  # sterncastle
    c.line(cx + s, cy - s * 0.1, cx + s * 0.86, cy - s * 0.32, INK, 2)   # bow
    # masts
    c.line(cx - s * 0.3, cy - s * 0.05, cx - s * 0.3, cy - s * 1.15, INK, 2)
    c.line(cx + s * 0.35, cy - s * 0.08, cx + s * 0.35, cy - s * 0.95, INK, 2)
    # sails (billow to the right)
    c.curve([(cx - s * 0.3, cy - s * 1.1), (cx - s * 0.05, cy - s * 0.9), (cx + s * 0.05, cy - s * 0.55), (cx - s * 0.3, cy - s * 0.35)], INK, 2)
    c.curve([(cx + s * 0.35, cy - s * 0.9), (cx + s * 0.6, cy - s * 0.72), (cx + s * 0.62, cy - s * 0.4), (cx + s * 0.35, cy - s * 0.28)], INK, 2)
    # flag
    c.polyline([(cx - s * 0.3, cy - s * 1.15), (cx - s * 0.02, cy - s * 1.08), (cx - s * 0.3, cy - s * 1.0)], RED, 2)
    # waterline
    for dx in (-14, 0, 14):
        c.curve([(cx + dx - 10, cy + s * 0.48), (cx + dx, cy + s * 0.42), (cx + dx + 10, cy + s * 0.48)], INK_SOFT, 1)


def serpent(c, cx, cy, s):
    """A sea serpent: three humps, a head, and a curling tail."""
    pts = []
    for i in range(41):
        t = i / 40
        x = cx - s + 2 * s * t
        y = cy + math.sin(t * math.pi * 2.2) * s * 0.28
        pts.append((x, y))
    c.curve(pts, INK, 3)
    for hx in (-0.55, 0.0, 0.55):
        hx_px = cx + hx * s
        hy = cy + math.sin((hx + 1) / 2 * math.pi * 2.2) * s * 0.28
        c.curve([(hx_px - 12, hy + 6), (hx_px, hy - 14), (hx_px + 12, hy + 6)], INK, 2)
    head = (cx + s + 8, cy + math.sin(math.pi * 2.2) * s * 0.28 - 6)
    c.curve([(cx + s - 4, cy + 2), (head[0] - 4, head[1] + 2), head], INK, 3)
    c.disc(head[0] + 3, head[1] - 3, 2, RED)  # the eye
    c.polyline([(head[0], head[1] - 2), (head[0] + 8, head[1] - 8), (head[0] + 10, head[1] - 1)], INK, 2)  # horn
    c.polyline([(head[0] + 4, head[1] + 3), (head[0] + 10, head[1] + 6)], INK, 1)  # jaw


def wave_marks(c, cx, cy, s, n=3):
    for i in range(n):
        y = cy + i * 12
        c.curve([(cx - s, y), (cx - s * 0.4, y - 5), (cx + s * 0.4, y - 5), (cx + s, y)], INK_SOFT, 1)


def gallows(c, cx, cy, s):
    """A little gallows on the bluff — the island's grim joke."""
    c.line(cx, cy, cx, cy - s, INK, 2)
    c.line(cx + s * 0.7, cy, cx + s * 0.7, cy - s, INK, 2)
    c.line(cx, cy - s, cx + s * 0.7, cy - s, INK, 2)
    c.line(cx + s * 0.35, cy - s, cx + s * 0.35, cy - s * 0.55, INK, 1)
    c.curve([(cx + s * 0.35, cy - s * 0.55), (cx + s * 0.5, cy - s * 0.4), (cx + s * 0.35, cy - s * 0.3)], INK, 1)


def anchor(c, cx, cy, s):
    c.line(cx, cy - s, cx, cy + s * 0.6, INK, 2)
    c.curve([(cx - s * 0.55, cy + s * 0.1), (cx, cy + s * 0.65), (cx + s * 0.55, cy + s * 0.1)], INK, 2)
    c.line(cx - s * 0.4, cy - s * 0.55, cx + s * 0.4, cy - s * 0.55, INK, 2)
    c.circle(cx, cy - s * 0.85, 3, INK, 1)


def draw_map(c):
    rng = random.Random(SEED)
    cx, cy = 480, 570
    island = island_outline(cx, cy, 305, 245, rng)
    parchment(c, island)

    # ---- rhumb lines, drawn before the land so they live only in the sea
    rcx, rcy = 862, 842
    for k in range(16):
        ang = math.radians(k * 22.5)
        x2, y2 = rcx + 900 * math.cos(ang), rcy + 900 * math.sin(ang)
        # faint: blend short segments by hand with a light colour
        steps = 60
        for i in range(steps):
            t = i / steps
            c.set(int(rcx + (x2 - rcx) * t), int(rcy + (y2 - rcy) * t), (190, 172, 128))

    # ---- the island itself
    c.fill_polygon(island, (240, 226, 192))
    c.polyline(island, INK, 3, closed=True)
    # inner coastline echo
    inner = [(cx + (x - cx) * 0.965, cy + (y - cy) * 0.965) for x, y in island]
    c.polyline(inner, INK_SOFT, 1, closed=True)

    # ---- Widow's Lagoon: a blue bay biting into the west coast
    lag = []
    for i in range(14):
        t = 2 * math.pi * i / 14
        rr = 1 + 0.14 * math.sin(3 * t + 1.1) + 0.07 * math.sin(5 * t + 2.3)
        lag.append((300 + 36 * rr * math.cos(t), 600 + 30 * rr * math.sin(t)))
    c.fill_polygon(lag, LAGOON)
    c.polyline(lag, INK, 2, closed=True)
    wave_marks(c, 300, 592, 18, n=2)

    # ---- river: Mermaid's Tears spring down to the lagoon
    c.curve([(438, 468), (400, 500), (372, 530), (352, 565), (332, 592)], RIVER, 3)
    c.curve([(438, 468), (400, 500), (372, 530), (352, 565), (332, 592)], INK_SOFT, 1)
    c.disc(438, 468, 7, RIVER)
    c.circle(438, 468, 7, INK, 1)

    # ---- Gallows Peak
    mountain(c, 432, 428, 34)
    mountain(c, 478, 448, 24)
    mountain(c, 392, 452, 20)

    # ---- Salt Marshes reeds
    for rx, ry in [(292, 470), (318, 452), (272, 492), (330, 486)]:
        reed_tuft(c, rx, ry, 16)

    # ---- Weeping Palms grove
    palm(c, 530, 648, 28)
    palm(c, 562, 662, 24)
    palm(c, 505, 668, 22)

    # ---- Hangman's Bluff: hatched cliff on the east shore + gallows
    c.polyline([(742, 470), (770, 500), (762, 540), (782, 575)], INK, 2)
    for i in range(6):
        t = i / 5
        x = 742 + (782 - 742) * t
        y = 470 + (575 - 470) * t
        c.line(x, y, x - 10, y + 12, INK_SOFT, 1)
    gallows(c, 742, 468, 26)

    # ---- Smuggler's Cove: the bay itself is the landmark (boat removed:
    # it collided with the crown label in revision 1)

    # ---- Dead Man's Anchorage: anchor + mooring dots on the south shore
    anchor(c, 470, 792, 16)
    for dx, dy in [(-30, 8), (34, 4), (58, 14)]:
        c.disc(470 + dx, 792 + dy, 2, INK)

    # ---- Wreck of the Gilded Gull: reef rocks + a broken mast, north-east
    for rx, ry, s in [(782, 332, 12), (806, 344, 9), (760, 348, 8)]:
        c.polyline([(rx - s, ry + 6), (rx, ry - s), (rx + s, ry + 6)], INK, 2)
    c.line(792, 330, 806, 292, INK, 2)  # snapped mast
    c.polyline([(806, 292), (824, 300), (806, 306)], RED, 2)  # torn flag
    c.curve([(748, 356), (770, 350), (792, 356), (816, 350)], INK_SOFT, 1)

    # ---- the dashed route: anchorage -> palms -> the X
    route = [(470, 792), (505, 748), (545, 712), (590, 700), (626, 692)]
    c.dashed(route, RED, width=3, dash=10, gap=8)
    # branch path from Smuggler's Cove
    c.dashed([(700, 760), (668, 730), (640, 705)], INK_SOFT, width=2, dash=6, gap=8)
    for px, py in route[1:-1]:
        c.disc(px, py, 2, RED)

    # ---- the X that marks the spot (inland, in the palm grove's clearing)
    X, Y = 640, 690
    c.line(X - 22, Y - 22, X + 22, Y + 22, RED, 6)
    c.line(X + 22, Y - 22, X - 22, Y + 22, RED, 6)
    c.circle(X, Y, 30, RED, 2)

    # ---- sea life and the ship
    serpent(c, 168, 852, 78)
    ship(c, 838, 392, 52)
    wave_marks(c, 130, 300, 26, n=3)
    wave_marks(c, 880, 560, 22, n=2)
    wave_marks(c, 120, 560, 20, n=2)
    wave_marks(c, 850, 200, 22, n=2)
    wave_marks(c, 250, 920, 20, n=2)

    # ---- compass rose, bottom right
    compass_rose(c, rcx, rcy, 62)

    # ---- labels (11 named places; each sits beside the thing it names)
    LS = 3.1  # place-label scale (~22 px tall)
    c.text(432, 350, "GALLOWS PEAK", LS, INK, align="center")
    c.text(315, 500, "MERMAID'S TEARS", 2.6, INK, align="center")
    c.text(298, 648, "WIDOW'S LAGOON", LS, INK, align="center")
    c.text(330, 398, "THE SALT MARSHES", 2.6, INK, align="center")
    c.text(470, 866, "DEAD MAN'S ANCHORAGE", LS, INK, align="center")
    c.text(680, 812, "SMUGGLER'S COVE", 2.6, INK, align="center")
    c.text(530, 596, "THE WEEPING PALMS", 2.6, INK, align="center")
    c.text(690, 738, "THE DROWNED KING'S", LS, INK, align="center")
    c.text(690, 764, "CROWN", LS, INK, align="center")
    c.text(680, 430, "HANGMAN'S BLUFF", 2.6, INK, align="center")
    c.text(782, 250, "WRECK OF THE", 2.6, INK, align="center")
    c.text(782, 272, "GILDED GULL", 2.6, INK, align="center")
    c.text(150, 250, "KRAKEN'S DEEP", LS, INK, align="center")
    # small jokes in the margins
    c.text(168, 782, "HERE BE KRAKENS", 2.2, INK_SOFT, align="center")
    c.text(300, 540, "THE WIDOW WAITS", 2.0, INK_SOFT, align="center")
    c.text(865, 306, "SHE STRUCK THE REEF", 1.9, INK_SOFT, align="center")

    # ---- title cartouche
    c.text(512, 40, "THE ISLE OF THE", 3.4, INK, align="center")
    c.text(512, 78, "DROWNED KING", 4.6, INK, align="center")
    c.text(512, 118, "SURVEY'D BY CAPT. E. MARLOWE - ANNO 1719", 2.1, INK_SOFT, align="center")
    c.text(512, 138, "THE CROWN LIES 12 PACES FROM THE OLD PALM", 2.1, INK_SOFT, align="center")
    c.line(300, 158, 724, 158, INK, 1)
    c.disc(300, 158, 3, INK)
    c.disc(724, 158, 3, INK)

    # ---- scale bar, bottom centre
    bx, by = 396, 956
    c.text(bx + 62, by - 26, "LEAGUES", 2.2, INK, align="center")
    for i, col in enumerate([(58, 40, 22), (238, 222, 186), (58, 40, 22), (238, 222, 186)]):
        x0 = bx + i * 31
        for y in range(by, by + 10):
            for x in range(x0, x0 + 31):
                c.set(x, y, col)
        c.line(x0, by, x0, by + 10, INK, 1)
    c.line(bx, by, bx + 124, by, INK, 1)
    c.line(bx, by + 10, bx + 124, by + 10, INK, 1)
    c.line(bx + 124, by, bx + 124, by + 10, INK, 1)
    c.text(bx, by + 14, "0", 2.0, INK, align="center")
    c.text(bx + 62, by + 14, "2", 2.0, INK, align="center")
    c.text(bx + 124, by + 14, "4", 2.0, INK, align="center")

    # ---- double-rule border with corner ornaments
    c.polyline([(18, 18), (1005, 18), (1005, 1005), (18, 1005)], INK, 2, closed=True)
    c.polyline([(26, 26), (997, 26), (997, 997), (26, 997)], INK_SOFT, 1, closed=True)
    for cxo, cyo in [(18, 18), (1005, 18), (18, 1005), (1005, 1005)]:
        c.circle(cxo, cyo, 7, GOLD, 2)
        c.disc(cxo, cyo, 2, GOLD)


# -------------------------------------------------------------------- main --
def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "entry.png")

    canvas = Canvas(W, H)
    draw_map(canvas)
    png = write_png(path, canvas)

    w, h, size = readback_png(path)
    assert (w, h) == (W, H), f"dimensions {w}x{h} != {W}x{H}"
    assert size <= 1048576, f"file too big: {size} bytes"
    mode = oct(os.stat(path).st_mode & 0o777)
    assert mode == "0o644", f"file mode {mode} != 0644"
    sha = hashlib.sha256(png).hexdigest()
    print(f"wrote {path}")
    print(f"dimensions: {w}x{h}")
    print(f"size: {size} bytes (limit 1048576)")
    print(f"sha256: {sha}")
    print(f"mode: {mode}")
    print("read-back: OK (signature, IHDR fields, CRCs, IDAT length, row filters)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
