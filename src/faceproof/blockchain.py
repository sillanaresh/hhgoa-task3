"""Public Base Sepolia publication and independent transaction verification."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from eth_typing import HexStr
from hexbytes import HexBytes
from web3 import HTTPProvider, Web3
from web3.exceptions import TimeExhausted, TransactionNotFound
from web3.types import TxParams, Wei

from faceproof.domain import BlockchainReceipt
from faceproof.errors import BlockchainError
from faceproof.wallet import load_wallet, wallet_address

PROOF_PREFIX = b"FACEPROOF\x01"
NETWORK_NAME = "Base Sepolia"


@dataclass(frozen=True)
class BlockchainStatus:
    reachable: bool
    chain_id: int | None
    wallet_address: str | None
    balance_wei: int | None


class BaseSepoliaClient:
    def __init__(
        self,
        rpc_url: str,
        chain_id: int,
        explorer_url: str,
        wallet_file: Path,
    ) -> None:
        self.web3 = Web3(HTTPProvider(rpc_url, request_kwargs={"timeout": 20}))
        self.chain_id = chain_id
        self.explorer_url = explorer_url.rstrip("/")
        self.wallet_file = wallet_file

    def status(self) -> BlockchainStatus:
        address = wallet_address(self.wallet_file)
        try:
            connected_chain = int(self.web3.eth.chain_id)
            checksum_address = Web3.to_checksum_address(address) if address else None
            balance = self.web3.eth.get_balance(checksum_address) if checksum_address else None
            return BlockchainStatus(True, connected_chain, address, balance)
        except Exception:
            return BlockchainStatus(False, None, address, None)

    def publish(self, digest_hex: str) -> BlockchainReceipt:
        digest = _digest_bytes(digest_hex)
        account = load_wallet(self.wallet_file)
        try:
            connected_chain = int(self.web3.eth.chain_id)
            if connected_chain != self.chain_id:
                raise BlockchainError(
                    f"The RPC endpoint reported chain {connected_chain}, not {self.chain_id}.",
                    "Use the Base Sepolia RPC endpoint and retry.",
                )
            balance = self.web3.eth.get_balance(account.address)
            if balance <= 0:
                raise BlockchainError(
                    "The disposable wallet has no Base Sepolia test ETH.",
                    "Fund the public wallet address from a Base Sepolia faucet and retry.",
                )

            payload = HexBytes(PROOF_PREFIX + digest)
            transaction: TxParams = {
                "chainId": self.chain_id,
                "nonce": self.web3.eth.get_transaction_count(account.address, "pending"),
                "to": account.address,
                "value": Wei(0),
                "data": payload,
                "gasPrice": self.web3.eth.gas_price,
            }
            transaction["gas"] = self.web3.eth.estimate_gas(transaction)
            signed = account.sign_transaction(transaction)  # type: ignore[arg-type]
            transaction_hash = self.web3.eth.send_raw_transaction(signed.raw_transaction)
            chain_receipt = self.web3.eth.wait_for_transaction_receipt(
                transaction_hash,
                timeout=120,
                poll_latency=2,
            )
        except BlockchainError:
            raise
        except TimeExhausted as exc:
            raise BlockchainError(
                "The transaction was sent but was not confirmed within two minutes.",
                f"Check {self.explorer_url}/address/{account.address} before retrying.",
            ) from exc
        except Exception as exc:
            raise BlockchainError(
                "Base Sepolia rejected the proof transaction.",
                "Check the RPC connection and test ETH balance, then retry.",
            ) from exc

        if int(chain_receipt["status"]) != 1:
            raise BlockchainError("The proof transaction was confirmed but failed.")
        current_block = int(self.web3.eth.block_number)
        block_number = int(chain_receipt["blockNumber"])
        hash_hex = Web3.to_hex(transaction_hash)
        return BlockchainReceipt(
            network=NETWORK_NAME,
            chain_id=self.chain_id,
            transaction_hash=hash_hex,
            block_number=block_number,
            from_address=account.address,
            to_address=account.address,
            evidence_id=digest_hex.lower(),
            confirmations=max(1, current_block - block_number + 1),
            explorer_url=f"{self.explorer_url}/tx/{hash_hex}",
        )

    def verify(self, transaction_hash: str, expected_digest: str) -> BlockchainReceipt:
        digest = _digest_bytes(expected_digest)
        expected_payload = PROOF_PREFIX + digest
        try:
            connected_chain = int(self.web3.eth.chain_id)
            if connected_chain != self.chain_id:
                raise BlockchainError(f"The RPC endpoint is connected to chain {connected_chain}.")
            hash_value = cast(HexStr, transaction_hash)
            transaction = self.web3.eth.get_transaction(hash_value)
            chain_receipt = self.web3.eth.get_transaction_receipt(hash_value)
        except BlockchainError:
            raise
        except TransactionNotFound as exc:
            raise BlockchainError(
                "The proof transaction was not found on Base Sepolia.",
                "Check the transaction hash and network, then retry.",
            ) from exc
        except Exception as exc:
            raise BlockchainError(
                "The blockchain record could not be read.",
                "Check the network connection and retry verification.",
            ) from exc

        input_data = transaction.get("input", transaction.get("data", b""))
        actual_payload = bytes(HexBytes(input_data))
        raw_chain_id = transaction.get("chainId")
        transaction_chain_id = int(raw_chain_id) if raw_chain_id is not None else None
        from_address = str(transaction.get("from") or "")
        to_address = str(transaction.get("to") or "")
        passed = (
            transaction_chain_id == self.chain_id
            and int(chain_receipt["status"]) == 1
            and actual_payload == expected_payload
            and bool(from_address)
            and from_address.lower() == to_address.lower()
        )
        block_number = int(chain_receipt["blockNumber"])
        current_block = int(self.web3.eth.block_number)
        hash_hex = Web3.to_hex(HexBytes(transaction["hash"]))
        return BlockchainReceipt(
            network=NETWORK_NAME,
            chain_id=self.chain_id,
            transaction_hash=hash_hex,
            block_number=block_number,
            from_address=from_address,
            to_address=to_address,
            evidence_id=expected_digest.lower(),
            confirmations=max(1, current_block - block_number + 1),
            explorer_url=f"{self.explorer_url}/tx/{hash_hex}",
            verified_at=datetime.now(UTC),
            verification_passed=passed,
        )


def _digest_bytes(value: str) -> bytes:
    cleaned = value.lower().removeprefix("0x")
    if len(cleaned) != 64:
        raise BlockchainError("The evidence fingerprint must contain 64 hexadecimal characters.")
    try:
        return bytes.fromhex(cleaned)
    except ValueError as exc:
        raise BlockchainError("The evidence fingerprint is not valid hexadecimal data.") from exc
