from __future__ import annotations

import stat
import uuid
from pathlib import Path

import pytest

from faceproof.store import RunStore
from faceproof.wallet import create_wallet, load_wallet


def test_store_round_trip_and_path_guards(tmp_path: Path) -> None:
    store = RunStore(tmp_path / "runs")
    record = store.create("portrait.jpg")

    assert store.get(record.run_id).original_filename == "portrait.jpg"
    assert stat.S_IMODE(store.root.stat().st_mode) == 0o700
    assert stat.S_IMODE(store.run_dir(record.run_id).stat().st_mode) == 0o700
    with pytest.raises(ValueError):
        store.run_dir("not-a-run-id")
    with pytest.raises(ValueError):
        store.artifact_path(record.run_id, "../secret")
    missing_id = uuid.uuid4().hex
    with pytest.raises(FileNotFoundError):
        store.get(missing_id)
    assert not store.run_dir(missing_id).exists()


def test_wallet_is_disposable_private_and_stable(tmp_path: Path) -> None:
    path = tmp_path / "wallet.json"
    address = create_wallet(path)

    assert create_wallet(path) == address
    assert load_wallet(path).address == address
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
