from __future__ import annotations

import numpy as np
import pytest

from faceproof.face import DetectedFace, FaceAnalysis, FaceEngine


def _face(embedding: np.ndarray) -> DetectedFace:
    return DetectedFace(
        raw=np.array(
            [5, 5, 20, 20, 8, 9, 18, 9, 13, 14, 9, 20, 17, 20, 0.9],
            dtype=np.float32,
        ),
        box=(5, 5, 20, 20),
        score=0.9,
        crop=np.zeros((20, 20, 3), dtype=np.uint8),
        embedding=embedding,
    )


def test_similarity_and_best_face_selection() -> None:
    reference = np.array([1.0, 0.0], dtype=np.float32)
    analysis = FaceAnalysis(
        faces=(
            _face(np.array([0.0, 1.0], dtype=np.float32)),
            _face(np.array([0.8, 0.6], dtype=np.float32)),
        )
    )

    assert FaceEngine.similarity(reference, reference) == 1.0
    score = FaceEngine.best_similarity(FaceEngine.__new__(FaceEngine), reference, analysis)
    assert score == pytest.approx(0.8)


def test_annotation_does_not_change_source_pixels() -> None:
    source = np.zeros((40, 40, 3), dtype=np.uint8)
    analysis = FaceAnalysis(faces=(_face(np.array([1.0], dtype=np.float32)),))

    annotated = FaceEngine.annotate(source, analysis)

    assert np.count_nonzero(source) == 0
    assert np.count_nonzero(annotated) > 0
