"""Extrai e guarda cores dominantes de escudos PNG para a interface."""
from __future__ import annotations

from collections import Counter
from struct import unpack
from time import sleep
from urllib.request import Request, urlopen
import zlib


def _paeth(left: int, up: int, upper_left: int) -> int:
    estimate = left + up - upper_left
    choices = (left, up, upper_left)
    distances = (abs(estimate - left), abs(estimate - up), abs(estimate - upper_left))
    return choices[distances.index(min(distances))]


def _png_pixels(raw: bytes):
    if not raw.startswith(b"\x89PNG\r\n\x1a\n"):
        return
    offset = 8
    width = height = bit_depth = color_type = 0
    compressed = bytearray()
    while offset + 12 <= len(raw):
        length = unpack(">I", raw[offset:offset + 4])[0]
        kind, payload = raw[offset + 4:offset + 8], raw[offset + 8:offset + 8 + length]
        offset += length + 12
        if kind == b"IHDR":
            width, height, bit_depth, color_type = unpack(">IIBB", payload[:10])
        elif kind == b"IDAT":
            compressed.extend(payload)
        elif kind == b"IEND":
            break
    if bit_depth != 8 or color_type not in (2, 6) or not width or not compressed:
        return
    channels = 4 if color_type == 6 else 3
    try:
        decoded = zlib.decompress(compressed)
    except zlib.error:
        return
    stride, cursor, previous = width * channels, 0, bytearray(width * channels)
    for _ in range(height):
        if cursor + stride >= len(decoded):
            return
        filter_type, row = decoded[cursor], bytearray(decoded[cursor + 1:cursor + 1 + stride])
        cursor += stride + 1
        for index, value in enumerate(row):
            left = row[index - channels] if index >= channels else 0
            up = previous[index]
            upper_left = previous[index - channels] if index >= channels else 0
            if filter_type == 1:
                row[index] = (value + left) & 255
            elif filter_type == 2:
                row[index] = (value + up) & 255
            elif filter_type == 3:
                row[index] = (value + ((left + up) >> 1)) & 255
            elif filter_type == 4:
                row[index] = (value + _paeth(left, up, upper_left)) & 255
            elif filter_type != 0:
                return
        for index in range(0, len(row), channels * 2):
            red, green, blue = row[index:index + 3]
            alpha = row[index + 3] if channels == 4 else 255
            if alpha >= 180 and max(red, green, blue) - min(red, green, blue) >= 18 and min(red, green, blue) <= 235:
                yield red, green, blue
        previous = row


def primary_color(url: str) -> str | None:
    if not url or not url.startswith("https://"):
        return None
    try:
        with urlopen(Request(url, headers={"User-Agent": "FUTRanking/1.0", "Referer": ""}), timeout=12) as response:
            raw = response.read(1_500_000)
    except OSError:
        return None
    bins: Counter[tuple[int, int, int]] = Counter()
    for red, green, blue in _png_pixels(raw) or ():
        bins[(red // 32 * 32 + 16, green // 32 * 32 + 16, blue // 32 * 32 + 16)] += 1
    if not bins:
        return None
    red, green, blue = bins.most_common(1)[0][0]
    return f"#{red:02x}{green:02x}{blue:02x}"


def backfill_fixture_colors(database, limit: int = 80) -> int:
    rows = database.execute(
        """SELECT DISTINCT c.id, c.crest_url FROM clubs c
           JOIN (SELECT home_club_id AS club_id FROM fixtures UNION SELECT away_club_id FROM fixtures) f
             ON f.club_id = c.id
           WHERE c.primary_color IS NULL AND c.crest_url IS NOT NULL LIMIT ?""",
        (limit,),
    ).fetchall()
    updated = 0
    for row in rows:
        if color := primary_color(str(row["crest_url"])):
            database.execute("UPDATE clubs SET primary_color=? WHERE id=?", (color, row["id"]))
            updated += 1
        sleep(0.08)
    return updated
