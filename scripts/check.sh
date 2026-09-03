#!/usr/bin/env bash
set -euo pipefail

repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_dir"

uv run ruff format --check src tests scripts/secret_scan.py scripts/package_check.py
uv run ruff check src tests scripts/secret_scan.py scripts/package_check.py
uv run mypy src
uv run pytest --cov=faceproof --cov-report=term-missing
uv run bandit -q -r src
uv run pip-audit
uv run python scripts/secret_scan.py
uv build --wheel --out-dir .context/check-dist
uv run python scripts/package_check.py .context/check-dist
