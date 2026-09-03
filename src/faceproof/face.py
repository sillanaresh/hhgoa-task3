"""Local face detection and SFace embedding comparison."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from faceproof.errors import FaceDetectionError
from faceproof.model_files import SFACE, YUNET, ensure_models


@dataclass(frozen=True)
class DetectedFace:
    raw: np.ndarray
    box: tuple[int, int, int, int]
    score: float
    crop: np.ndarray
    embedding: np.ndarray


@dataclass(frozen=True)
class FaceAnalysis:
    faces: tuple[DetectedFace, ...]

    @property
    def selected(self) -> DetectedFace:
        return self.faces[0]


class FaceEngine:
    detector_name = YUNET.name
    recognizer_name = SFACE.name

    def __init__(self, models_dir: Path, score_threshold: float = 0.80) -> None:
        paths = ensure_models(models_dir)
        self.detector = cv2.FaceDetectorYN.create(
            str(paths[YUNET.filename]),
            "",
            (320, 320),
            score_threshold,
            0.3,
            5000,
        )
        self.recognizer = cv2.FaceRecognizerSF.create(str(paths[SFACE.filename]), "")

    def analyze(self, image: np.ndarray, *, require_face: bool = True) -> FaceAnalysis:
        if image.ndim != 3 or image.shape[2] != 3:
            raise FaceDetectionError("The face model requires a three channel color image.")

        height, width = image.shape[:2]
        self.detector.setInputSize((width, height))
        _, detected = self.detector.detect(image)
        if detected is None or len(detected) == 0:
            if require_face:
                raise FaceDetectionError(
                    "No clear face was detected in the image.",
                    "Use a front facing photo with one unobstructed face and even lighting.",
                )
            return FaceAnalysis(faces=())

        results: list[DetectedFace] = []
        for raw_face in detected:
            x, y, box_width, box_height = (round(value) for value in raw_face[:4])
            if box_width < 24 or box_height < 24:
                continue
            try:
                aligned = self.recognizer.alignCrop(image, raw_face)
                feature = self.recognizer.feature(aligned).reshape(-1).astype(np.float32)
            except cv2.error:
                continue
            norm = float(np.linalg.norm(feature))
            if norm == 0:
                continue
            results.append(
                DetectedFace(
                    raw=raw_face.copy(),
                    box=(max(0, x), max(0, y), box_width, box_height),
                    score=float(raw_face[-1]),
                    crop=aligned,
                    embedding=feature / norm,
                )
            )

        if not results:
            if require_face:
                raise FaceDetectionError(
                    "A face was detected but could not be encoded.",
                    "Use a sharper image where both eyes and the full face are visible.",
                )
            return FaceAnalysis(faces=())

        results.sort(key=lambda face: face.box[2] * face.box[3], reverse=True)
        return FaceAnalysis(faces=tuple(results))

    @staticmethod
    def similarity(first: np.ndarray, second: np.ndarray) -> float:
        return float(np.clip(np.dot(first, second), -1.0, 1.0))

    def best_similarity(self, reference: np.ndarray, analysis: FaceAnalysis) -> float | None:
        if not analysis.faces:
            return None
        return max(self.similarity(reference, face.embedding) for face in analysis.faces)

    @staticmethod
    def annotate(image: np.ndarray, analysis: FaceAnalysis) -> np.ndarray:
        annotated = image.copy()
        for index, face in enumerate(analysis.faces):
            x, y, width, height = face.box
            color = (102, 92, 27) if index == 0 else (126, 126, 126)
            cv2.rectangle(annotated, (x, y), (x + width, y + height), color, 3)
            for point_index in range(5):
                point_x = round(face.raw[4 + point_index * 2])
                point_y = round(face.raw[5 + point_index * 2])
                cv2.circle(annotated, (point_x, point_y), 2, color, -1)
        return annotated
