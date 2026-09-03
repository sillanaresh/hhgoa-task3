from __future__ import annotations

import asyncio
import io
import json
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from faceproof.domain import BlockchainReceipt, RunStatus, SearchCandidate, SearchTrace
from faceproof.face import DetectedFace, FaceAnalysis
from faceproof.pipeline import Pipeline
from faceproof.search import LensSearchResult
from faceproof.store import RunStore


def _jpeg() -> bytes:
    output = io.BytesIO()
    Image.new("RGB", (240, 240), (65, 109, 117)).save(output, format="JPEG")
    return output.getvalue()


class FakeFaceEngine:
    detector_name = "Test YuNet"
    recognizer_name = "Test SFace"

    def __init__(self, *_: object) -> None:
        pass

    def analyze(self, image: np.ndarray, *, require_face: bool = True) -> FaceAnalysis:
        del require_face
        embedding = np.zeros(128, dtype=np.float32)
        embedding[0] = 1
        raw = np.array(
            [40, 35, 150, 165, 80, 90, 150, 90, 115, 120, 90, 160, 145, 160, 0.98],
            dtype=np.float32,
        )
        return FaceAnalysis(
            faces=(
                DetectedFace(
                    raw=raw,
                    box=(40, 35, 150, 165),
                    score=0.98,
                    crop=image[35:200, 40:190],
                    embedding=embedding,
                ),
            )
        )

    @staticmethod
    def annotate(image: np.ndarray, _: FaceAnalysis) -> np.ndarray:
        return image.copy()

    @staticmethod
    def best_similarity(_: np.ndarray, __: FaceAnalysis) -> float:
        return 0.731234


class FakeSearchClient:
    def __init__(self, *_: object) -> None:
        pass

    async def search(self, _: bytes, *, query_kind: str) -> LensSearchResult:
        position = 1 if query_kind == "face_crop" else 2
        candidate = SearchCandidate(
            candidate_id=f"{query_kind}-1",
            position=position,
            title=f"Fresh {query_kind} public result",
            source="Instagram",
            post_url=f"https://www.instagram.com/p/{query_kind}/",
            media_url=f"https://cdn.example.test/{query_kind}.jpg",
            exact_match=query_kind == "face_crop",
            query_kind=query_kind,
        )
        return LensSearchResult(
            trace=SearchTrace(
                query_kind=query_kind,
                search_id=f"search-{query_kind}",
                provider_status="Success",
                result_count=3,
                social_result_count=1,
            ),
            candidates=(candidate,),
        )


class FakeChain:
    def __init__(self) -> None:
        self.published_digest: str | None = None

    def _receipt(self, digest: str, passed: bool) -> BlockchainReceipt:
        return BlockchainReceipt(
            network="Base Sepolia",
            chain_id=84532,
            transaction_hash="0x" + "9" * 64,
            block_number=12_345,
            from_address="0x1111111111111111111111111111111111111111",
            to_address="0x1111111111111111111111111111111111111111",
            evidence_id=digest,
            confirmations=2,
            explorer_url="https://sepolia.basescan.org/tx/0x" + "9" * 64,
            verified_at=datetime.now(UTC) if passed else None,
            verification_passed=passed,
        )

    def publish(self, digest: str) -> BlockchainReceipt:
        self.published_digest = digest
        return self._receipt(digest, False)

    def verify(self, _: str, expected: str) -> BlockchainReceipt:
        return self._receipt(expected, expected == self.published_digest)


@pytest.mark.asyncio
async def test_pipeline_prepares_publishes_and_reverifies(
    settings,
    monkeypatch,
) -> None:
    monkeypatch.setattr("faceproof.pipeline.FaceEngine", FakeFaceEngine)
    monkeypatch.setattr("faceproof.pipeline.SerpApiLensClient", FakeSearchClient)

    async def fake_download(_: str, *, maximum_bytes: int) -> tuple[bytes, str]:
        del maximum_bytes
        return _jpeg(), "image/jpeg"

    monkeypatch.setattr("faceproof.pipeline.download_image", fake_download)
    store = RunStore(settings.runs_dir)
    record = store.create("face.jpg")
    upload = store.artifact_path(record.run_id, "upload.bin")
    upload.write_bytes(_jpeg())
    pipeline = Pipeline(settings, store)
    chain = FakeChain()
    monkeypatch.setattr(pipeline, "_blockchain_client", lambda: chain)

    prepared = await pipeline.prepare(record.run_id, upload)

    assert prepared.status == RunStatus.AWAITING_PUBLISH
    assert len(prepared.searches) == 2
    assert len(prepared.candidates) == 2
    assert prepared.selected_match is not None
    assert prepared.selected_match.post_url.endswith("/face_crop/")
    assert prepared.selected_match.threshold == 0.363
    assert prepared.evidence is not None
    assert not upload.exists()
    evidence_file = Path(settings.runs_dir / record.run_id / "evidence.json")
    assert await asyncio.to_thread(evidence_file.is_file)

    verified = await pipeline.publish_and_verify(record.run_id)

    assert verified.status == RunStatus.VERIFIED
    assert verified.blockchain is not None
    assert verified.blockchain.verification_passed is True
    assert all(step.status.value == "complete" for step in verified.steps)

    second_call = await pipeline.publish_and_verify(record.run_id)
    assert second_call.status == RunStatus.VERIFIED

    evidence_path = store.artifact_path(record.run_id, "evidence.json")
    tampered = json.loads(evidence_path.read_text("utf-8"))
    tampered["discovered_content"]["title"] = "Tampered title"
    evidence_path.write_text(json.dumps(tampered), encoding="utf-8")

    failed = await pipeline.verify_saved(record.run_id)
    assert failed.status == RunStatus.FAILED
    assert failed.blockchain is not None
    assert failed.blockchain.verification_passed is False


@pytest.mark.asyncio
async def test_pipeline_preserves_a_clear_no_match_failure(settings, monkeypatch) -> None:
    monkeypatch.setattr("faceproof.pipeline.FaceEngine", FakeFaceEngine)

    class EmptySearchClient(FakeSearchClient):
        async def search(self, _: bytes, *, query_kind: str) -> LensSearchResult:
            return LensSearchResult(
                trace=SearchTrace(query_kind=query_kind, provider_status="Success"),
                candidates=(),
            )

    monkeypatch.setattr("faceproof.pipeline.SerpApiLensClient", EmptySearchClient)
    store = RunStore(settings.runs_dir)
    record = store.create("face.jpg")
    upload = store.artifact_path(record.run_id, "upload.bin")
    upload.write_bytes(_jpeg())

    failed = await Pipeline(settings, store).prepare(record.run_id, upload)

    assert failed.status == RunStatus.FAILED
    assert failed.error is not None
    assert failed.error.code == "no_match"
    assert not upload.exists()
    assert failed.current_step == "search"
    assert next(step for step in failed.steps if step.key == "search").status.value == "failed"
