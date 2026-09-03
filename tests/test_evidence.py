from __future__ import annotations

import json
from pathlib import Path

from faceproof.domain import FaceSummary, MatchSummary, SearchTrace
from faceproof.evidence import (
    build_manifest,
    evidence_id,
    load_manifest,
    manifest_payload,
    write_evidence,
)


def _manifest():
    face = FaceSummary(
        faces_detected=1,
        selected_box=(12, 18, 160, 180),
        detection_score=0.992,
        embedding_dimensions=128,
        detector_model="YuNet",
        recognizer_model="SFace",
        input_sha256="a" * 64,
        crop_sha256="b" * 64,
        input_url="/input.jpg",
        crop_url="/face.jpg",
        annotated_url="/annotated.jpg",
    )
    search = SearchTrace(
        query_kind="face_crop",
        search_id="search-1",
        provider_status="Success",
        result_count=8,
        social_result_count=2,
    )
    match = MatchSummary(
        candidate_id="face_crop-1",
        post_url="https://www.instagram.com/p/example/",
        title="Public post",
        source="Instagram",
        media_url="https://cdn.example.test/photo.jpg",
        local_image_url="/candidate-1.jpg",
        image_sha256="c" * 64,
        similarity=0.7312344,
        threshold=0.45,
        exact_match=True,
        query_kind="face_crop",
    )
    return build_manifest(face, [search], match)


def test_evidence_fingerprint_is_stable_across_key_order() -> None:
    manifest = _manifest()
    payload = manifest_payload(manifest)
    reversed_payload = dict(reversed(list(payload.items())))

    assert evidence_id(payload) == evidence_id(reversed_payload)


def test_any_covered_change_changes_the_fingerprint() -> None:
    payload = manifest_payload(_manifest())
    original = evidence_id(payload)
    payload["discovered_content"]["title"] = "Changed title"

    assert evidence_id(payload) != original


def test_write_evidence_is_reproducible_and_loadable(tmp_path: Path) -> None:
    manifest = _manifest()
    pretty_path, canonical_path, digest = write_evidence(tmp_path, manifest)

    assert evidence_id(load_manifest(pretty_path)) == digest
    assert canonical_path.read_bytes() == canonical_path.read_bytes().strip()
    assert json.loads(pretty_path.read_text("utf-8"))["privacy"] == {
        "blockchain_payload": "schema marker and SHA-256 fingerprint only",
        "face_embedding_stored": False,
        "raw_image_stored_on_chain": False,
    }
    payload = json.loads(pretty_path.read_text("utf-8"))
    assert payload["input"]["crop_sha256"] == "b" * 64
    assert payload["input"]["embedding_dimensions"] == 128
    assert payload["search"]["cache_disabled"] is True
