"""Canonical evidence documents and deterministic fingerprints."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from faceproof.domain import FaceSummary, MatchSummary, SearchTrace
from faceproof.utils import atomic_write_bytes, canonical_json_bytes, sha256_bytes, utc_now


class StrictEvidenceModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


Sha256Hex = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]


class InputEvidence(StrictEvidenceModel):
    sha256: Sha256Hex
    crop_sha256: Sha256Hex
    faces_detected: int = Field(ge=1)
    selected_box: tuple[int, int, int, int]
    detection_score: float = Field(ge=0.0, le=1.0)
    embedding_dimensions: int = Field(ge=1)
    detector_model: str
    recognizer_model: str


class SearchEvidence(StrictEvidenceModel):
    provider: str
    live_search: Literal[True] = True
    cache_disabled: Literal[True] = True
    queries: list[SearchTrace]


class ContentEvidence(StrictEvidenceModel):
    platform: str
    post_url: str
    title: str
    source_media_url: str
    retrieved_media_sha256: Sha256Hex


class FaceMatchEvidence(StrictEvidenceModel):
    metric: Literal["cosine_similarity"] = "cosine_similarity"
    score: float = Field(ge=-1.0, le=1.0)
    threshold: float = Field(ge=-1.0, le=1.0)
    decision: Literal["match"] = "match"
    exact_visual_match_reported: bool
    query_kind: str


class PrivacyEvidence(StrictEvidenceModel):
    face_embedding_stored: Literal[False] = False
    raw_image_stored_on_chain: Literal[False] = False
    blockchain_payload: Literal["schema marker and SHA-256 fingerprint only"] = (
        "schema marker and SHA-256 fingerprint only"
    )


class EvidenceManifest(StrictEvidenceModel):
    schema_version: Literal["faceproof.evidence.v1"] = "faceproof.evidence.v1"
    collected_at: str
    input: InputEvidence
    search: SearchEvidence
    discovered_content: ContentEvidence
    face_match: FaceMatchEvidence
    privacy: PrivacyEvidence


def build_manifest(
    face: FaceSummary,
    searches: list[SearchTrace],
    match: MatchSummary,
) -> EvidenceManifest:
    return EvidenceManifest(
        collected_at=utc_now().isoformat(),
        input=InputEvidence(
            sha256=face.input_sha256,
            crop_sha256=face.crop_sha256,
            faces_detected=face.faces_detected,
            selected_box=face.selected_box,
            detection_score=round(face.detection_score, 6),
            embedding_dimensions=face.embedding_dimensions,
            detector_model=face.detector_model,
            recognizer_model=face.recognizer_model,
        ),
        search=SearchEvidence(queries=searches, provider="SerpApi Google Lens"),
        discovered_content=ContentEvidence(
            platform=match.source,
            post_url=match.post_url,
            title=match.title,
            source_media_url=match.media_url,
            retrieved_media_sha256=match.image_sha256,
        ),
        face_match=FaceMatchEvidence(
            score=round(match.similarity, 6),
            threshold=round(match.threshold, 6),
            exact_visual_match_reported=match.exact_match,
            query_kind=match.query_kind,
        ),
        privacy=PrivacyEvidence(),
    )


def manifest_payload(manifest: EvidenceManifest | dict[str, Any]) -> dict[str, Any]:
    if isinstance(manifest, EvidenceManifest):
        return manifest.model_dump(mode="json")
    return EvidenceManifest.model_validate(manifest).model_dump(mode="json")


def evidence_id(manifest: EvidenceManifest | dict[str, Any]) -> str:
    return sha256_bytes(canonical_json_bytes(manifest_payload(manifest)))


def write_evidence(run_dir: Path, manifest: EvidenceManifest) -> tuple[Path, Path, str]:
    payload = manifest_payload(manifest)
    canonical = canonical_json_bytes(payload)
    pretty_path = run_dir / "evidence.json"
    canonical_path = run_dir / "evidence.canonical.json"
    pretty = (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode(
        "utf-8"
    )
    atomic_write_bytes(pretty_path, pretty)
    atomic_write_bytes(canonical_path, canonical)
    return pretty_path, canonical_path, sha256_bytes(canonical)


def load_manifest(path: Path) -> EvidenceManifest:
    return EvidenceManifest.model_validate_json(path.read_text("utf-8"))
