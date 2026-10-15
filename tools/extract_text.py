from __future__ import annotations

import csv
import json
import re
import struct
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROM = ROOT / "Gegege no Kitarou - Kikiippatsu! Youkai Rettou (Japan).gba"
OUT = ROOT / "work" / "source"


def japanese_count(text: str) -> int:
    return sum(
        "ぁ" <= ch <= "ヿ"
        or "一" <= ch <= "龯"
        or ch in "々〆ヶ"
        for ch in text
    )


def main() -> None:
    data = ROM.read_bytes()
    pointers: dict[int, list[int]] = defaultdict(list)
    for location in range(0, len(data) - 3, 4):
        value = struct.unpack_from("<I", data, location)[0]
        if 0x08000000 <= value < 0x08000000 + len(data):
            pointers[value - 0x08000000].append(location)

    records: list[dict[str, object]] = []
    for match in re.finditer(rb"[^\x00]{2,}", data):
        raw = match.group()
        try:
            text = raw.decode("cp932")
        except UnicodeDecodeError:
            continue
        if not all(ch.isprintable() or ch in "\r\n\t" for ch in text):
            continue
        count = japanese_count(text)
        if count < 1:
            continue
        offset = match.start()
        records.append(
            {
                "offset": offset,
                "offset_hex": f"0x{offset:06X}",
                "byte_length": len(raw),
                "jp_count": count,
                "refs": pointers.get(offset, []),
                "text": text,
                "translation": "",
            }
        )

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "strings.json").write_text(
        json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    with (OUT / "strings.tsv").open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f, delimiter="\t", lineterminator="\n")
        writer.writerow(["offset", "bytes", "refs", "japanese", "korean"])
        for row in records:
            writer.writerow(
                [
                    row["offset_hex"],
                    row["byte_length"],
                    ",".join(f"0x{x:06X}" for x in row["refs"]),
                    row["text"],
                    "",
                ]
            )

    by_region: Counter[int] = Counter(row["offset"] >> 16 for row in records)
    referenced = sum(bool(row["refs"]) for row in records)
    print(f"ROM bytes: {len(data):,}")
    print(f"Decoded Japanese strings: {len(records):,}")
    print(f"Strings with aligned ROM pointers: {referenced:,}")
    print(f"Japanese codepoints: {sum(row['jp_count'] for row in records):,}")
    for region, count in sorted(by_region.items()):
        if count:
            print(f"{region:02X}xxxx: {count:4} strings")
    print(f"Wrote {OUT / 'strings.tsv'}")


if __name__ == "__main__":
    main()
