#!/usr/bin/env python3
"""news-image-20261126 entrypoint (Python 3.13, standard library only).

Copies the entry image (entry.png, stored next to this file) into the
output directory -- default /output, overridable with $MAKEFUN_OUTPUT_DIR --
after validating the competition gate: the file must be a PNG or a JPEG,
at most 1 MiB (1048576 bytes) and at most 1024 by 1024 pixels. The image
itself is produced by the deterministic PIL render script in the workspace
and committed alongside this program; this entrypoint does not draw, fetch,
or modify it, so both runs write identical bytes. Outputs are left
world-readable (mode 0644) so the grader can collect them.
"""

import os
import shutil
import struct
import sys
from pathlib import Path

MAX_BYTES = 1_048_576
MAX_DIMENSION = 1024

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def png_dimensions(data: bytes) -> tuple[int, int]:
    """Return (width, height) from a PNG's IHDR chunk."""
    if len(data) < 24 or data[:8] != PNG_SIGNATURE:
        raise ValueError("not a PNG file")
    width, height = struct.unpack(">II", data[16:24])
    return width, height


def jpeg_dimensions(data: bytes) -> tuple[int, int]:
    """Return (width, height) from a JPEG's first SOF marker."""
    if len(data) < 2 or data[:2] != b"\xff\xd8":
        raise ValueError("not a JPEG file")
    pos = 2
    while pos + 9 < len(data):
        if data[pos] != 0xFF:
            raise ValueError("malformed JPEG marker")
        marker = data[pos + 1]
        if marker in (0xD8, 0xD9) or 0xD0 <= marker <= 0xD7:
            pos += 2
            continue
        length = struct.unpack(">H", data[pos + 2:pos + 4])[0]
        if 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):
            height, width = struct.unpack(">HH", data[pos + 5:pos + 9])
            return width, height
        pos += 2 + length
    raise ValueError("no JPEG SOF marker found")


def image_dimensions(data: bytes) -> tuple[str, int, int]:
    """Detect the format and return (format, width, height)."""
    if data[:8] == PNG_SIGNATURE:
        width, height = png_dimensions(data)
        return "PNG", width, height
    if data[:2] == b"\xff\xd8":
        width, height = jpeg_dimensions(data)
        return "JPEG", width, height
    raise ValueError("entry image must be a PNG or a JPEG")


def main() -> int:
    here = Path(__file__).resolve().parent
    source = here / "entry.png"
    output_dir = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))
    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / "entry.png"

    data = source.read_bytes()
    if len(data) > MAX_BYTES:
        print(f"entry image is {len(data)} bytes, over the 1 MiB limit",
              file=sys.stderr)
        return 1
    fmt, width, height = image_dimensions(data)
    if width > MAX_DIMENSION or height > MAX_DIMENSION:
        print(f"entry image is {width}x{height}, over the 1024x1024 limit",
              file=sys.stderr)
        return 1

    shutil.copyfile(source, output)
    os.chmod(output, 0o644)
    if output.stat().st_size != len(data):
        print("output copy is incomplete", file=sys.stderr)
        return 1
    print(f"wrote {output} ({fmt} {width}x{height}, {len(data)} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
