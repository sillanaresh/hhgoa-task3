"""End to end orchestration from input image to public proof."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np

from faceproof.blockchain import BaseSepoliaClient
from faceproof.config import Settings
from faceproof.domain import (
    EvidenceSummary,
    FaceSummary,
    MatchSummary,
    PublicError,
    RunRecord,
    RunStatus,
    SearchCandidate,
    StepStatus,
)
from faceproof.errors import FaceProofError, NoMatchError
from faceproof.evidence import build_manifest, evidence_id, load_manifest, write_evidence
from faceproof.face import FaceEngine
from faceproof.image_io import (
    decode_image,
    download_image,
    encode_jpeg,
    lens_ready_jpeg,
    write_jpeg,
)
from faceproof.search import SerpApiLensClient
from faceproof.store import RunStore
from faceproof.utils import sha256_bytes, utc_now

logger = logging.getLogger(__name__)


class Pipeline:
    def __init__(self, settings: Settings, store: RunStore) -> None:
        self.settings = settings
        self.store = store
        self._publication_lock = asyncio.Lock()

    async def prepare(self, run_id: str, uploaded_path: Path) -> RunRecord:
        record = self.store.get(run_id)
        record.status = RunStatus.RUNNING
        record.status_message = "Starting local face analysis."
        self.store.save(record)

        try:
            face_engine = await asyncio.to_thread(
                FaceEngine,
                self.settings.models_dir,
                self.settings.detector_score_threshold,
            )
            record = await self._analyze_input(record, uploaded_path, face_engine)
            record = await self._search_web(record, face_engine)
            record = await self._compare_candidates(record, face_engine)
            record = await self._prepare_evidence(record)
            return record
        except asyncio.CancelledError:
            record = self.store.get(run_id)
            record.status = RunStatus.CANCELED
            record.status_message = "The run was canceled. Saved results remain available."
            if record.current_step:
                self._set_step(
                    record,
                    record.current_step,
                    StepStatus.SKIPPED,
                    "Canceled before this stage completed.",
                )
            self.store.save(record)
            raise
        except FaceProofError as exc:
            return self._fail(record.run_id, exc)
        except Exception as exc:
            return self._fail(
                record.run_id,
                FaceProofError(
                    "The pipeline stopped because of an unexpected internal error.",
                    "Keep the saved run and inspect the server log before retrying.",
                ),
                internal=exc,
            )

    async def publish_and_verify(self, run_id: str) -> RunRecord:
        async with self._publication_lock:
            return await self._publish_and_verify_locked(run_id)

    async def _publish_and_verify_locked(self, run_id: str) -> RunRecord:
        record = self.store.get(run_id)
        if record.status == RunStatus.VERIFIED:
            return record
        if record.status != RunStatus.AWAITING_PUBLISH:
            return self._fail(
                run_id,
                FaceProofError(
                    "This run is not ready for blockchain publication.",
                    "Wait for evidence preparation to finish or start a new run.",
                ),
            )
        if not record.evidence:
            return self._fail(
                run_id,
                FaceProofError(
                    "This run has no evidence ready to publish.",
                    "Complete face search and matching before publishing.",
                ),
            )

        record.status = RunStatus.PUBLISHING
        record.current_step = "publish"
        record.status_message = "Sending the evidence fingerprint to Base Sepolia."
        self._set_step(
            record,
            "publish",
            StepStatus.RUNNING,
            "Signing a zero value transaction with the disposable test wallet.",
        )
        self.store.save(record)

        try:
            manifest_path = self.store.artifact_path(run_id, "evidence.json")
            manifest = load_manifest(manifest_path)
            digest = evidence_id(manifest)
            if digest != record.evidence.evidence_id:
                raise FaceProofError(
                    "The local evidence changed after it was prepared.",
                    "Start a new search run so the evidence can be reviewed again.",
                )

            client = self._blockchain_client()
            receipt = await asyncio.to_thread(client.publish, digest)
            record = self.store.get(run_id)
            record.blockchain = receipt
            self._set_step(
                record,
                "publish",
                StepStatus.COMPLETE,
                f"Confirmed in Base Sepolia block {receipt.block_number}.",
            )
            record.current_step = "verify"
            record.status_message = "Reading the public transaction back from Base Sepolia."
            self._set_step(
                record,
                "verify",
                StepStatus.RUNNING,
                "Comparing the public transaction data with the local evidence fingerprint.",
            )
            self.store.save(record)

            verified = await asyncio.to_thread(client.verify, receipt.transaction_hash, digest)
            record = self.store.get(run_id)
            record.blockchain = verified
            if not verified.verification_passed:
                raise FaceProofError(
                    "The public transaction does not contain the expected evidence fingerprint.",
                    "Keep the evidence and transaction receipt for investigation.",
                )
            self._set_step(
                record,
                "verify",
                StepStatus.COMPLETE,
                "The onchain fingerprint matches the reviewed evidence.",
            )
            record.status = RunStatus.VERIFIED
            record.current_step = None
            record.status_message = "Public proof verified."
            self.store.save(record)
            return record
        except FaceProofError as exc:
            return self._fail(run_id, exc)
        except Exception as exc:
            return self._fail(
                run_id,
                FaceProofError(
                    "The blockchain step stopped because of an unexpected internal error.",
                    "Inspect the server log before retrying publication.",
                ),
                internal=exc,
            )

    async def verify_saved(self, run_id: str) -> RunRecord:
        record = self.store.get(run_id)
        if not record.evidence or not record.blockchain:
            raise FaceProofError("This run does not contain a blockchain receipt.")
        manifest = load_manifest(self.store.artifact_path(run_id, "evidence.json"))
        digest = evidence_id(manifest)
        verified = await asyncio.to_thread(
            self._blockchain_client().verify,
            record.blockchain.transaction_hash,
            digest,
        )
        record.blockchain = verified
        record.status = RunStatus.VERIFIED if verified.verification_passed else RunStatus.FAILED
        record.status_message = (
            "Public proof verified."
            if verified.verification_passed
            else "Verification failed because the local evidence fingerprint does not match."
        )
        self.store.save(record)
        return record

    async def _analyze_input(
        self,
        record: RunRecord,
        uploaded_path: Path,
        face_engine: FaceEngine,
    ) -> RunRecord:
        self._start_step(record, "face", "Checking the image and locating every visible face.")
        payload = await asyncio.to_thread(uploaded_path.read_bytes)
        image = await asyncio.to_thread(
            decode_image,
            payload,
            maximum_bytes=self.settings.max_upload_bytes,
        )
        analysis = await asyncio.to_thread(face_engine.analyze, image)
        selected = analysis.selected
        run_dir = self.store.run_dir(record.run_id)

        input_payload = await asyncio.to_thread(write_jpeg, run_dir / "input.jpg", image)
        search_crop = _context_crop(image, selected.box)
        crop_payload = await asyncio.to_thread(write_jpeg, run_dir / "face.jpg", search_crop)
        annotated = await asyncio.to_thread(face_engine.annotate, image, analysis)
        await asyncio.to_thread(write_jpeg, run_dir / "annotated.jpg", annotated)

        warning = None
        if len(analysis.faces) > 1:
            warning = (
                f"{len(analysis.faces)} faces were detected. "
                "The largest face was selected and the others were not searched."
            )
        record.face = FaceSummary(
            faces_detected=len(analysis.faces),
            selected_box=selected.box,
            detection_score=round(selected.score, 6),
            embedding_dimensions=int(selected.embedding.size),
            detector_model=face_engine.detector_name,
            recognizer_model=face_engine.recognizer_name,
            input_sha256=sha256_bytes(input_payload),
            crop_sha256=sha256_bytes(crop_payload),
            input_url=self._artifact_url(record.run_id, "input.jpg"),
            crop_url=self._artifact_url(record.run_id, "face.jpg"),
            annotated_url=self._artifact_url(record.run_id, "annotated.jpg"),
            warning=warning,
        )
        self._set_step(
            record,
            "face",
            StepStatus.COMPLETE,
            f"Encoded the selected face into {selected.embedding.size} dimensions.",
        )
        record.status_message = "Face encoding complete. Starting a fresh visual search."
        self.store.save(record)
        return record

    async def _search_web(self, record: RunRecord, face_engine: FaceEngine) -> RunRecord:
        del face_engine
        self._start_step(
            record,
            "search",
            "Uploading the detected face crop for a fresh Google Lens search.",
        )
        api_key = (
            self.settings.serpapi_api_key.get_secret_value()
            if self.settings.serpapi_api_key
            else ""
        )
        client = SerpApiLensClient(api_key, self.settings.social_domains)
        run_dir = self.store.run_dir(record.run_id)
        face_image = decode_image(
            (run_dir / "face.jpg").read_bytes(),
            maximum_bytes=self.settings.max_upload_bytes,
        )
        full_image = decode_image(
            (run_dir / "input.jpg").read_bytes(),
            maximum_bytes=self.settings.max_upload_bytes,
        )

        search_inputs = (
            ("face_crop", lens_ready_jpeg(face_image)),
            ("full_image", lens_ready_jpeg(full_image)),
        )
        combined: list[SearchCandidate] = []
        candidate_groups: list[list[SearchCandidate]] = []
        seen_urls: set[str] = set()
        for query_kind, search_bytes in search_inputs:
            result = await client.search(search_bytes, query_kind=query_kind)
            record.searches.append(result.trace)
            group: list[SearchCandidate] = []
            for candidate in result.candidates:
                if candidate.post_url not in seen_urls:
                    seen_urls.add(candidate.post_url)
                    group.append(candidate)
            candidate_groups.append(group)
            combined = _interleave_candidates(candidate_groups, self.settings.max_candidates)
            record.candidates = combined
            self.store.save(record)

        if not combined:
            raise NoMatchError(
                "The live search returned no public social media results for this face.",
                "Try a clearer image of a public figure whose photo appears in a public post.",
            )

        record.candidates = combined[: self.settings.max_candidates]
        self._set_step(
            record,
            "search",
            StepStatus.COMPLETE,
            (
                f"Found {len(record.candidates)} distinct public social results "
                "across two live queries."
            ),
        )
        record.status_message = "Social results found. Checking each candidate face locally."
        self.store.save(record)
        return record

    async def _compare_candidates(
        self,
        record: RunRecord,
        face_engine: FaceEngine,
    ) -> RunRecord:
        self._start_step(record, "compare", "Downloading candidate media with strict size limits.")
        reference_image = decode_image(
            self.store.artifact_path(record.run_id, "input.jpg").read_bytes(),
            maximum_bytes=self.settings.max_upload_bytes,
        )
        reference = face_engine.analyze(reference_image).selected.embedding
        semaphore = asyncio.Semaphore(self.settings.candidate_download_concurrency)

        async def retrieve(candidate: SearchCandidate) -> tuple[SearchCandidate, bytes | None]:
            urls = [url for url in (candidate.media_url, candidate.thumbnail_url) if url]
            for url in urls:
                try:
                    async with semaphore:
                        payload, _ = await download_image(
                            url,
                            maximum_bytes=self.settings.max_remote_image_bytes,
                        )
                    candidate.media_url = url
                    return candidate, payload
                except FaceProofError as exc:
                    candidate.evaluation_error = exc.message
            return candidate, None

        retrieved = await asyncio.gather(*(retrieve(item) for item in record.candidates))
        evaluated: list[SearchCandidate] = []
        for index, (candidate, payload) in enumerate(retrieved, start=1):
            if payload is None:
                evaluated.append(candidate)
                continue
            try:
                candidate_image = decode_image(
                    payload,
                    maximum_bytes=self.settings.max_remote_image_bytes,
                )
                candidate_analysis = await asyncio.to_thread(
                    face_engine.analyze,
                    candidate_image,
                    require_face=False,
                )
                candidate.faces_detected = len(candidate_analysis.faces)
                similarity = face_engine.best_similarity(reference, candidate_analysis)
                if similarity is None:
                    candidate.evaluation_error = "No face could be encoded in the candidate image."
                else:
                    filename = f"candidate-{index}.jpg"
                    normalized = encode_jpeg(candidate_image)
                    self.store.artifact_path(record.run_id, filename).write_bytes(normalized)
                    candidate.image_url = self._artifact_url(record.run_id, filename)
                    candidate.image_sha256 = sha256_bytes(normalized)
                    candidate.similarity = round(similarity, 6)
                    candidate.passes_threshold = similarity >= self.settings.face_match_threshold
                    candidate.evaluation_error = None
            except FaceProofError as exc:
                candidate.evaluation_error = exc.message
            evaluated.append(candidate)
            record.candidates = evaluated + [item for item, _ in retrieved[index:]]
            record.status_message = f"Compared {index} of {len(retrieved)} social results."
            self.store.save(record)

        passing = [
            candidate
            for candidate in evaluated
            if candidate.passes_threshold
            and candidate.similarity is not None
            and candidate.image_url
            and candidate.image_sha256
            and candidate.media_url
        ]
        if not passing:
            raise NoMatchError(
                "No social result passed the configured face similarity threshold.",
                (
                    "Review the candidates or try a clearer input image. "
                    "FaceProof will not force a match."
                ),
            )

        passing.sort(
            key=lambda candidate: (
                candidate.similarity or -1.0,
                candidate.exact_match,
                -candidate.position,
            ),
            reverse=True,
        )
        selected = passing[0]
        record.candidates = sorted(
            evaluated,
            key=lambda candidate: (
                candidate.similarity if candidate.similarity is not None else -2.0
            ),
            reverse=True,
        )
        record.selected_match = MatchSummary(
            candidate_id=selected.candidate_id,
            post_url=selected.post_url,
            title=selected.title,
            source=selected.source,
            media_url=selected.media_url or "",
            local_image_url=selected.image_url or "",
            image_sha256=selected.image_sha256 or "",
            similarity=selected.similarity or 0.0,
            threshold=self.settings.face_match_threshold,
            exact_match=selected.exact_match,
            query_kind=selected.query_kind,
        )
        self._set_step(
            record,
            "compare",
            StepStatus.COMPLETE,
            (
                f"Selected the strongest candidate at cosine similarity "
                f"{record.selected_match.similarity:.3f}."
            ),
        )
        record.status_message = "A face match passed the threshold. Preparing evidence."
        self.store.save(record)
        return record

    async def _prepare_evidence(self, record: RunRecord) -> RunRecord:
        if not record.face or not record.selected_match:
            raise FaceProofError("The evidence stage is missing a face or selected social result.")
        self._start_step(
            record,
            "evidence",
            "Writing the selected source and match result into deterministic JSON.",
        )
        manifest = build_manifest(record.face, record.searches, record.selected_match)
        _, _, digest = await asyncio.to_thread(
            write_evidence,
            self.store.run_dir(record.run_id),
            manifest,
        )
        record.evidence = EvidenceSummary(
            evidence_id=digest,
            manifest_url=self._artifact_url(record.run_id, "evidence.json"),
            canonical_url=self._artifact_url(record.run_id, "evidence.canonical.json"),
            created_at=datetime.fromisoformat(manifest.collected_at),
            schema_version=manifest.schema_version,
        )
        self._set_step(
            record,
            "evidence",
            StepStatus.COMPLETE,
            f"Prepared SHA-256 fingerprint {digest[:12]}…{digest[-8:]}.",
        )
        record.status = RunStatus.AWAITING_PUBLISH
        record.current_step = None
        record.status_message = "Evidence ready for review. Publication requires your approval."
        self.store.save(record)
        return record

    def _blockchain_client(self) -> BaseSepoliaClient:
        return BaseSepoliaClient(
            self.settings.base_rpc_url,
            self.settings.base_chain_id,
            self.settings.base_explorer_url,
            self.settings.wallet_file,
        )

    def _start_step(self, record: RunRecord, key: str, detail: str) -> None:
        record.current_step = key
        record.status = RunStatus.RUNNING
        record.status_message = detail
        self._set_step(record, key, StepStatus.RUNNING, detail)
        self.store.save(record)

    @staticmethod
    def _set_step(
        record: RunRecord,
        key: str,
        status: StepStatus,
        detail: str,
    ) -> None:
        step = next(item for item in record.steps if item.key == key)
        step.status = status
        step.detail = detail
        if status == StepStatus.RUNNING and not step.started_at:
            step.started_at = utc_now()
        if status in {StepStatus.COMPLETE, StepStatus.FAILED, StepStatus.SKIPPED}:
            step.completed_at = utc_now()

    def _fail(
        self,
        run_id: str,
        error: FaceProofError,
        *,
        internal: Exception | None = None,
    ) -> RunRecord:
        if internal is not None:
            logger.error("Unexpected FaceProof pipeline failure", exc_info=internal)
        record = self.store.get(run_id)
        record.status = RunStatus.FAILED
        record.status_message = error.message
        record.error = PublicError(code=error.code, message=error.message, recovery=error.recovery)
        if record.current_step:
            self._set_step(record, record.current_step, StepStatus.FAILED, error.message)
        self.store.save(record)
        return record

    @staticmethod
    def _artifact_url(run_id: str, filename: str) -> str:
        return f"/api/runs/{run_id}/files/{filename}"


def _context_crop(image: np.ndarray, box: tuple[int, int, int, int]) -> np.ndarray:
    height, width = image.shape[:2]
    x, y, box_width, box_height = box
    margin_x = int(box_width * 0.35)
    margin_y = int(box_height * 0.45)
    start_x = max(0, x - margin_x)
    start_y = max(0, y - margin_y)
    end_x = min(width, x + box_width + margin_x)
    end_y = min(height, y + box_height + margin_y)
    crop = image[start_y:end_y, start_x:end_x]
    longest = max(crop.shape[:2])
    if longest < 512:
        scale = 512 / longest
        crop = cv2.resize(crop, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    return crop


def _interleave_candidates(
    groups: list[list[SearchCandidate]],
    limit: int,
) -> list[SearchCandidate]:
    """Keep provider order while reserving room for each live query."""

    combined: list[SearchCandidate] = []
    offset = 0
    while len(combined) < limit:
        added = False
        for group in groups:
            if offset < len(group):
                combined.append(group[offset])
                added = True
                if len(combined) == limit:
                    break
        if not added:
            break
        offset += 1
    return combined
