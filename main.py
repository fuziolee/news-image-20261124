#!/usr/bin/env python3
"""News-image entry renderer: "The World in One Day - Tuesday, 24 November 2026".

Draws a dense newspaper front page (1024x1024) summing up 24 November 2026
world news: 4 hero stories, 12 small stories, 34 one-liners, a UTC timeline
and a world map. Standard library only: no Pillow, no network, no fonts
from disk. Text is drawn with a bitmap font defined in this file, and the
PNG is encoded by hand (zlib + struct). Output is deterministic: two runs
produce byte-identical files.

Usage:  python3 main.py
Writes entry.png to $MAKEFUN_OUTPUT_DIR (or /output, or ./entry.png).
"""

import os
import struct
import sys
import zlib

# ---------------------------------------------------------------------------
# Bitmap font: every glyph is a 5-wide x 9-tall grid ('#' = ink, '.' = blank).
# Capitals and digits occupy rows 0-6. Lowercase x-height letters occupy
# rows 2-6, ascenders rows 0-6, descenders rows 2-8 (they drop below the
# baseline, which is what keeps lowercase 'g' visibly distinct from '9':
# '9' is full height with its tail curving left inside the cap height,
# while 'g' is x-height with a tail that drops below the baseline and
# hooks LEFT along the bottom row).
# ---------------------------------------------------------------------------

_BLANK = "....."


def _c(*rows):
    """Capital / digit glyph: 7 rows given, padded with 2 blank rows."""
    return tuple(rows) + (_BLANK, _BLANK)


def _x(*rows):
    """Lowercase x-height glyph: 5 rows given, 2 blank above and below."""
    return (_BLANK, _BLANK) + tuple(rows) + (_BLANK, _BLANK)


def _a(*rows):
    """Lowercase ascender glyph: 7 rows given, padded with 2 blank rows."""
    return tuple(rows) + (_BLANK, _BLANK)


def _d(*rows):
    """Lowercase descender glyph: 7 rows given (rows 2-8), 2 blank above."""
    return (_BLANK, _BLANK) + tuple(rows)


def _r(*rows):
    """Raw glyph: all 9 rows given."""
    return tuple(rows)


FONT = {
    # --- capitals ---
    "A": _c(".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    "B": _c("####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."),
    "C": _c(".###.", "#...#", "#....", "#....", "#....", "#...#", ".###."),
    "D": _c("####.", "#...#", "#...#", "#...#", "#...#", "#...#", "####."),
    "E": _c("#####", "#....", "#....", "####.", "#....", "#....", "#####"),
    "F": _c("#####", "#....", "#....", "####.", "#....", "#....", "#...."),
    "G": _c(".###.", "#...#", "#....", "#.###", "#...#", "#...#", ".###."),
    "H": _c("#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    "I": _c(".###.", "..#..", "..#..", "..#..", "..#..", "..#..", ".###."),
    "J": _c("..###", "....#", "....#", "....#", "....#", "#...#", ".###."),
    "K": _c("#...#", "#..#.", "#.#..", "##...", "#.#..", "#..#.", "#...#"),
    "L": _c("#....", "#....", "#....", "#....", "#....", "#....", "#####"),
    "M": _c("#...#", "##.##", "#.#.#", "#.#.#", "#...#", "#...#", "#...#"),
    "N": _c("#...#", "##..#", "##..#", "#.#.#", "#..##", "#..##", "#...#"),
    "O": _c(".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    "P": _c("####.", "#...#", "#...#", "####.", "#....", "#....", "#...."),
    "Q": _c(".###.", "#...#", "#...#", "#...#", "#.#.#", "#..#.", ".##.#"),
    "R": _c("####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"),
    "S": _c(".####", "#....", "#....", ".###.", "....#", "....#", "####."),
    "T": _c("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."),
    "U": _c("#...#", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    "V": _c("#...#", "#...#", "#...#", "#...#", "#...#", ".#.#.", "..#.."),
    "W": _c("#...#", "#...#", "#...#", "#.#.#", "#.#.#", "##.##", "#...#"),
    "X": _c("#...#", "#...#", ".#.#.", "..#..", ".#.#.", "#...#", "#...#"),
    "Y": _c("#...#", "#...#", ".#.#.", "..#..", "..#..", "..#..", "..#.."),
    "Z": _c("#####", "....#", "...#.", "..#..", ".#...", "#....", "#####"),
    # --- digits ---
    # '9' is full height: closed bowl on top, tail down the right side
    # curving left on the LAST row of the cap height. 'g' (below) is
    # x-height with a descender - they cannot be confused.
    "0": _c(".###.", "#...#", "#..##", "#.#.#", "##..#", "#...#", ".###."),
    "1": _c("..#..", ".##..", "..#..", "..#..", "..#..", "..#..", ".###."),
    "2": _c(".###.", "#...#", "....#", "...#.", "..#..", ".#...", "#####"),
    "3": _c("####.", "....#", "....#", ".###.", "....#", "....#", "####."),
    "4": _c("...#.", "..##.", ".#.#.", "#..#.", "#####", "...#.", "...#."),
    "5": _c("#####", "#....", "####.", "....#", "....#", "#...#", ".###."),
    "6": _c(".###.", "#....", "#....", "####.", "#...#", "#...#", ".###."),
    "7": _c("#####", "....#", "...#.", "..#..", "..#..", "..#..", "..#.."),
    "8": _c(".###.", "#...#", "#...#", ".###.", "#...#", "#...#", ".###."),
    "9": _c(".###.", "#...#", "#...#", ".####", "....#", "....#", ".###."),
}

# --- lowercase ---
# 'g': single-story, closed upper bowl, tail down the right side that
# drops BELOW the baseline and hooks LEFT along the bottom row. Compare
# with '9' above: different height, different tail, different bowl.
FONT.update({
    "a": _x(".###.", "....#", ".####", "#...#", ".###."),
    "b": _a("#....", "#....", "####.", "#...#", "#...#", "#...#", "####."),
    "c": _x(".###.", "#....", "#....", "#....", ".###."),
    "d": _a("....#", "....#", ".####", "#...#", "#...#", "#...#", ".###."),
    "e": _x(".###.", "#...#", "#####", "#....", ".###."),
    "f": _a("..##.", ".#...", ".#...", "####.", ".#...", ".#...", ".#..."),
    "g": _d(".###.", "#...#", "#...#", ".###.", "....#", "#...#", "####."),
    "h": _a("#....", "#....", "####.", "#...#", "#...#", "#...#", "#...#"),
    "i": _a("..#..", ".....", "..#..", "..#..", "..#..", "..#..", ".###."),
    "j": _r("..#..", ".....", "...#.", "...#.", "...#.", "...#.", "...#.",
            "...#.", ".##.."),
    "k": _a("#....", "#....", "#..#.", "#.#..", "##...", "#.#..", "#..#."),
    "l": _a("..#..", "..#..", "..#..", "..#..", "..#..", "..#..", ".###."),
    "m": _x("##.#.", "#.#.#", "#.#.#", "#.#.#", "#.#.#"),
    "n": _x("####.", "#...#", "#...#", "#...#", "#...#"),
    "o": _x(".###.", "#...#", "#...#", "#...#", ".###."),
    "p": _d("####.", "#...#", "#...#", "####.", "#....", "#....", "#...."),
    "q": _d(".###.", "#...#", "#...#", ".###.", "....#", "....#", "....#"),
    "r": _x("#.##.", "##..#", "#....", "#....", "#...."),
    "s": _x(".####", "#....", ".###.", "....#", "####."),
    "t": _a(".#...", ".#...", "####.", ".#...", ".#...", ".#...", ".##.."),
    "u": _x("#...#", "#...#", "#...#", "#...#", ".###."),
    "v": _x("#...#", "#...#", "#...#", ".#.#.", "..#.."),
    "w": _x("#...#", "#.#.#", "#.#.#", "##.##", "#...#"),
    "x": _x("#...#", ".#.#.", "..#..", ".#.#.", "#...#"),
    "y": _d("#...#", "#...#", "#...#", ".###.", "..#..", "..#..", ".##.."),
    "z": _x("#####", "...#.", "..#..", ".#...", "#####"),
})

# --- punctuation and symbols ---
FONT.update({
    " ": _r(*[_BLANK] * 9),
    ".": _r(*[_BLANK] * 6, ".##..", _BLANK, _BLANK),
    ",": _r(*[_BLANK] * 5, ".##..", ".##..", ".#...", "#...."),
    ";": _r(_BLANK, _BLANK, ".##..", _BLANK, _BLANK, ".##..", ".##..",
            ".#...", "#...."),
    ":": _r(_BLANK, _BLANK, ".##..", ".##..", _BLANK, ".##..", ".##..",
            _BLANK, _BLANK),
    "!": _c("..#..", "..#..", "..#..", "..#..", "..#..", ".....", "..#.."),
    "?": _c(".###.", "#...#", "....#", "...#.", "..#..", ".....", "..#.."),
    "'": _c("..#..", "..#..", ".#...", ".....", ".....", ".....", "....."),
    '"': _c(".#.#.", ".#.#.", ".#.#.", ".....", ".....", ".....", "....."),
    "(": _c("...#.", "..#..", ".#...", ".#...", ".#...", "..#..", "...#."),
    ")": _c(".#...", "..#..", "...#.", "...#.", "...#.", "..#..", ".#..."),
    "-": _c(".....", ".....", ".....", ".###.", ".....", ".....", "....."),
    "\u2013": _c(".....", ".....", ".....", "#####", ".....", ".....", "....."),
    "\u2014": _c(".....", ".....", ".....", "#####", ".....", ".....", "....."),
    "/": _c("....#", "...#.", "...#.", "..#..", ".#...", ".#...", "#...."),
    "%": _c("##..#", "##.#.", "..#..", ".#...", "#..##", "#..##", "....."),
    "&": _c(".##..", "#..#.", "#.#..", ".#...", "#.#.#", "#..#.", ".##.#"),
    "$": _c("..#..", ".####", "#.#..", ".###.", "..#.#", "####.", "..#.."),
    "#": _c(".#.#.", ".#.#.", "#####", ".#.#.", "#####", ".#.#.", ".#.#."),
    "+": _c(".....", "..#..", "..#..", "#####", "..#..", "..#..", "....."),
    "=": _c(".....", ".....", "#####", ".....", "#####", ".....", "....."),
    "*": _c(".....", ".#.#.", ".###.", "#####", ".###.", ".#.#.", "....."),
    "\u00b7": _r(_BLANK, _BLANK, _BLANK, ".##..", _BLANK, _BLANK, _BLANK,
                _BLANK, _BLANK),
    "\u20ac": _c(".###.", "#...#", "#....", "####.", "#....", "#...#", ".###."),
    "\u2022": _r(_BLANK, _BLANK, _BLANK, ".###.", ".###.", _BLANK, _BLANK,
                _BLANK, _BLANK),
    "\u00b0": _c(".##..", "#..#.", ".##..", ".....", ".....", ".....", "....."),
    "<": _c("...#.", "..#..", ".#...", "#....", ".#...", "..#..", "...#."),
    ">": _c(".#...", "..#..", "...#.", "....#", "...#.", "..#..", ".#..."),
    "_": _c(".....", ".....", ".....", ".....", ".....", ".....", "#####"),
    "[": _c(".###.", ".#...", ".#...", ".#...", ".#...", ".#...", ".###."),
    "]": _c(".###.", "...#.", "...#.", "...#.", "...#.", "...#.", ".###."),
    "\\": _c("#....", ".#...", ".#...", "..#..", "...#.", "...#.", "....#"),
    "@": _c(".###.", "#...#", "#.###", "#.#.#", "#.###", "#....", ".###."),
    "~": _c(".....", ".....", ".##.#", "#.#.#", ".....", ".....", "....."),
    "^": _c("..#..", ".#.#.", ".....", ".....", ".....", ".....", "....."),
    "`": _c(".#...", "..#..", ".....", ".....", ".....", ".....", "....."),
    "{": _c("..##.", ".#...", ".#...", ".##..", ".#...", ".#...", "..##."),
    "}": _c(".##..", "...#.", "...#.", "..##.", "...#.", "...#.", ".##.."),
    "|": _c("..#..", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."),
})

# Normalise curly quotes etc. to glyphs we have.
NORMALISE = {
    "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"',
    "\u2026": "...", "\u00a0": " ",
}

_FALLBACK = FONT["?"]


def glyph_rows(ch):
    ch = NORMALISE.get(ch, ch)
    return FONT.get(ch, _FALLBACK)

# ---------------------------------------------------------------------------
# Canvas + PNG encoder (stdlib only)
# ---------------------------------------------------------------------------

PAPER = (247, 241, 222)
INK = (22, 19, 16)
RED = (178, 34, 34)
LIGHT_RULE = (176, 164, 138)
LAND = (122, 138, 96)
WHITE = (255, 255, 255)

REGION_COLOURS = {
    "Europe": (37, 99, 180),
    "Middle East": (214, 110, 24),
    "Asia": (122, 63, 160),
    "Americas": (178, 34, 34),
    "Africa": (34, 139, 60),
    "Oceania": (0, 139, 139),
    "Global": (110, 110, 110),
}


class Canvas:
    def __init__(self, w, h, bg):
        self.w = w
        self.h = h
        self.px = bytearray(w * h * 3)
        self.fill_rect(0, 0, w, h, bg)

    def set(self, x, y, colour):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i], self.px[i + 1], self.px[i + 2] = colour

    def fill_rect(self, x, y, w, h, colour):
        x0 = max(0, x)
        y0 = max(0, y)
        x1 = min(self.w, x + w)
        y1 = min(self.h, y + h)
        r, g, b = colour
        for yy in range(y0, y1):
            base = (yy * self.w + x0) * 3
            for xx in range(x0, x1):
                i = base + (xx - x0) * 3
                self.px[i], self.px[i + 1], self.px[i + 2] = r, g, b

    def hline(self, x, y, w, colour, thick=1):
        self.fill_rect(x, y, w, thick, colour)

    def vline(self, x, y, h, colour, thick=1):
        self.fill_rect(x, y, thick, h, colour)

    def rect_outline(self, x, y, w, h, colour, thick=1):
        self.hline(x, y, w, colour, thick)
        self.hline(x, y + h - thick, w, colour, thick)
        self.vline(x, y, h, colour, thick)
        self.vline(x + w - thick, y, h, colour, thick)

    def fill_circle(self, cx, cy, r, colour):
        for yy in range(cy - r, cy + r + 1):
            for xx in range(cx - r, cx + r + 1):
                if (xx - cx) ** 2 + (yy - cy) ** 2 <= r * r:
                    self.set(xx, yy, colour)

    def circle_outline(self, cx, cy, r, colour, thick=1):
        for yy in range(cy - r - 1, cy + r + 2):
            for xx in range(cx - r - 1, cx + r + 2):
                d = ((xx - cx) ** 2 + (yy - cy) ** 2) ** 0.5
                if abs(d - r) <= thick / 2.0 + 0.4:
                    self.set(xx, yy, colour)


def _png_chunk(kind, data):
    chunk = struct.pack(">I", len(data)) + kind + data
    chunk += struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    return chunk


def write_png(path, canvas):
    w, h = canvas.w, canvas.h
    raw = bytearray()
    for y in range(h):
        raw.append(0)
        raw += canvas.px[y * w * 3:(y + 1) * w * 3]
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n"
    png += _png_chunk(b"IHDR", ihdr)
    png += _png_chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    png += _png_chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)


# ---------------------------------------------------------------------------
# Text engine
# ---------------------------------------------------------------------------

def char_width(scale):
    return int(round(5 * scale))


def char_gap(scale):
    return 1 if scale <= 2 else 2


def advance(scale):
    return char_width(scale) + char_gap(scale)


def bold_px(scale):
    """Extra output pixels boldening adds to each glyph stroke.

    A fixed small amount: one font pixel of extra width would merge
    adjacent strokes at large scales (a 5px stroke + 5px bold = 10px
    strokes with 5px gaps), so boldening grows much slower than scale.
    """
    return max(1, int(round(scale / 3.0)))


def text_width(s, scale, bold=False):
    w = 0
    for ch in s:
        w += advance(scale)
    if s:
        w -= char_gap(scale)
    if bold:
        w += bold_px(scale)
    return w


def line_height(scale):
    return int(round(9 * scale)) + (1 if scale <= 1 else 2)


def draw_text(cv, x, y, s, scale, colour, bold=False):
    """Draw text with its top at y. Returns the x just past the text."""
    cw = char_width(scale)
    chh = int(round(9 * scale))
    gap = char_gap(scale)
    cx = x
    for ch in s:
        rows = glyph_rows(ch)
        for fy in range(9):
            row = rows[fy]
            oy0 = y + (fy * chh) // 9
            oy1 = y + ((fy + 1) * chh) // 9
            if oy1 <= oy0:
                oy1 = oy0 + 1
            for fx in range(5):
                if row[fx] != "#":
                    continue
                ox0 = cx + (fx * cw) // 5
                ox1 = cx + ((fx + 1) * cw) // 5
                if ox1 <= ox0:
                    ox1 = ox0 + 1
                if bold:
                    ox1 += bold_px(scale)
                cv.fill_rect(ox0, oy0, ox1 - ox0, oy1 - oy0, colour)
        cx += advance(scale)
    return cx


def draw_text_centred(cv, cx, y, s, scale, colour, bold=False):
    draw_text(cv, cx - text_width(s, scale, bold) // 2, y, s, scale,
              colour, bold)


def wrap_text(s, scale, max_w, bold=False):
    """Greedy word wrap. Returns a list of lines that fit max_w."""
    words = s.split(" ")
    lines = []
    cur = ""
    for word in words:
        trial = word if not cur else cur + " " + word
        if text_width(trial, scale, bold) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def draw_wrapped(cv, x, y, s, scale, colour, max_w, bold=False,
                 max_lines=None, lh=None):
    """Draw wrapped text, return y just below the last line."""
    if lh is None:
        lh = line_height(scale)
    lines = wrap_text(s, scale, max_w, bold)
    if max_lines is not None:
        lines = lines[:max_lines]
    for i, line in enumerate(lines):
        draw_text(cv, x, y + i * lh, line, scale, colour, bold)
    return y + len(lines) * lh

# ---------------------------------------------------------------------------
# The 50 stories of Tuesday, 24 November 2026.
# Region totals: Europe 10, Middle East 9, Asia 8, Americas 8, Africa 8,
# Oceania 5, Global 2 = 50. CLAIM = one side's account, not independently
# confirmed. Date rule: happened or first reported 24 Nov 2026.
# ---------------------------------------------------------------------------

HEROES = [
    {
        "num": 1, "region": "Middle East", "topic": "CONFLICT", "claim": True,
        "headline": "Iran claims three tankers hit mines in Strait of Hormuz",
        "summary": "Iran's Revolutionary Guard says three \"violating\" oil "
        "tankers caught fire after striking naval mines in the strait, "
        "despite a US escort; no vessel names given and no maritime "
        "authority has confirmed it. (Reuters, 24 Nov)",
    },
    {
        "num": 2, "region": "Europe", "topic": "WAR", "claim": False,
        "headline": "Russian strike kills 2, injures 40 in Zaporizhzhia",
        "summary": "An overnight strike partly destroyed a five-storey "
        "apartment block and a house; officials said 2 people were killed "
        "and 40 injured, including four children. (Reuters, 24 Nov)",
    },
    {
        "num": 3, "region": "Americas", "topic": "CONFLICT", "claim": True,
        "headline": "Car bomb hits governor's office in Colombia; 23 hurt",
        "summary": "A car bomb exploded outside the Meta governor's office "
        "in Villavicencio, injuring 23 people; the president blamed "
        "drug-trafficking groups, but no group claimed it. "
        "(JKN / News Central TV, 24 Nov)",
    },
    {
        "num": 4, "region": "Asia", "topic": "DEFENCE", "claim": False,
        "headline": "Russian warplanes enter South Korea's air zone; "
        "jets scrambled",
        "summary": "Several Russian military aircraft entered South Korea's "
        "air defence identification zone near Ulleung Island; jets were "
        "scrambled and a brief island alert lifted within minutes. No "
        "airspace violation. (Reuters, 24 Nov)",
    },
]

SMALLS = [
    ("Europe", "WAR", False,
     "Zelenskyy confirms Ukraine hit Russian ship Sparta II",
     "Kyiv says the drone strike in the Gulf of Finland targeted a weapons "
     "cargo; the ship was towed to St Petersburg. (Bloomberg, 24 Nov)"),
    ("Europe", "DIPLOMACY", False,
     "Moscow warns Estonia it is 'on the verge of triggering open war'",
     "Russia summoned Estonia's envoy after Tallinn said it will close its "
     "land border with Russia from 1 December. (Reuters, 24 Nov)"),
    ("Europe", "SECURITY", True,
     "NATO vows to defend space as Russia 'may launch nuclear satellite'",
     "Reports say Western intelligence believes Russia could launch a "
     "nuclear-armed satellite within weeks; Moscow dismisses the claims. "
     "(Defense News, 24 Nov)"),
    ("Middle East", "CONFLICT", False,
     "Israeli strikes kill six in Gaza, including Hamas security chief",
     "Medics said Naeem Abu Nahel and two police officers were among the "
     "dead; 1,679 Palestinians have been killed since the October 2025 "
     "ceasefire. (Reuters, 24 Nov)"),
    ("Middle East", "DIPLOMACY", False,
     "Board of Peace: Hamas agreed Gaza disarmament roadmap",
     "Factions agreed a 15-point plan on 30 July to give up weapons, the "
     "board told the UN; implementation remains limited. (JBizNews, 24 Nov)"),
    ("Asia", "SPACE", False,
     "China unveils Shenzhou-24 crew with first foreign astronaut",
     "Pakistan's Zeeshan Ali will be the first foreign astronaut aboard "
     "Tiangong; launch set for 25 Nov. (Xinhua, 24 Nov)"),
    ("Asia", "POLITICS", True,
     "Indonesia charges ex-police chief with treason",
     "Listyo Sigit is accused of a wiretap plot to undermine President "
     "Prabowo; treason carries a possible death penalty. (Reuters, 24 Nov)"),
    ("Asia", "POLITICS", True,
     "Hasina says she will return to Bangladesh on 16 December",
     "The ousted PM set a date for the first time; Dhaka says she can "
     "return only by extradition, \"in handcuffs\". (Reuters, 24 Nov)"),
    ("Asia", "DISASTER", False,
     "5.6 quake hits Nepal's far east; felt across three countries",
     "The quake struck Taplejung near the Tibet border at 07:17 local; "
     "tremors were felt in India, Bhutan and Bangladesh. No casualties "
     "reported. (The Hindu, 24 Nov)"),
    ("Africa", "POLITICS", False,
     "Madagascar seeks arrest of ex-president Rajoelina",
     "Warrants are sought for the ousted former president and a former "
     "prime minister. (Africanews, 24 Nov)"),
    ("Africa", "CONFLICT", True,
     "DR Congo military aircraft missing as rebels claim shoot-down",
     "Kinshasa says a military plane is missing; rebels claim they shot it "
     "down. Unconfirmed. (BBC Africa, 24 Nov)"),
    ("Oceania", "CLIMATE", False,
     "Kiribati evacuates all of Kanton Island with a day's notice",
     "All 40-50 residents were relocated to Tarawa over El Nino "
     "conditions; return may take four years. (TVNZ / PINA, 24 Nov)"),
]

ONE_LINERS = [
    # Europe (6)
    ("EU Parliament debates inflation, Hungary and 2027 budget in "
     "Strasbourg (Europe Says)"),
    ("Visegrad leaders reject Costa's \u20ac1.58tn EU budget plan "
     "(Reuters)"),
    ("European gas prices rise for a fourth day as cold snap looms "
     "(OilPrice)"),
    ("EU car sales up 5.4% in October; battery EVs take 23.4% share "
     "(ACEA)"),
    ("UK PM Burnham: Tory welfare cuts would cause 'social chaos' "
     "(Daily Mirror)"),
    ("Pentagon yet to approve about 60 Patriot interceptors for Ukraine "
     "(Financial Times)"),
    # Middle East (6)
    ("Netanyahu presses Trump for renewed strikes on Iran "
     "(The Business Standard)"),
    ("Gulf leaders meet in Qatar to avert new US\u2013Iran strikes "
     "(Times of Middle East)"),
    ("Israel arrests 10 after settler attacks on Palestinians and "
     "diplomats (Times of Middle East)"),
    ("Thousands displaced as Israeli siege tightens on Hebron "
     "(Times of Middle East)"),
    ("Baghdad orders federal ministry to run oilfields in Kurdish-held "
     "areas (Reuters)"),
    ("Flydubai cleared to resume Dubai\u2013Tel Aviv flights (Reuters)"),
    # Asia (4)
    ("Kospi jumps 7.2%, Nikkei 3.9% as Nvidia CEO comeback lifts Asian "
     "tech (SCMP)"),
    ("Malaysia tells data centres to shun seven US-blacklisted firms "
     "(BusinessMirror)"),
    ("Anwar: Beijing 'extremely reasonable' in South China Sea talks "
     "(SCMP)"),
    ("Kim Yo Jong threatens to close Switzerland's Pyongyang office "
     "(AP / KCNA)"),
    # Americas (7)
    ("Trump pardons turkeys Freedom and Feathers at the White House "
     "(White House)"),
    ("Rubio: US did not help Flavio Bolsonaro flee Brazil "
     "(Al Jazeera)"),
    ("Court video shows Bolsonaro damaging ankle monitor with hot iron "
     "(DPA)"),
    ("WHO chief Tedros visits Cuba amid health-system collapse "
     "(Al Jazeera)"),
    ("Miss Universe crowns 75th winner in San Juan (Parade)"),
    ("Wells Fargo terms making customers liable for their AI agents take "
     "effect (The Why Daily)"),
    ("Canada and Qatar to sign investment protection agreement "
     "(Reuters)"),
    # Africa (6)
    ("60+ killed in reprisal attacks in Niger State, Nigeria "
     "(BusinessDay)"),
    ("Police confirm six dead in attack on Delta campaign convoy "
     "(JolibaLive)"),
    ("DA and ActionSA strike six-party coalition deal in Nelson Mandela "
     "Bay (IOL)"),
    ("Joburg mayoral vote delayed as coalition talks continue "
     "(AllAfrica)"),
    ("Amnesty: Ethiopia Tigray strikes should be probed as war crimes "
     "(Reuters)"),
    ("Fighting near Ebola hospital traps DR Congo responders "
     "(UN News)"),
    # Oceania (4)
    ("Coalition opposes Australia\u2013Vanuatu treaty over net-zero clause "
     "(AAP)"),
    ("Australia seeks Solomon Islands pact as PM Wale arrives in "
     "Canberra (Bloomberg)"),
    ("PNG parliament begins vote on Bougainville independence "
     "ratification (The Conversation)"),
    ("Fiji shuts all schools for five days as El Nino drought deepens "
     "(PINA)"),
    # Global (1)
    ("World ran 1.46C above pre-industrial as strongest-ever El Nino "
     "looms (Beyond2C / NASA)"),
]

TIMELINE = [
    ("00:48", "Russian warplanes enter South Korea's air zone; jets "
     "scrambled (Reuters)"),
    ("02:30", "Car bomb explodes outside Meta governor's office, "
     "Villavicencio (JKN)"),
    ("07:01", "60+ killed in Nigeria reprisal attacks first reported "
     "(BusinessDay)"),
    ("10:39", "Rubio: US did not help Flavio Bolsonaro flee Brazil "
     "(Al Jazeera)"),
    ("12:32", "Madagascar seeks arrest warrants for ex-president "
     "Rajoelina (Africanews)"),
    ("19:00", "Trump pardons Thanksgiving turkeys Freedom and Feathers "
     "(White House)"),
]

# Stylised world map, 56 columns x 28 rows, '#' = land. Equirectangular:
# col 0 = 180W, col 55 = 180E; row 0 = 90N, row 27 = 60S.
MAP_ROWS = [
    "........................................................",
    "........####...###.....................................",
    "...######..########..###..........##################....",
    "..###############...####..######.####################..",
    ".....###########.....#..########.####################..",
    ".....###########....#..#######..#####################..",
    ".....##########......#######....##########..#########...",
    ".....#########......#######.....#########..##########...",
    ".....#########......######..############..########..##..",
    ".....#########.......####..#########..##########..###...",
    "......########......###############..######.#####.......",
    "......####..........##############..#####..####.........",
    ".......###..........#############..#####..####..........",
    ".........##.........############...####...###...........",
    ".........######....##########.......##...####...........",
    ".........#######....#########...........######..........",
    ".........#######....########............######..........",
    ".........######......######.............######..........",
    ".........######.......####..............#######.........",
    ".........######.......###..............########.........",
    ".........#####........###..............########.........",
    ".........#####........##...............#######..#.......",
    ".........####.........##...............######....##......",
    ".........####..........................###.......#.......",
    ".........###............................................",
    ".........##.............................................",
    ".........##.............................................",
    "........................................................",
]

# Hero dot positions on the map grid (col, row): Hormuz, Zaporizhzhia,
# Villavicencio (Colombia), Ulleung Island (South Korea).
HERO_DOTS = [(37, 12), (33, 8), (17, 16), (48, 10)]

# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------

W = H = 1024
MX = 20            # side margin
CW = W - 2 * MX    # content width = 984
RIGHT = W - MX     # 1004


def draw_hero(cv, x, y, w, hero):
    colour = REGION_COLOURS[hero["region"]]
    # Numbered circle.
    cx, cy = x + 13, y + 13
    cv.fill_circle(cx, cy, 12, colour)
    draw_text_centred(cv, cx, cy - 7, str(hero["num"]), 1.5, WHITE, bold=True)
    # Tag line: REGION · TOPIC [+ CLAIM].
    tx = x + 32
    tag = hero["region"].upper() + " \u00b7 " + hero["topic"]
    nx = draw_text(cv, tx, y + 2, tag, 1, colour, bold=True)
    if hero["claim"]:
        draw_text(cv, nx + 6, y + 2, "\u2014 CLAIM", 1, RED, bold=True)
    # Headline, bold, up to 2 lines.
    lines = wrap_text(hero["headline"], 2, w - 32, bold=True)
    if len(lines) > 2:
        print("OVERFLOW hero %d headline: %d lines" % (hero["num"], len(lines)),
              file=sys.stderr)
    hy = y + 16
    for i, line in enumerate(lines[:2]):
        draw_text(cv, tx, hy + i * line_height(2), line, 2, INK, bold=True)
    # Summary, up to 4 lines.
    sy = hy + 2 * line_height(2) + 2
    lines = wrap_text(hero["summary"], 1, w - 32)
    if len(lines) > 4:
        print("OVERFLOW hero %d summary: %d lines" % (hero["num"], len(lines)),
              file=sys.stderr)
    for i, line in enumerate(lines[:4]):
        draw_text(cv, tx, sy + i * 10, line, 1, INK)


def draw_small(cv, x, y, w, small):
    region, topic, claim, headline, summary = small
    colour = REGION_COLOURS[region]
    tag = region.upper() + " \u00b7 " + topic
    nx = draw_text(cv, x, y, tag, 1, colour, bold=True)
    if claim:
        draw_text(cv, nx + 6, y, "CLAIM", 1, RED, bold=True)
    cy = y + 12
    lines = wrap_text(headline, 1, w, bold=True)
    if len(lines) > 3:
        print("OVERFLOW small headline: %d lines: %s"
              % (len(lines), headline), file=sys.stderr)
    for i, line in enumerate(lines[:3]):
        draw_text(cv, x, cy + i * 10, line, 1, INK, bold=True)
    cy += len(lines[:3]) * 10 + 2
    lines = wrap_text(summary, 1, w)
    if len(lines) > 7:
        print("OVERFLOW small summary: %d lines: %s"
              % (len(lines), headline), file=sys.stderr)
    for i, line in enumerate(lines[:7]):
        draw_text(cv, x, cy + i * 9, line, 1, INK)


def draw_timeline_entry(cv, x, y, col_w, time, text):
    prefix = time + " \u2014 "
    indent = text_width(prefix, 1, bold=True)
    draw_text(cv, x, y, time, 1, RED, bold=True)
    draw_text(cv, x + text_width(time, 1, bold=True), y, " \u2014 ", 1, INK)
    lines = wrap_text(text, 1, col_w - indent)
    if len(lines) > 2:
        print("OVERFLOW timeline: %d lines: %s" % (len(lines), text),
              file=sys.stderr)
    for i, line in enumerate(lines[:2]):
        draw_text(cv, x + indent, y + i * 11, line, 1, INK)


def draw_map(cv, x, y, cell):
    for r, row in enumerate(MAP_ROWS):
        row = (row + "." * 56)[:56]
        for c, ch in enumerate(row):
            if ch == "#":
                cv.fill_rect(x + c * cell, y + r * cell, cell, cell, LAND)
    # Hero dots, numbered, in region colours.
    for hero, (gc, gr) in zip(HEROES, HERO_DOTS):
        colour = REGION_COLOURS[hero["region"]]
        cx = x + gc * cell + cell // 2
        cy = y + gr * cell + cell // 2
        cv.fill_circle(cx, cy, 8, colour)
        cv.circle_outline(cx, cy, 8, WHITE, 1)
        draw_text_centred(cv, cx, cy - 5, str(hero["num"]), 1, WHITE,
                          bold=True)


def draw_page():
    cv = Canvas(W, H, PAPER)
    cv.rect_outline(10, 10, W - 20, H - 20, INK, 2)

    # --- kicker ---
    draw_text(cv, MX, 16, "ONE DAY OF WORLD NEWS, ONE PICTURE", 1.5, INK,
              bold=True)
    right = "50 STORIES \u00b7 7 REGIONS"
    draw_text(cv, RIGHT - text_width(right, 1.5, bold=True), 16, right, 1.5,
              INK, bold=True)
    cv.hline(MX, 34, CW, INK, 2)

    # --- masthead ---
    draw_text_centred(cv, W // 2, 40, "TUESDAY, 24 NOVEMBER 2026", 5, INK,
                      bold=True)
    cv.hline(MX, 90, CW, INK, 2)
    cv.hline(MX, 94, CW, INK, 1)

    # --- UTC timeline ---
    cv.fill_rect(MX, 103, 10, 10, RED)
    draw_text(cv, MX + 14, 100, "THE DAY IN UTC", 2, INK, bold=True)
    col_w = 320
    for i, (time, text) in enumerate(TIMELINE):
        col = i % 3
        row = i // 3
        draw_timeline_entry(cv, MX + col * 328, 122 + row * 22, col_w,
                            time, text)
    cv.hline(MX, 172, CW, INK, 1)

    # --- heroes: 2 x 2 ---
    hero_w, hero_h = 486, 110
    for i, hero in enumerate(HEROES):
        hx = MX + (i % 2) * (hero_w + 12)
        hy = 178 + (i // 2) * (hero_h + 8)
        draw_hero(cv, hx, hy, hero_w, hero)
    cv.vline(512, 178, 2 * hero_h + 8, LIGHT_RULE, 1)
    cv.hline(MX, 292, CW, LIGHT_RULE, 1)
    cv.hline(MX, 412, CW, INK, 1)

    # --- smalls: 2 rows x 6 ---
    small_w = 157
    for i, small in enumerate(SMALLS):
        col = i % 6
        row = i // 6
        sx = MX + col * (small_w + 8)
        sy = 418 + row * 114
        draw_small(cv, sx, sy, small_w, small)
    for col in range(1, 6):
        vx = MX + col * (small_w + 8) - 4
        cv.vline(vx, 418, 2 * 106 + 8, LIGHT_RULE, 1)
    cv.hline(MX, 528, CW, LIGHT_RULE, 1)
    cv.hline(MX, 644, CW, INK, 1)

    # --- bottom band: map + one-liners ---
    draw_text(cv, MX, 650, "WHERE IT HAPPENED", 2, INK, bold=True)
    map_x = MX + 4
    draw_map(cv, map_x, 672, 4)
    legend_y = 792
    for i, region in enumerate(["Europe", "Middle East", "Asia",
                                "Americas", "Africa", "Oceania", "Global"]):
        ly = legend_y + i * 11
        cv.fill_rect(MX + 4, ly + 1, 8, 8, REGION_COLOURS[region])
        draw_text(cv, MX + 16, ly, region, 1, INK)
    draw_text(cv, MX + 4, 876, "1-4 = the four hero stories", 1, INK)

    ox = 264
    draw_text(cv, ox, 650, "ALSO ON TUESDAY 24 NOVEMBER", 2, INK, bold=True)
    col_w = 240
    groups = [ONE_LINERS[0:12], ONE_LINERS[12:23], ONE_LINERS[23:34]]
    for gi, group in enumerate(groups):
        cx = ox + gi * (col_w + 10)
        cy = 672
        for item in group:
            lines = wrap_text(item, 1, col_w)
            if len(lines) > 3:
                print("OVERFLOW one-liner: %d lines: %s"
                      % (len(lines), item), file=sys.stderr)
            for i, line in enumerate(lines):
                draw_text(cv, cx, cy + i * 9, line, 1, INK)
            cy += len(lines) * 9 + 1
        if cy > 952:
            print("OVERFLOW one-liner column %d ends at y=%d" % (gi, cy),
                  file=sys.stderr)

    # --- red DATE CHECK banner ---
    cv.fill_rect(MX, 954, CW, 24, RED)
    banner = ("DATE CHECK \u2014 Every story here happened or was first "
              "reported on Tuesday, 24 November 2026.")
    draw_text_centred(cv, W // 2, 958, banner, 1.5, WHITE, bold=True)

    # --- footer ---
    draw_text_centred(
        cv, W // 2, 984,
        "Every story here happened or was first reported on 24 November "
        "2026. CLAIM = one side's account, not independently confirmed.",
        1, INK)
    draw_text_centred(
        cv, W // 2, 995,
        "Sources: Reuters, Bloomberg, Al Jazeera, AP, BBC, Xinhua, "
        "The Hindu, SCMP and others.",
        1, INK)
    return cv


def output_path():
    outdir = os.environ.get("MAKEFUN_OUTPUT_DIR") or "/output"
    try:
        os.makedirs(outdir, exist_ok=True)
        probe = os.path.join(outdir, ".write-test")
        with open(probe, "wb") as f:
            f.write(b"")
        os.remove(probe)
        return os.path.join(outdir, "entry.png")
    except OSError:
        return os.path.join(os.getcwd(), "entry.png")


def glyph_test(path):
    """Large-scale check that lowercase 'g' cannot be read as '9'."""
    cv = Canvas(900, 330, PAPER)
    draw_text(cv, 20, 20, "g 9", 8, INK, bold=True)
    draw_text(cv, 20, 110, "grounds", 4, INK, bold=True)
    draw_text(cv, 20, 170, "Johannesburg", 4, INK, bold=True)
    draw_text(cv, 20, 230, "43.9bn", 4, INK, bold=True)
    draw_text(cv, 20, 290, "g9 g9 g9  --  9g 9g 9g", 2, INK)
    write_png(path, cv)


def main():
    assert len(HEROES) == 4, len(HEROES)
    assert len(SMALLS) == 12, len(SMALLS)
    assert len(ONE_LINERS) == 34, len(ONE_LINERS)
    assert len(TIMELINE) == 6, len(TIMELINE)
    if "--glyph-test" in sys.argv:
        path = sys.argv[sys.argv.index("--glyph-test") + 1]
        glyph_test(path)
        print("wrote %s" % path)
        return
    cv = draw_page()
    path = output_path()
    write_png(path, cv)
    print("wrote %s (%d bytes)" % (path, os.path.getsize(path)))


if __name__ == "__main__":
    main()
