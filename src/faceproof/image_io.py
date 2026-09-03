"""Image validation, normalization, and bounded remote retrieval."""

from __future__ import annotations

import io
import ipaddress
import socket
from pathlib import Path
from urllib.parse import urlparse

import cv2
import httpx
import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError

from faceproof.errors import ImageValidationError

ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}
ALLOWED_MEDIA_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_IMAGE_PIXELS = 40_000_000


def decode_image(payload: bytes, *, maximum_bytes: int) -> np.ndarray:
    if not payload:
        raise ImageValidationError("The image file is empty.", "Choose a JPEG, PNG, or WebP image.")
    if len(payload) > maximum_bytes:
        raise ImageValidationError(
            f"The image is larger than the {maximum_bytes // (1024 * 1024)} MB limit.",
            "Choose a smaller JPEG, PNG, or WebP image.",
        )

    Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS
    try:
        with Image.open(io.BytesIO(payload)) as source:
            if source.format not in ALLOWED_FORMATS:
                raise ImageValidationError(
                    f"{source.format or 'This format'} is not supported.",
                    "Convert the image to JPEG, PNG, or WebP.",
                )
            source.load()
            corrected = ImageOps.exif_transpose(source).convert("RGB")
            if corrected.width * corrected.height > MAX_IMAGE_PIXELS:
                raise ImageValidationError(
                    "The image has too many pixels to process safely.",
                    "Resize the image so it contains fewer than 40 million pixels.",
                )
            rgb = np.asarray(corrected)
    except ImageValidationError:
        raise
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise ImageValidationError(
            "The file could not be decoded as an image.",
            "Choose an unmodified JPEG, PNG, or WebP file.",
        ) from exc

    return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)


def encode_jpeg(image: np.ndarray, quality: int = 92) -> bytes:
    success, encoded = cv2.imencode(
        ".jpg",
        image,
        [int(cv2.IMWRITE_JPEG_QUALITY), quality, int(cv2.IMWRITE_JPEG_OPTIMIZE), 1],
    )
    if not success:
        raise ImageValidationError("The processed image could not be encoded.")
    return encoded.tobytes()


def write_jpeg(path: Path, image: np.ndarray, quality: int = 92) -> bytes:
    payload = encode_jpeg(image, quality)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return payload


def lens_ready_jpeg(image: np.ndarray, maximum_bytes: int = 490_000) -> bytes:
    """Fit a local image below SerpApi's 500 KB upload limit."""

    working = image
    longest = max(working.shape[:2])
    if longest > 1600:
        scale = 1600 / longest
        working = cv2.resize(working, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)

    for quality in (92, 86, 80, 72, 64, 56):
        payload = encode_jpeg(working, quality)
        if len(payload) <= maximum_bytes:
            return payload

    scale = (maximum_bytes / len(payload)) ** 0.5 * 0.92
    working = cv2.resize(working, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    payload = encode_jpeg(working, 70)
    if len(payload) > maximum_bytes:
        raise ImageValidationError(
            "The face crop could not be prepared for the search service.",
            "Use an image with less background detail.",
        )
    return payload


def ensure_public_http_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ImageValidationError("A search result returned an invalid image URL.")
    if parsed.username or parsed.password:
        raise ImageValidationError("A search result returned an unsafe image URL.")

    try:
        default_port = 443 if parsed.scheme == "https" else 80
        addresses = socket.getaddrinfo(
            parsed.hostname,
            parsed.port or default_port,
            type=socket.SOCK_STREAM,
        )
    except socket.gaierror as exc:
        raise ImageValidationError("A search result image host could not be resolved.") from exc

    for address in addresses:
        ip = ipaddress.ip_address(address[4][0])
        if not ip.is_global:
            raise ImageValidationError("A search result pointed to a private network address.")
    return url


async def download_image(url: str, *, maximum_bytes: int) -> tuple[bytes, str]:
    ensure_public_http_url(url)
    headers = {
        "User-Agent": "FaceProof/0.1 (+https://github.com/sillanaresh/hhgoa-task3)",
        "Accept": "image/avif,image/webp,image/png,image/jpeg,*/*;q=0.5",
    }
    try:
        async with (
            httpx.AsyncClient(
                follow_redirects=True,
                timeout=20.0,
                headers=headers,
            ) as client,
            client.stream("GET", url) as response,
        ):
            response.raise_for_status()
            ensure_public_http_url(str(response.url))
            media_type = response.headers.get("content-type", "").split(";", 1)[0].lower()
            if media_type and media_type not in ALLOWED_MEDIA_TYPES:
                raise ImageValidationError("A search result URL did not return a supported image.")
            declared_size = int(response.headers.get("content-length", "0") or 0)
            if declared_size > maximum_bytes:
                raise ImageValidationError("A search result image exceeded the download limit.")
            chunks: list[bytes] = []
            size = 0
            async for chunk in response.aiter_bytes():
                size += len(chunk)
                if size > maximum_bytes:
                    raise ImageValidationError("A search result image exceeded the download limit.")
                chunks.append(chunk)
    except ImageValidationError:
        raise
    except httpx.HTTPError as exc:
        raise ImageValidationError("A search result image could not be downloaded.") from exc

    payload = b"".join(chunks)
    decode_image(payload, maximum_bytes=maximum_bytes)
    return payload, media_type or "image/jpeg"
