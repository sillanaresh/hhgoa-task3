#!/usr/bin/env bash
set -euo pipefail

repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_dir"

uv run faceproof doctor
echo
echo "Opening FaceProof at http://127.0.0.1:8765"

if command -v open >/dev/null 2>&1; then
  (sleep 1 && open http://127.0.0.1:8765) &
fi

exec uv run faceproof serve --port 8765
