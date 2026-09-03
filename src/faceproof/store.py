"""Durable per-run state stored outside Git."""

from __future__ import annotations

import threading
import uuid
from pathlib import Path

from faceproof.domain import RunRecord, RunStatus, initial_steps
from faceproof.utils import atomic_write_json, utc_now


class RunStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self.root.chmod(0o700)
        self._lock = threading.RLock()

    def create(self, original_filename: str) -> RunRecord:
        now = utc_now()
        record = RunRecord(
            run_id=uuid.uuid4().hex,
            status=RunStatus.CREATED,
            status_message="Image received. The pipeline has not started yet.",
            created_at=now,
            updated_at=now,
            original_filename=original_filename,
            steps=initial_steps(),
        )
        self.save(record)
        return record

    def run_dir(self, run_id: str) -> Path:
        uuid.UUID(hex=run_id)
        path = (self.root / run_id).resolve()
        if self.root.resolve() not in path.parents:
            raise ValueError("Invalid run identifier")
        return path

    def state_path(self, run_id: str) -> Path:
        return self.run_dir(run_id) / "state.json"

    def get(self, run_id: str) -> RunRecord:
        with self._lock:
            return RunRecord.model_validate_json(self.state_path(run_id).read_text("utf-8"))

    def save(self, record: RunRecord) -> None:
        with self._lock:
            record.updated_at = utc_now()
            run_dir = self.run_dir(record.run_id)
            run_dir.mkdir(parents=True, exist_ok=True)
            run_dir.chmod(0o700)
            atomic_write_json(
                run_dir / "state.json",
                record.model_dump(mode="json", exclude_none=True),
            )

    def artifact_path(self, run_id: str, name: str) -> Path:
        if not name or Path(name).name != name:
            raise ValueError("Invalid artifact name")
        return self.run_dir(run_id) / name
