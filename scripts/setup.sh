#!/usr/bin/env bash
set -euo pipefail

repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_dir"

if ! command -v uv >/dev/null 2>&1; then
  echo "uv is required. Install it from https://docs.astral.sh/uv/getting-started/installation/"
  exit 1
fi

uv sync --locked --extra dev
uv run faceproof models

if [[ ! -f .context/secrets.env ]]; then
  mkdir -p .context
  umask 077
  printf 'SERPAPI_API_KEY=\n' > .context/secrets.env
  echo "Created .context/secrets.env. Add your SerpApi key there."
fi
chmod 700 .context
chmod 600 .context/secrets.env

uv run faceproof doctor
