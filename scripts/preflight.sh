#!/usr/bin/env bash
set -euo pipefail

repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_dir"

uv run faceproof doctor --strict
./scripts/check.sh

echo "Preflight passed. The live pipeline and repository checks are ready."
