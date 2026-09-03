from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from hexbytes import HexBytes

from faceproof.blockchain import PROOF_PREFIX, BaseSepoliaClient, _digest_bytes
from faceproof.errors import BlockchainError
from faceproof.wallet import create_wallet


class FakeEth:
    chain_id = 84532
    block_number = 101

    def __init__(self, payload: bytes) -> None:
        self.payload = payload

    def get_transaction(self, _: object) -> dict[str, Any]:
        return {
            "input": HexBytes(self.payload),
            "chainId": self.chain_id,
            "from": "0x1111111111111111111111111111111111111111",
            "to": "0x1111111111111111111111111111111111111111",
            "hash": HexBytes("0x" + "9" * 64),
        }

    def get_transaction_receipt(self, _: object) -> dict[str, Any]:
        return {"status": 1, "blockNumber": 100}


class FakeWeb3:
    def __init__(self, payload: bytes) -> None:
        self.eth = FakeEth(payload)


class FakePublishEth:
    chain_id = 84532
    block_number = 501
    gas_price = 1_000_000_000

    def __init__(self) -> None:
        self.transaction: dict[str, Any] | None = None

    @staticmethod
    def get_balance(_: object) -> int:
        return 10**16

    @staticmethod
    def get_transaction_count(_: object, __: str) -> int:
        return 7

    def estimate_gas(self, transaction: dict[str, Any]) -> int:
        self.transaction = transaction
        return 25_000

    @staticmethod
    def send_raw_transaction(_: bytes) -> HexBytes:
        return HexBytes("0x" + "8" * 64)

    @staticmethod
    def wait_for_transaction_receipt(
        _: object,
        *,
        timeout: int,
        poll_latency: int,
    ) -> dict[str, int]:
        assert timeout == 120
        assert poll_latency == 2
        return {"status": 1, "blockNumber": 500}


class FakePublishWeb3:
    def __init__(self) -> None:
        self.eth = FakePublishEth()


def test_digest_requires_exact_sha256_hex() -> None:
    assert _digest_bytes("ab" * 32) == bytes.fromhex("ab" * 32)
    with pytest.raises(BlockchainError):
        _digest_bytes("abc")
    with pytest.raises(BlockchainError):
        _digest_bytes("zz" * 32)


def test_verification_reads_and_compares_public_payload(tmp_path: Path) -> None:
    digest = "ab" * 32
    client = BaseSepoliaClient("https://unused.test", 84532, "https://scan.test", tmp_path / "w")
    client.web3 = FakeWeb3(PROOF_PREFIX + bytes.fromhex(digest))  # type: ignore[assignment]

    receipt = client.verify("0x" + "9" * 64, digest)

    assert receipt.verification_passed is True
    assert receipt.confirmations == 2
    assert receipt.evidence_id == digest
    assert receipt.transaction_hash.startswith("0x")


def test_verification_fails_after_fingerprint_change(tmp_path: Path) -> None:
    stored_digest = "ab" * 32
    expected_digest = "cd" * 32
    client = BaseSepoliaClient("https://unused.test", 84532, "https://scan.test", tmp_path / "w")
    client.web3 = FakeWeb3(  # type: ignore[assignment]
        PROOF_PREFIX + bytes.fromhex(stored_digest)
    )

    assert client.verify("0x" + "9" * 64, expected_digest).verification_passed is False


def test_verification_requires_explicit_chain_and_self_transaction(tmp_path: Path) -> None:
    digest = "ab" * 32
    client = BaseSepoliaClient("https://unused.test", 84532, "https://scan.test", tmp_path / "w")
    fake_web3 = FakeWeb3(PROOF_PREFIX + bytes.fromhex(digest))
    transaction = fake_web3.eth.get_transaction(None)
    transaction.pop("chainId")
    transaction["to"] = None
    fake_web3.eth.get_transaction = lambda _: transaction  # type: ignore[method-assign]
    client.web3 = fake_web3  # type: ignore[assignment]

    receipt = client.verify("0x" + "9" * 64, digest)

    assert receipt.verification_passed is False


def test_publish_signs_zero_value_self_transaction_with_versioned_digest(
    tmp_path: Path,
) -> None:
    digest = "ef" * 32
    wallet_path = tmp_path / "wallet.json"
    address = create_wallet(wallet_path)
    client = BaseSepoliaClient(
        "https://unused.test",
        84532,
        "https://scan.test",
        wallet_path,
    )
    fake_web3 = FakePublishWeb3()
    client.web3 = fake_web3  # type: ignore[assignment]

    receipt = client.publish(digest)

    transaction = fake_web3.eth.transaction
    assert transaction is not None
    assert transaction["to"] == address
    assert transaction["value"] == 0
    assert bytes(transaction["data"]) == PROOF_PREFIX + bytes.fromhex(digest)
    assert receipt.transaction_hash == "0x" + "8" * 64
    assert receipt.explorer_url.endswith(receipt.transaction_hash)
