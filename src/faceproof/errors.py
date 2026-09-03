"""Errors that can be shown safely in the command line and web interfaces."""


class FaceProofError(Exception):
    """Base class for expected pipeline failures."""

    code = "faceproof_error"

    def __init__(self, message: str, recovery: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.recovery = recovery


class ConfigurationError(FaceProofError):
    code = "configuration_error"


class ImageValidationError(FaceProofError):
    code = "image_validation_error"


class FaceDetectionError(FaceProofError):
    code = "face_detection_error"


class SearchError(FaceProofError):
    code = "search_error"


class NoMatchError(FaceProofError):
    code = "no_match"


class BlockchainError(FaceProofError):
    code = "blockchain_error"
