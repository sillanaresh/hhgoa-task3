from __future__ import annotations

import io

import cv2
import numpy as np
import pytest
from PIL import Image

from faceproof.errors import ImageValidationError
from faceproof.image_io import decode_image, ensure_public_http_url, lens_ready_jpeg


def _jpeg(width: int = 120, height: int = 80) -> bytes:
    image = Image.new("RGB", (width, height), (54, 112, 118))
    output = io.BytesIO()
    image.save(output, format="JPEG", quality=92)
    return output.getvalue()


def test_decode_normalizes_supported_image() -> None:
    decoded = decode_image(_jpeg(), maximum_bytes=1_000_000)

    assert decoded.shape == (80, 120, 3)
    assert decoded.dtype == np.uint8


def test_decode_rejects_invalid_and_oversized_files() -> None:
    with pytest.raises(ImageValidationError):
        decode_image(b"not an image", maximum_bytes=1_000_000)
    with pytest.raises(ImageValidationError):
        decode_image(_jpeg(), maximum_bytes=10)


def test_lens_encoding_stays_below_upload_limit() -> None:
    source = np.random.default_rng(7).integers(0, 256, (1400, 1800, 3), dtype=np.uint8)
    payload = lens_ready_jpeg(source, maximum_bytes=490_000)
    decoded = cv2.imdecode(np.frombuffer(payload, np.uint8), cv2.IMREAD_COLOR)

    assert len(payload) <= 490_000
    assert decoded is not None


def test_remote_image_guard_rejects_private_networks() -> None:
    with pytest.raises(ImageValidationError):
        ensure_public_http_url("http://127.0.0.1/private.jpg")
    with pytest.raises(ImageValidationError):
        ensure_public_http_url("file:///etc/passwd")
