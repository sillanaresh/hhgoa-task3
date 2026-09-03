"""Pinned OpenCV model sources and integrity values."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import httpx

from faceproof.errors import ConfigurationError
from faceproof.utils import sha256_file


@dataclass(frozen=True)
class ModelFile:
    name: str
    filename: str
    url: str
    sha256: str


YUNET = ModelFile(
    name="YuNet 2023 March",
    filename="face_detection_yunet_2023mar.onnx",
    url=(
        "https://github.com/opencv/opencv_zoo/raw/main/models/"
        "face_detection_yunet/face_detection_yunet_2023mar.onnx"
    ),
    sha256="8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4",
)

SFACE = ModelFile(
    name="SFace 2021 December",
    filename="face_recognition_sface_2021dec.onnx",
    url=(
        "https://github.com/opencv/opencv_zoo/raw/main/models/"
        "face_recognition_sface/face_recognition_sface_2021dec.onnx"
    ),
    sha256="0ba9fbfa01b5270c96627c4ef784da859931e02f04419c829e83484087c34e79",
)

MODEL_FILES = (YUNET, SFACE)


def ensure_models(models_dir: Path) -> dict[str, Path]:
    models_dir.mkdir(parents=True, exist_ok=True)
    resolved: dict[str, Path] = {}
    with httpx.Client(follow_redirects=True, timeout=120.0) as client:
        for model in MODEL_FILES:
            destination = models_dir / model.filename
            if destination.exists() and sha256_file(destination) == model.sha256:
                resolved[model.filename] = destination
                continue

            temporary = destination.with_suffix(".download")
            try:
                with client.stream("GET", model.url) as response:
                    response.raise_for_status()
                    with temporary.open("wb") as handle:
                        for chunk in response.iter_bytes(1024 * 1024):
                            handle.write(chunk)
                if sha256_file(temporary) != model.sha256:
                    raise ConfigurationError(
                        f"The downloaded {model.name} file failed its integrity check.",
                        "Delete the model file and run faceproof models again.",
                    )
                os.replace(temporary, destination)
            finally:
                temporary.unlink(missing_ok=True)
            resolved[model.filename] = destination
    return resolved
