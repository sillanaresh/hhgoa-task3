from __future__ import annotations

import hashlib
from pathlib import Path

import httpx
import respx

from faceproof.model_files import ModelFile, ensure_models


@respx.mock
def test_model_download_is_pinned_and_reused(tmp_path: Path, monkeypatch) -> None:
    payload = b"pinned model bytes"
    model = ModelFile(
        name="Test model",
        filename="test.onnx",
        url="https://models.example.test/test.onnx",
        sha256=hashlib.sha256(payload).hexdigest(),
    )
    monkeypatch.setattr("faceproof.model_files.MODEL_FILES", (model,))
    route = respx.get(model.url).mock(return_value=httpx.Response(200, content=payload))

    first = ensure_models(tmp_path)
    second = ensure_models(tmp_path)

    assert first[model.filename].read_bytes() == payload
    assert second == first
    assert route.call_count == 1
