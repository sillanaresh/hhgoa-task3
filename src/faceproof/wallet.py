"""Disposable Base Sepolia wallet management."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from eth_account import Account
from eth_account.signers.local import LocalAccount

from faceproof.errors import ConfigurationError
from faceproof.utils import atomic_write_json, utc_now


def create_wallet(path: Path) -> str:
    if path.exists():
        return load_wallet(path).address

    account: LocalAccount = Account.create(os.urandom(32))
    payload = {
        "address": account.address,
        "created_at": utc_now().isoformat(),
        "network": "Base Sepolia",
        "private_key": account.key.hex(),
        "warning": "Disposable testnet wallet. Never fund this address with real assets.",
    }
    atomic_write_json(path, payload)
    path.chmod(0o600)
    return account.address


def load_wallet(path: Path) -> LocalAccount:
    if not path.exists():
        raise ConfigurationError(
            "The Base Sepolia test wallet has not been created.",
            "Run faceproof wallet-create, then fund the printed address with free test ETH.",
        )
    try:
        payload: dict[str, Any] = json.loads(path.read_text("utf-8"))
        private_key = str(payload["private_key"])
        account: LocalAccount = Account.from_key(private_key)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        raise ConfigurationError(
            "The Base Sepolia wallet file could not be read.",
            "Move the invalid wallet file aside and run faceproof wallet-create.",
        ) from exc
    return account


def wallet_address(path: Path) -> str | None:
    try:
        return load_wallet(path).address
    except ConfigurationError:
        return None
