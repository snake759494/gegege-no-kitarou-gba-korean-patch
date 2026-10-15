#!/usr/bin/env python3
"""Build the Korean patch for Gegege no Kitarou (GBA).

The game's original text pointers are absolute GBA ROM pointers. Translated
strings are appended to the expanded ROM and each verified pointer entry is
redirected to its replacement. A sorted CP932-to-glyph table is rebuilt in
the expanded ROM with Galmuri11 glyphs in the game's native 16x14 source cell.
"""

from __future__ import annotations

import csv
import hashlib
import json
import struct
import textwrap
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
ROM_NAME = "Gegege no Kitarou - Kikiippatsu! Youkai Rettou (Japan).gba"
OUTPUT_NAME = "Gegege no Kitarou - Kikiippatsu! Youkai Rettou (Korean).gba"
SOURCE_SHA256 = "7c6c4806b637e6326cfc7e242a38fc3d3dcc53abaab9be96b8388f04bf1976cc"
SOURCE_SIZE = 0x1000000

TEXT_TABLE_OFF = 0x355DE8
FONT_DATA_OFF = 0x358020
FONT_COUNT = 0x111B
GLYPH_BYTES = 56

TABLE_LITERAL_OFFSETS = (0x3DE8, 0x3E04, 0x3E8C, 0x3FC0, 0x3FD4, 0x4064)
FONT_LITERAL_OFFSETS = (0x3DEC, 0x4068)
COUNT_LITERAL_OFFSETS = (0x3DE4, 0x3FBC)


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def align(value: int, alignment: int) -> int:
    return (value + alignment - 1) & ~(alignment - 1)


def parse_bdf(path: Path) -> dict[int, dict[str, object]]:
    glyphs: dict[int, dict[str, object]] = {}
    current: dict[str, object] | None = None
    bitmap_mode = False

    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("STARTCHAR "):
            current = {"name": line[10:], "bitmap": []}
            bitmap_mode = False
        elif current is not None and line.startswith("ENCODING "):
            fields = line.split()
            try:
                current["encoding"] = int(fields[1])
            except (IndexError, ValueError):
                current["encoding"] = -1
        elif current is not None and line.startswith("DWIDTH "):
            current["dwidth"] = tuple(map(int, line.split()[1:3]))
        elif current is not None and line.startswith("BBX "):
            current["bbx"] = tuple(map(int, line.split()[1:5]))
        elif current is not None and line == "BITMAP":
            bitmap_mode = True
        elif current is not None and line == "ENDCHAR":
            cp = int(current.get("encoding", -1))
            if cp >= 0:
                glyphs[cp] = current
            current = None
            bitmap_mode = False
        elif current is not None and bitmap_mode:
            current["bitmap"].append(int(line, 16))

    return glyphs


def bdf_to_game_glyph(glyph: dict[str, object]) -> tuple[bytes, int]:
    """Native 16x14, MSB first 2bpp; renderer reads both 8-pixel halves."""
    width, height, xoff, yoff = glyph["bbx"]
    if width > 16 or height > 14:
        raise ValueError(f"Glyph exceeds 16x14: {glyph.get('name')} {glyph['bbx']}")
    pixels = [[0] * 16 for _ in range(14)]
    left = min(max(xoff, 0), 16-width)
    top = min(max(14-height-yoff, 0), 14-height)
    for sy, row in enumerate(glyph["bitmap"]):
        for sx in range(width):
            if row >> (((width+7)//8)*8-1-sx) & 1:
                pixels[top+sy][left+sx] = 3
    return b"".join(sum(p << (30-2*x) for x,p in enumerate(row)).to_bytes(4,"little") for row in pixels), 0


def glyph_for_cp932(code: int, bdf: dict[int, dict[str, object]]) -> bytes | None:
    try:
        char = bytes((code >> 8, code & 0xFF)).decode("cp932")
    except UnicodeDecodeError:
        return None
    if len(char) != 1:
        return None
    glyph = bdf.get(ord(char))
    return bdf_to_game_glyph(glyph)[0] if glyph else None


def wrap_translation(text: str, line_count: int, width: int = 9) -> list[str]:
    # Preserve Korean words. Extra original rows stay blank instead of splitting
    # words merely to fill the original Japanese row count.
    lines = []
    current = ""
    pixels = lambda value: sum(6 if ch == " " else 12 for ch in value)
    for word in text.split():
        if pixels(word) > width * 12:
            raise ValueError(f"Word exceeds paragraph width: {word}")
        candidate = (current + " " + word).strip()
        if current and pixels(candidate) > width * 12:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    if len(lines) > line_count:
        raise ValueError(f"Translation exceeds available rows: {text}")
    return lines + [""] * (line_count - len(lines))



def load_translations(source_rom: bytes) -> tuple[dict[int, str], dict[str, str], dict[str, int]]:
    rows = [r for r in read_tsv(ROOT / "translation" / "ko_strings.tsv") if r["pointer_refs"]]
    groups = json.loads((ROOT / "work" / "source" / "paragraph_groups.json").read_text(encoding="utf-8"))
    paragraph_rows = read_tsv(ROOT / "translation" / "ko_paragraphs.tsv")
    paragraphs = {r["start_ref"].upper(): r["korean"] for r in paragraph_rows}
    names = {r["japanese"]: r["korean"] for r in read_tsv(ROOT / "translation" / "ko_names.tsv")}

    direct: dict[str, str] = {}
    for filename in ("ko_items.tsv", "ko_dialogue.tsv", "ko_misc.tsv"):
        for r in read_tsv(ROOT / "translation" / filename):
            if not r["korean"]:
                raise ValueError(f"Blank translation in {filename}: {r}")
            if r["offset"].upper() in direct:
                raise ValueError(f"Duplicate direct translation offset: {r['offset']}")
            direct[r["offset"].upper()] = r["korean"]

    translated_by_ref: dict[int, str] = {}
    paragraph_fallback_by_offset: dict[str, str] = {}
    paragraph_refs: set[int] = set()
    paragraph_offsets: set[str] = set()
    for group in groups:
        start_ref = group["start_ref"].upper()
        if start_ref not in paragraphs:
            raise ValueError(f"Missing paragraph translation: {start_ref}")
        korean = paragraphs[start_ref]
        if "|" in korean:
            lines = [part.strip() for part in korean.split("|")]
            if len(lines) != len(group["entries"]):
                raise ValueError(f"Wrong explicit line count for {start_ref}: {len(lines)}")
        else:
            lines = wrap_translation(korean, len(group["entries"]))

        for entry, line in zip(group["entries"], lines):
            ref = int(entry["ref"], 16)
            off = int(entry["offset"], 16)
            actual = struct.unpack_from("<I", source_rom, ref)[0]
            expected = 0x08000000 + off
            if actual != expected:
                raise ValueError(f"Pointer mismatch at {ref:#x}: got {actual:#x}, expected {expected:#x}")
            translated_by_ref[ref] = line
            paragraph_fallback_by_offset.setdefault(entry["offset"].upper(), line)
            paragraph_refs.add(ref)
            paragraph_offsets.add(entry["offset"].upper())

    direct_used: set[str] = set()
    refs_seen: set[int] = set()
    for r in rows:
        off_text = r["offset"].upper()
        off = int(off_text, 16)
        source = r["japanese"]
        if off_text in paragraph_offsets:
            base_translation = paragraph_fallback_by_offset[off_text]
        elif 0x39000 <= off < 0x397B8:
            base_translation = names.get(source)
            if base_translation is None:
                raise ValueError(f"Missing name translation: {off_text} {source}")
        else:
            base_translation = direct.get(off_text)
            if base_translation is None:
                raise ValueError(f"Missing direct translation: {off_text} {source}")
            direct_used.add(off_text)

        expected = 0x08000000 + off
        for ref_text in r["pointer_refs"].split(","):
            ref = int(ref_text, 16)
            actual = struct.unpack_from("<I", source_rom, ref)[0]
            if actual != expected:
                raise ValueError(f"Pointer mismatch at {ref:#x}: got {actual:#x}, expected {expected:#x}")
            if ref not in translated_by_ref:
                translated_by_ref[ref] = base_translation
            refs_seen.add(ref)

    if direct_used != set(direct):
        raise ValueError(f"Unused direct translations: {sorted(set(direct) - direct_used)}")
    if len(refs_seen) != 1218:
        raise ValueError(f"Unexpected pointer reference count: {len(refs_seen)}")
    if len(translated_by_ref) != len(refs_seen):
        raise ValueError("Translation was not assigned to each distinct pointer reference")

    # Item descriptions reserve 48 tiles per row, i.e. 16 original 12px
    # characters. Space packing does not reduce the original DMA allocation.
    # Override by reference, including formerly empty second-row pointers.
    item_rows = read_tsv(ROOT / 'translation' / 'ko_item_descriptions.tsv')
    assert len(item_rows) == 156
    for row in item_rows:
        ref = int(row['pointer_ref'], 16)
        off = int(row['source_offset'], 16)
        assert 0xBBB7C <= ref < 0xBBDEC and ref % 4 == 0
        assert struct.unpack_from('<I', source_rom, ref)[0] == 0x08000000 + off
        text = row['korean']
        assert len(text) <= 16, (hex(ref), text)
        assert '\u3000' not in text and '  ' not in text
        translated_by_ref[ref] = text

    stats = {
        'item_description_rows': len(item_rows),
        'item_row_max_characters_including_spaces': 16,
        "translated_rows": len(rows),
        "paragraph_groups": len(groups),
        "paragraph_entries": sum(len(g["entries"]) for g in groups),
        "pointer_references": len(refs_seen),
        "unique_pointer_replacements": len(translated_by_ref),
    }
    return translated_by_ref, names, stats


def encode_text(text: str, char_codes: dict[str, int]) -> bytes:
    out = bytearray()
    i = 0
    while i < len(text):
        if text.startswith("%s", i):
            out.extend(b"%s")
            i += 2
            continue
        ch = text[i]
        if ch == "\u3000":
            out.extend(b"\x81\x40")
            i += 1
            continue
        try:
            code = char_codes[ch]
        except KeyError as e:
            raise ValueError(f"No custom glyph code for U+{ord(ch):04X} {ch!r}") from e
        out.extend(struct.pack(">H", code))
        i += 1
    out.extend(b"\x00\x00")
    return bytes(out)


def update_header_checksum(rom: bytearray) -> int:
    checksum = (-sum(rom[0xA0:0xBD]) - 0x19) & 0xFF
    rom[0xBD] = checksum
    return checksum


def main() -> None:
    source_path = ROOT / ROM_NAME
    source = source_path.read_bytes()
    if len(source) != SOURCE_SIZE or sha256(source) != SOURCE_SHA256:
        raise SystemExit("Original ROM size or SHA-256 differs from the analyzed clean dump.")
    if source[0xA0:0xAC].decode("ascii", "replace").rstrip("\x00 ") != "KITARO":
        raise SystemExit("ROM header title mismatch.")

    translated_by_ref, _, stats = load_translations(source)
    from full_text import load_complete_text, patch_scripts
    script_mapping, extra_menu = load_complete_text()
    for row in extra_menu:
        for ref in row['refs']:
            if ref < 0x100000:
                translated_by_ref[ref] = row['korean']
    all_texts = list(translated_by_ref.values()) + list(script_mapping.values())
    custom_char_set: set[str] = set()
    for text in all_texts:
        i = 0
        while i < len(text):
            if text.startswith("%s", i):
                i += 2
            else:
                if text[i] != "\u3000":
                    custom_char_set.add(text[i])
                i += 1
    custom_chars = sorted(custom_char_set)
    if not custom_chars:
        raise SystemExit("No translated glyphs were found.")
    if 0xF040 + len(custom_chars) - 1 > 0xFFFF:
        raise SystemExit(f"Custom code range exhausted: {len(custom_chars)} characters")

    bdf_path = ROOT / "work" / "fonts" / "galmuri" / "Galmuri11.bdf"
    bdf = parse_bdf(bdf_path)
    missing = sorted(ch for ch in custom_chars if ord(ch) not in bdf)
    if missing:
        raise SystemExit("Galmuri11 is missing translated glyphs: " + "".join(missing))
    safe_codes = [(hi<<8)|lo for hi in range(0xF0,0xFD) for lo in list(range(0x40,0x7F))+list(range(0x80,0xFD)) if lo != 0x5C]
    assert len(custom_chars) <= len(safe_codes)
    char_codes = dict(zip(custom_chars, safe_codes))

    if TEXT_TABLE_OFF + FONT_COUNT * 2 > FONT_DATA_OFF:
        raise SystemExit("Original character table overlaps original glyph data.")
    original_codes = [struct.unpack_from("<H", source, TEXT_TABLE_OFF + i * 2)[0] for i in range(FONT_COUNT)]
    if original_codes != sorted(original_codes) or len(set(original_codes)) != FONT_COUNT:
        raise SystemExit("Original character table is not uniquely sorted.")
    if max(original_codes) >= 0xF040:
        raise SystemExit("Custom font code range overlaps the original table.")

    pairs: list[tuple[int, bytes]] = []
    font_clips = 0
    for i, code in enumerate(original_codes):
        start = FONT_DATA_OFF + i * GLYPH_BYTES
        old_bitmap = source[start:start + GLYPH_BYTES]
        new_bitmap = old_bitmap  # Preserve every original Japanese glyph.
        pairs.append((code, new_bitmap))

    for ch in custom_chars:
        bitmap, clipped = bdf_to_game_glyph(bdf[ord(ch)])
        font_clips += clipped
        pairs.append((char_codes[ch], bitmap))

    pairs.sort(key=lambda item: item[0])
    new_codes = [code for code, _ in pairs]
    if new_codes != sorted(set(new_codes)):
        raise SystemExit("Expanded character table is not uniquely sorted.")
    new_count = len(pairs)

    out = bytearray(source)
    table_offset = align(len(out), 4)
    if table_offset > len(out):
        out.extend(b"\xFF" * (table_offset - len(out)))
    new_table = b"".join(struct.pack("<H", code) for code, _ in pairs)
    out.extend(new_table)
    font_offset = align(len(out), 4)
    if font_offset > len(out):
        out.extend(b"\xFF" * (font_offset - len(out)))
    if font_offset != len(out):
        raise AssertionError("Font table alignment error")
    for _, bitmap in pairs:
        out.extend(bitmap)

    table_address = 0x08000000 + table_offset
    font_address = 0x08000000 + font_offset
    if table_address > 0x09FFFFFF or font_address + new_count * GLYPH_BYTES > 0x0A000000:
        raise SystemExit("Expanded font exceeds the GBA Game Pak ROM window.")

    for off in TABLE_LITERAL_OFFSETS:
        struct.pack_into("<I", out, off, table_address)
    for off in FONT_LITERAL_OFFSETS:
        struct.pack_into("<I", out, off, font_address)
    for off in COUNT_LITERAL_OFFSETS:
        struct.pack_into("<I", out, off, new_count)

    appended_strings: dict[int, dict[str, object]] = {}
    for ref, text in sorted(translated_by_ref.items()):
        data = encode_text(text, char_codes)
        string_offset = len(out)
        if string_offset + len(data) >= 0x02000000:
            raise SystemExit("Translated strings exceed the GBA ROM address window.")
        out.extend(data)
        appended_strings[ref] = {"offset": string_offset, "text": text, "bytes": len(data)}
        struct.pack_into("<I", out, ref, 0x08000000 + string_offset)

    script_stats = patch_scripts(source, out, script_mapping, char_codes, encode_text)

    from patch_title import make_title
    out, title_report = make_title(out)

    from patch_static_title import patch_static_title
    title_report["stationary_title"] = patch_static_title(source, out)

    from patch_menu_graphics import patch_menu_graphics
    menu_graphics = patch_menu_graphics(source, out)

    from patch_ui_graphics import patch_ui
    ui_report = patch_ui(source, out)

    from patch_chapters import patch_chapters
    chapter_report = patch_chapters(source, out)

    from patch_remaining_graphics import patch_remaining
    remaining_graphics = patch_remaining(source, out)

    from patch_menu_animation import patch_menu_animation
    animation_report = patch_menu_animation(source, out)
    from patch_halfspace import patch_halfspace
    halfspace_report = patch_halfspace(source, out, char_codes)

    from patch_gameover import patch_gameover
    gameover_report = patch_gameover(source, out)

    checksum = update_header_checksum(out)
    if len(out) > 0x02000000:
        raise SystemExit("Built ROM exceeds the 32 MiB GBA cartridge window.")

    output_path = ROOT / OUTPUT_NAME
    output_path.write_bytes(out)
    final_hash = sha256(out)

    # Read-back checks bind every pointer to its appended, terminated translation.
    for ref, item in appended_strings.items():
        target = struct.unpack_from("<I", out, ref)[0] - 0x08000000
        if target != item["offset"]:
            raise SystemExit(f"Pointer read-back mismatch at {ref:#x}")
        expected = encode_text(item["text"], char_codes)
        if out[target:target + len(expected)] != expected:
            raise SystemExit(f"String read-back mismatch at {ref:#x}")
    if struct.unpack_from("<I", out, COUNT_LITERAL_OFFSETS[0])[0] != new_count:
        raise SystemExit("Font count literal read-back mismatch")
    if struct.unpack_from("<I", out, TABLE_LITERAL_OFFSETS[0])[0] != table_address:
        raise SystemExit("Font table address read-back mismatch")
    if out[0xBD] != checksum:
        raise SystemExit("GBA header checksum read-back mismatch")

    report = {
        "game": "Gegege no Kitarou - Kikiippatsu! Youkai Rettou (Japan)",
        "source": {
            "file": ROM_NAME,
            "size": len(source),
            "sha256": SOURCE_SHA256,
            "crc32": "7F2B2657",
        },
        "output": {
            "file": OUTPUT_NAME,
            "size": len(out),
            "sha256": final_hash,
            "header_complement_checksum": f"{checksum:02X}",
        },
        "translation": stats,
        "title_graphics": title_report,
        "menu_graphics": menu_graphics,
        "scene_scripts": script_stats,
        "supplemental_menu_strings": len(extra_menu),
        "remaining_graphics": remaining_graphics,
        "chapter_graphics": chapter_report,
        "ui_graphics": ui_report,
        "halfwidth_space": halfspace_report,
        "menu_animation": animation_report,
        "gameover_graphics": gameover_report,
        "font": {
            "face": "Galmuri11",
            "license": "SIL Open Font License 1.1",
            "native_cell": "16x14 source cell; both 8-pixel halves rendered; Galmuri11 retained without scaling or clipping",
            "original_glyphs": FONT_COUNT,
            "custom_translation_glyphs": len(custom_chars),
            "expanded_glyph_count": new_count,
            "table_rom_offset": f"0x{table_offset:X}",
            "bitmap_rom_offset": f"0x{font_offset:X}",
            "clipped_source_pixels": font_clips,
        },
        "strings": {
            "appended_data_bytes": len(out) - min(v["offset"] for v in appended_strings.values()),
            "format_placeholders_preserved": sum(text.count("%s") for text in all_texts),
        },
    }
    (ROOT / "work" / "build").mkdir(parents=True, exist_ok=True)
    (ROOT / "work" / "build" / "build_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (ROOT / "work" / "build" / "custom_glyph_map.tsv").write_text(
        "character\tcode\tunicode\n" + "".join(
            f"{ch}\t0x{char_codes[ch]:04X}\tU+{ord(ch):04X}\n" for ch in custom_chars
        ),
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
