from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from faceproof.config import Settings


@pytest.fixture
def settings(tmp_path: Path) -> Iterator[Settings]:
    configured = Settings(
        _env_file=None,
        models_dir=tmp_path / "models",
        runs_dir=tmp_path / "runs",
        wallet_file=tmp_path / "wallet.json",
        serpapi_api_key="test-search-key",
        base_rpc_url="https://rpc.example.test",
    )
    configured.ensure_runtime_dirs()
    yield configured
