# ─────────────────────────────────────────────────────────────────────────────
# IBVAP Backend — Structured Error Types
# ─────────────────────────────────────────────────────────────────────────────
from enum import Enum
from fastapi import HTTPException


class IBVAPErrorCode(str, Enum):
    INVALID_ZONE_GEOMETRY   = "INVALID_ZONE_GEOMETRY"
    INVALID_BBOX             = "INVALID_BBOX"
    INVALID_CONFIDENCE       = "INVALID_CONFIDENCE"
    INVALID_OBJECT_TYPE      = "INVALID_OBJECT_TYPE"
    ZONE_NOT_FOUND           = "ZONE_NOT_FOUND"
    CAMERA_NOT_FOUND         = "CAMERA_NOT_FOUND"
    INVALID_TIMESTAMP        = "INVALID_TIMESTAMP"
    DATABASE_ERROR           = "DATABASE_ERROR"
    DUPLICATE_ENTRY          = "DUPLICATE_ENTRY"
    INVALID_RELIABILITY      = "INVALID_RELIABILITY"
    INTERNAL_ERROR           = "INTERNAL_ERROR"
    CONFIG_NOT_FOUND         = "CONFIG_NOT_FOUND"
    DETECTION_ID_CONTENT_MISMATCH = "DETECTION_ID_CONTENT_MISMATCH"
    INFERENCE_TIMEOUT        = "INFERENCE_TIMEOUT"
    # Component 6 — Tracking Engine
    TRACK_NOT_FOUND          = "TRACK_NOT_FOUND"
    TRACKING_UNAVAILABLE     = "TRACKING_UNAVAILABLE"
    PROVIDER_TIMEOUT         = "PROVIDER_TIMEOUT"
    PROVIDER_ERROR           = "PROVIDER_ERROR"
    INVALID_TRACK            = "INVALID_TRACK"
    REVISION_CONFLICT        = "REVISION_CONFLICT"


class IBVAPError(Exception):
    """Base domain error. Never leaks internals to HTTP clients."""

    def __init__(
        self,
        code: IBVAPErrorCode,
        message: str,
        field: str | None = None,
        status_code: int = 400,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.field = field
        self.status_code = status_code

    def to_dict(self) -> dict:
        payload: dict = {"code": self.code.value, "message": self.message}
        if self.field:
            payload["field"] = self.field
        return {"error": payload}


class ZoneGeometryError(IBVAPError):
    def __init__(self, message: str, field: str = "polygon") -> None:
        super().__init__(IBVAPErrorCode.INVALID_ZONE_GEOMETRY, message, field)


class ZoneNotFoundError(IBVAPError):
    def __init__(self, zone_id: str) -> None:
        super().__init__(
            IBVAPErrorCode.ZONE_NOT_FOUND,
            f"Zone '{zone_id}' not found.",
            status_code=404,
        )


class IncidentNotFoundError(IBVAPError):
    def __init__(self, incident_id: str) -> None:
        super().__init__(
            IBVAPErrorCode.INTERNAL_ERROR,
            f"Incident '{incident_id}' not found.",
            status_code=404,
        )


class InvalidConfidenceError(IBVAPError):
    def __init__(self, value: float) -> None:
        super().__init__(
            IBVAPErrorCode.INVALID_CONFIDENCE,
            f"Confidence must be between 0.0 and 1.0, got: {value}",
            field="confidence",
        )


class InvalidObjectTypeError(IBVAPError):
    def __init__(self, value: str) -> None:
        super().__init__(
            IBVAPErrorCode.INVALID_OBJECT_TYPE,
            f"Unknown object type '{value}'. Allowed: HUMAN, VEHICLE, ANIMAL.",
            field="object_type",
        )


class InvalidBBoxError(IBVAPError):
    def __init__(self, message: str) -> None:
        super().__init__(IBVAPErrorCode.INVALID_BBOX, message, field="bbox")


class DatabaseError(IBVAPError):
    def __init__(self, message: str = "A database error occurred.") -> None:
        super().__init__(IBVAPErrorCode.DATABASE_ERROR, message, status_code=500)


def ibvap_error_to_http(err: IBVAPError) -> HTTPException:
    return HTTPException(status_code=err.status_code, detail=err.to_dict())
