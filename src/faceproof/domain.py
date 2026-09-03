"""Typed records shared by the pipeline, API, and command line interface."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class DomainModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RunStatus(StrEnum):
    CREATED = "created"
    RUNNING = "running"
    AWAITING_PUBLISH = "awaiting_publish"
    PUBLISHING = "publishing"
    VERIFIED = "verified"
    FAILED = "failed"
    CANCELED = "canceled"


class StepStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETE = "complete"
    FAILED = "failed"
    SKIPPED = "skipped"


class PipelineStep(DomainModel):
    key: str
    title: str
    status: StepStatus = StepStatus.PENDING
    detail: str
    started_at: datetime | None = None
    completed_at: datetime | None = None


def initial_steps() -> list[PipelineStep]:
    return [
        PipelineStep(
            key="face",
            title="Detect and encode face",
            detail="Waiting for an input image.",
        ),
        PipelineStep(
            key="search",
            title="Search the public web",
            detail="A fresh Google Lens search will run after face detection.",
        ),
        PipelineStep(
            key="compare",
            title="Compare candidate faces",
            detail="Each social result will be checked with the local face model.",
        ),
        PipelineStep(
            key="evidence",
            title="Prepare evidence fingerprint",
            detail="The selected source and match details will be written to canonical JSON.",
        ),
        PipelineStep(
            key="publish",
            title="Publish public proof",
            detail="Publication waits for explicit approval.",
        ),
        PipelineStep(
            key="verify",
            title="Verify from Base Sepolia",
            detail="The fingerprint will be read back from the confirmed transaction.",
        ),
    ]


class FaceSummary(DomainModel):
    faces_detected: int
    selected_box: tuple[int, int, int, int]
    detection_score: float
    embedding_dimensions: int
    detector_model: str
    recognizer_model: str
    input_sha256: str
    crop_sha256: str
    input_url: str
    crop_url: str
    annotated_url: str
    warning: str | None = None


class SearchTrace(DomainModel):
    query_kind: str
    provider: str = "SerpApi Google Lens"
    search_id: str | None = None
    provider_status: str
    created_at: str | None = None
    result_count: int = 0
    social_result_count: int = 0


class SearchCandidate(DomainModel):
    candidate_id: str
    position: int
    title: str
    source: str
    post_url: str
    media_url: str | None = None
    thumbnail_url: str | None = None
    exact_match: bool = False
    query_kind: str
    image_url: str | None = None
    image_sha256: str | None = None
    faces_detected: int | None = None
    similarity: float | None = None
    passes_threshold: bool = False
    evaluation_error: str | None = None


class MatchSummary(DomainModel):
    candidate_id: str
    post_url: str
    title: str
    source: str
    media_url: str
    local_image_url: str
    image_sha256: str
    similarity: float
    threshold: float
    exact_match: bool
    query_kind: str


class EvidenceSummary(DomainModel):
    evidence_id: str
    manifest_url: str
    canonical_url: str
    created_at: datetime
    schema_version: str


class BlockchainReceipt(DomainModel):
    network: str
    chain_id: int
    transaction_hash: str
    block_number: int
    from_address: str
    to_address: str
    evidence_id: str
    confirmations: int
    explorer_url: str
    verified_at: datetime | None = None
    verification_passed: bool = False


class PublicError(DomainModel):
    code: str
    message: str
    recovery: str | None = None


class RunRecord(DomainModel):
    run_id: str
    status: RunStatus
    current_step: str | None = None
    status_message: str
    created_at: datetime
    updated_at: datetime
    original_filename: str
    steps: list[PipelineStep] = Field(default_factory=initial_steps)
    face: FaceSummary | None = None
    searches: list[SearchTrace] = Field(default_factory=list)
    candidates: list[SearchCandidate] = Field(default_factory=list)
    selected_match: MatchSummary | None = None
    evidence: EvidenceSummary | None = None
    blockchain: BlockchainReceipt | None = None
    error: PublicError | None = None


class HealthResponse(DomainModel):
    status: str
    version: str
    search_configured: bool
    models_ready: bool
    wallet_configured: bool
    wallet_address: str | None = None
    wallet_funded: bool
    wallet_balance_wei: int | None = None
    blockchain_reachable: bool
    chain_id: int
    network: str
