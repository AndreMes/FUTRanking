"""Extrai e guarda a cor dominante de escudos PNG para a interface."""
from __future__ import annotations

from collections import Counter
from functools import lru_cache
from io import BytesIO
from struct import unpack
from time import sleep
from urllib.request import Request, urlopen
import zlib


def _paeth(left: int, up: int, upper_left: int) -> int:
    estimate = left + up - upper_left
    distances = abs(estimate - left), abs(estimate - up), abs(estimate - upper_left)
    return (left, up, upper_left)[distances.index(min(distances))]


def _png_pixels(raw: bytes):
    if not raw.startswith(b"\x89PNG\r\n\x1a\n"):
        return
    offset, width, height, bit_depth, color_type = 8, 0, 0, 0, 0
    data = bytearray()
    while offset + 8 <= len(raw):
        length = unpack(">I", raw[offset:offset + 4])[0]
        kind, payload = raw[offset + 4:offset + 8], raw[offset + 8:offset + 8 + length]
        offset += 12 + length
        if kind == b"IHDR":
            width, height, bit_depth, color_type = unpack(">IIBB", payload[:10])
        elif kind == b"IDAT":
            data.extend(payload)
        elif kind == b"IEND":
            break
    if bit_depth != 8 or color_type not in (2, 6) or not width or not data:
        return
    channels = 4 if color_type == 6 else 3
    try:
        decoded = zlib.decompress(data)
    except zlib.error:
        return
    stride, cursor, previous = width * channels, 0, bytearray(width * channels)
    for _ in range(height):
        if cursor >= len(decoded):
            return
        filter_type, row = decoded[cursor], bytearray(decoded[cursor + 1:cursor + 1 + stride])
        cursor += stride + 1
        if len(row) != stride:
            return
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
            # Fundo transparente/branco/cinza não deve determinar o escudo.
            if alpha < 180 or max(red, green, blue) - min(red, green, blue) < 18 or min(red, green, blue) > 235:
                continue
            yield red, green, blue
        previous = row


@lru_cache(maxsize=512)
def _download_crest(url: str) -> bytes | None:
    if not url or not url.startswith("https://"):
        return None
    try:
        request = Request(url, headers={"User-Agent": "FUTRanking/1.0", "Referer": ""})
        with urlopen(request, timeout=12) as response:
            return response.read(1_500_000)
    except OSError:
        return None


def _png_fingerprint(raw: bytes, size: int = 8) -> int | None:
    """Assinatura visual compacta, independente de URL e tamanho do PNG."""
    if not raw.startswith(b"\x89PNG\r\n\x1a\n"):
        return None
    offset, width, height, bit_depth, color_type = 8, 0, 0, 0, 0
    data = bytearray()
    while offset + 8 <= len(raw):
        length = unpack(">I", raw[offset:offset + 4])[0]
        kind, payload = raw[offset + 4:offset + 8], raw[offset + 8:offset + 8 + length]
        offset += 12 + length
        if kind == b"IHDR":
            width, height, bit_depth, color_type = unpack(">IIBB", payload[:10])
        elif kind == b"IDAT":
            data.extend(payload)
        elif kind == b"IEND":
            break
    if bit_depth != 8 or color_type not in (2, 6) or not width or not height:
        return None
    channels = 4 if color_type == 6 else 3
    try:
        decoded = zlib.decompress(data)
    except zlib.error:
        return None
    target_x = [min(width - 1, int((index + .5) * width / size)) for index in range(size)]
    target_y = {min(height - 1, int((index + .5) * height / size)): index for index in range(size)}
    values: list[int | None] = [None] * (size * size)
    stride, cursor, previous = width * channels, 0, bytearray(width * channels)
    for y in range(height):
        if cursor >= len(decoded):
            return None
        filter_type, row = decoded[cursor], bytearray(decoded[cursor + 1:cursor + 1 + stride])
        cursor += stride + 1
        if len(row) != stride:
            return None
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
                return None
        if y in target_y:
            for x_index, x in enumerate(target_x):
                red, green, blue = row[x * channels:x * channels + 3]
                alpha = row[x * channels + 3] if channels == 4 else 255
                values[target_y[y] * size + x_index] = 255 if alpha < 100 else (red * 299 + green * 587 + blue * 114) // 1000
        previous = row
    luminance = [value if value is not None else 255 for value in values]
    average = sum(luminance) / len(luminance)
    fingerprint = 0
    for value in luminance:
        fingerprint = (fingerprint << 1) | int(value < average)
    return fingerprint


def crest_similarity(first_url: str | None, second_url: str | None) -> float | None:
    """Compara forma/luminosidade de escudos PNG; 1,0 significa idênticos."""
    first = _png_fingerprint(_download_crest(first_url or "") or b"")
    second = _png_fingerprint(_download_crest(second_url or "") or b"")
    if first is None or second is None:
        return None
    return 1.0 - ((first ^ second).bit_count() / 64)


def primary_color(url: str) -> str | None:
    """Retorna a cor predominante quantizada; falhas deixam o fallback visual."""
    raw = _download_crest(url)
    if raw is None:
        return None
    bins: Counter[tuple[int, int, int]] = Counter()
    for red, green, blue in _png_pixels(raw) or ():
        bins[(red // 32 * 32 + 16, green // 32 * 32 + 16, blue // 32 * 32 + 16)] += 1
    if not bins:
        return None
    red, green, blue = bins.most_common(1)[0][0]
    return f"#{red:02x}{green:02x}{blue:02x}"


def backfill_fixture_colors(database, limit: int = 80) -> int:
    """Busca uma vez as cores ausentes dos clubes presentes na agenda atual."""
    rows = database.execute(
        """SELECT DISTINCT c.id, c.crest_url FROM clubs c
           JOIN (SELECT home_club_id AS club_id FROM fixtures UNION SELECT away_club_id FROM fixtures) f
             ON f.club_id = c.id
           WHERE c.primary_color IS NULL AND c.crest_url IS NOT NULL
           LIMIT ?""",
        (limit,),
    ).fetchall()
    updated = 0
    for row in rows:
        color = primary_color(str(row["crest_url"]))
        if color:
            database.execute("UPDATE clubs SET primary_color=? WHERE id=?", (color, row["id"]))
            updated += 1
        sleep(0.08)
    return updated

