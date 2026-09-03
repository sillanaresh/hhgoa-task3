#!/usr/bin/env python3
"""Fail when a tracked or unignored source file contains a common secret shape."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

PATTERNS = (
    re.compile(r"SERPAPI_API_KEY\s*=\s*[^\s#]{8,}", re.IGNORECASE),
    re.compile(r"(?:ghp|github_pat)_[A-Za-z0-9_]{20,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"[\"']private_key[\"']\s*:\s*[\"'](?:0x)?[0-9a-fA-F]{64}[\"']"),
)
SKIPPED_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".onnx", ".lock"}
SAFE_PLACEHOLDERS = {"test-search-key", "your_key_here"}


def source_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        check=True,
        capture_output=True,
    )
    return [Path(value.decode()) for value in result.stdout.split(b"\0") if value]


def main() -> int:
    findings: list[str] = []
    for path in source_files():
        if path.suffix.lower() in SKIPPED_SUFFIXES or not path.is_file():
            continue
        try:
            text = path.read_text("utf-8")
        except UnicodeDecodeError:
            continue
        for line_number, line in enumerate(text.splitlines(), start=1):
            for pattern in PATTERNS:
                match = pattern.search(line)
                if match and not any(
                    placeholder in match.group(0).lower() for placeholder in SAFE_PLACEHOLDERS
                ):
                    findings.append(f"{path}:{line_number}")
                    break
    if findings:
        print("Possible secret values found:")
        print("\n".join(findings))
        return 1
    print("Secret shape scan passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
