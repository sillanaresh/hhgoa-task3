#!/usr/bin/env python3
"""Confirm the built wheel contains every runtime web asset."""

from __future__ import annotations

import sys
from pathlib import Path
from zipfile import ZipFile

REQUIRED_ASSETS = {
    "faceproof/static/app.js",
    "faceproof/static/favicon.svg",
    "faceproof/static/index.html",
    "faceproof/static/styles.css",
    "faceproof/static/tokens.css",
}


def main(directory: Path) -> int:
    wheels = sorted(directory.glob("faceproof-*.whl"), key=lambda path: path.stat().st_mtime)
    if not wheels:
        print(f"No FaceProof wheel found in {directory}")
        return 1
    wheel = wheels[-1]
    with ZipFile(wheel) as archive:
        missing = REQUIRED_ASSETS.difference(archive.namelist())
    if missing:
        print("Built wheel is missing runtime assets:")
        print("\n".join(sorted(missing)))
        return 1
    print(f"Package asset check passed: {wheel.name}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: package_check.py WHEEL_DIRECTORY")
    raise SystemExit(main(Path(sys.argv[1])))
