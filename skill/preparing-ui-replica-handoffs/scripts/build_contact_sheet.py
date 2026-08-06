from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path, PurePosixPath
import re

from PIL import Image, ImageDraw, ImageFont


MANIFEST_PATH = PurePosixPath("contracts/asset-manifest.json")
URI_SCHEME_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")
WINDOWS_ABSOLUTE_PATTERN = re.compile(r"^[A-Za-z]:[\\/]|^\\\\")
TILE_WIDTH = 320
TILE_HEIGHT = 250
IMAGE_WIDTH = 288
IMAGE_HEIGHT = 190
PADDING = 16
MAX_COLUMNS = 4


def _reject_nonfinite_json_constant(value: str) -> object:
    raise ValueError(f"non-finite JSON number is forbidden: {value}")


def _package_path(root: Path, relative_path: str) -> Path:
    if (
        not isinstance(relative_path, str)
        or not relative_path
        or relative_path.startswith(("/", "\\"))
        or "\\" in relative_path
        or WINDOWS_ABSOLUTE_PATTERN.match(relative_path)
        or URI_SCHEME_PATTERN.match(relative_path)
        or ".." in PurePosixPath(relative_path).parts
    ):
        raise ValueError(f"unsafe package-relative path: {relative_path!r}")
    resolved_root = root.resolve()
    candidate = (root / PurePosixPath(relative_path)).resolve()
    try:
        candidate.relative_to(resolved_root)
    except ValueError as error:
        raise ValueError(f"package path escapes handoff root: {relative_path!r}") from error
    return candidate


def _relative_output(handoff_root: Path, output_path: Path) -> str:
    try:
        return output_path.resolve().relative_to(handoff_root.resolve()).as_posix()
    except ValueError:
        return str(output_path.resolve())


def build_contact_sheet(handoff_root: Path, output_path: Path) -> dict:
    """Build a deterministic PNG index from package-relative manifest assets."""

    handoff_root = Path(handoff_root)
    output_path = Path(output_path)
    if os.path.lexists(output_path):
        raise FileExistsError(f"contact-sheet output already exists: {output_path}")
    manifest_file = handoff_root / MANIFEST_PATH
    manifest = json.loads(
        manifest_file.read_text(encoding="utf-8"),
        parse_constant=_reject_nonfinite_json_constant,
    )
    assets = sorted(manifest.get("assets", []), key=lambda asset: asset["assetId"])
    if not assets:
        raise ValueError("asset manifest contains no assets")

    font = ImageFont.load_default()
    columns = min(MAX_COLUMNS, len(assets))
    rows = math.ceil(len(assets) / columns)
    sheet = Image.new("RGB", (columns * TILE_WIDTH, rows * TILE_HEIGHT), "white")
    draw = ImageDraw.Draw(sheet)
    labels = []

    for index, asset in enumerate(assets):
        delivery_path = asset["deliveryRelativePath"]
        source = _package_path(handoff_root, delivery_path)
        if not source.is_file():
            raise FileNotFoundError(f"manifest asset is missing: {delivery_path}")
        filename = PurePosixPath(delivery_path).name
        label = (
            f"{asset['assetId']} | {asset['width']}x{asset['height']} | {filename}"
        )
        labels.append(label)
        column = index % columns
        row = index // columns
        left = column * TILE_WIDTH
        top = row * TILE_HEIGHT
        image_left = left + PADDING
        image_top = top + PADDING

        with Image.open(source) as opened:
            rendered = opened.convert("RGB")
            resampling = getattr(Image, "Resampling", Image).LANCZOS
            rendered.thumbnail((IMAGE_WIDTH, IMAGE_HEIGHT), resampling)
            x = image_left + (IMAGE_WIDTH - rendered.width) // 2
            y = image_top + (IMAGE_HEIGHT - rendered.height) // 2
            sheet.paste(rendered, (x, y))

        draw.rectangle(
            (image_left, image_top, image_left + IMAGE_WIDTH, image_top + IMAGE_HEIGHT),
            outline="#b8b8b8",
            width=1,
        )
        draw.text((left + PADDING, top + 216), label, fill="black", font=font)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output_path, format="PNG", optimize=False, compress_level=9)
    return {
        "status": "created",
        "assetCount": len(assets),
        "outputPath": _relative_output(handoff_root, output_path),
        "width": sheet.width,
        "height": sheet.height,
        "labels": labels,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build a deterministic contact sheet for a UI handoff package."
    )
    parser.add_argument("handoff_root", type=Path)
    parser.add_argument("--output-path", type=Path)
    arguments = parser.parse_args(argv)
    output = arguments.output_path or (
        arguments.handoff_root / "reports" / "contact-sheet.png"
    )
    try:
        result = build_contact_sheet(arguments.handoff_root, output)
    except Exception as error:
        result = {
            "status": "failed",
            "issues": [
                {
                    "code": "CONTACT_SHEET_BUILD_FAILED",
                    "severity": "error",
                    "message": str(error),
                }
            ],
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
