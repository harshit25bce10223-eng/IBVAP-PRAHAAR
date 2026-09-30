# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR Component 5 — Detection Normalizer
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.domain.detection.inference_provider import InferenceResult, RawDetection
from app.models.detection import (
    Detection,
    DetectionClass,
    DetectionQuality,
    DetectionOcclusion,
    DetectionState,
    DetectionSource,
    DetectionSyncState,
)


@dataclass
class NormalizedDetection:
    """Canonical detection result after normalization."""
    detection_id: str
    camera_id: str
    class_name: str
    bbox_x: float
    bbox_y: float
    bbox_width: float
    bbox_height: float
    quality_state: str
    occlusion_state: str
    detection_state: str
    source: str
    frame_id: str | None = None
    event_id: str | None = None
    track_id: str | None = None
    incident_id: str | None = None
    evidence_id: str | None = None
    class_id: int | None = None
    taxonomy_version: str | None = None
    provider_class: str | None = None
    confidence: float | None = None
    frame_width: int | None = None
    frame_height: int | None = None
    source: str = "UNKNOWN"
    provider: str | None = None
    model_name: str | None = None
    model_version: str | None = None
    runtime_version: str | None = None
    device: str | None = None
    inference_mode: str | None = None
    postprocess_version: str | None = None
    schema_version: str = "1.0"
    taxonomy_version: str | None = None
    region_profile: str | None = None
    sector_id: str | None = None
    camera_health_state: str | None = None
    camera_health_reliability: str | None = None
    camera_viewpoint_shift: bool | None = None
    camera_health_captured_at: str | None = None
    sync_state: str = "UNKNOWN"
    sync_payload_hash: str | None = None
    edge_device_id: str | None = None
    source_event_id: str | None = None
    source_sequence: int | None = None
    observed_at: str = ""
    received_at: str = ""
    processed_at: str | None = None
    inference_latency_ms: int | None = None
    queue_latency_ms: int | None = None
    payload_json: str | None = None


class BBoxFormat:
    XYXY = "xyxy"
    XYWH = "xywh"
    XYXY_NORM = "xyxy_norm"
    XYWH_NORM = "xywh_norm"


class DetectionNormalizer:
    """
    Normalizes provider-specific detection outputs to canonical Detection format.
    
    Handles:
    - BBox format conversion (xyxy, xywh, normalized, pixel)
    - Class name normalization to canonical taxonomy
    - Confidence validation
    - Quality/occlusion mapping
    - Timestamp normalization
    """
    
    # Canonical taxonomy
    CANONICAL_CLASSES = {
        "PERSON": ["person", "human", "pedestrian", "people"],
        "VEHICLE": ["car", "truck", "bus", "motorcycle", "bicycle", "vehicle", "auto"],
        "ANIMAL": ["dog", "cat", "bird", "cow", "horse", "animal", "wildlife"],
        "OBJECT": ["package", "bag", "box", "object", "item"],
        "UNKNOWN": ["unknown", "other", "unclassified"],
    }
    
    def __init__(
        self,
        taxonomy_version: str = "1.0",
        schema_version: str = "1.0",
        default_confidence_threshold: float = 0.3,
        clip_bbox: bool = True,
    ):
        self.taxonomy_version = taxonomy_version
        self.schema_version = schema_version
        self.default_confidence_threshold = default_confidence_threshold
        self.clip_bbox = clip_bbox
        
        # Build reverse lookup for class normalization
        self._class_map = {}
        for canonical, aliases in self.CANONICAL_CLASSES.items():
            for alias in aliases:
                self._class_map[alias.lower()] = canonical
    
    def normalize_class(self, provider_class: str) -> tuple[str, str | None]:
        """
        Normalize provider class name to canonical taxonomy.
        
        Returns:
            (canonical_class, provider_class)
        """
        normalized = provider_class.strip().lower()
        canonical = self._class_map.get(normalized, "UNKNOWN")
        return canonical, provider_class
    
    def normalize_bbox(
        self,
        bbox: list[float],
        bbox_format: str,
        frame_width: int | None = None,
        frame_height: int | None = None,
    ) -> tuple[float, float, float, float]:
        """
        Convert bbox to normalized xywh format (0-1).
        
        Returns:
            (x, y, width, height) in normalized coordinates
        """
        if len(bbox) != 4:
            raise ValueError(f"BBox must have 4 values, got {len(bbox)}")
        
        # Validate for NaN/Infinity in bbox coordinates
        import math
        for i, val in enumerate(bbox):
            if not isinstance(val, (int, float)):
                raise ValueError(f"BBox coordinate {i} must be numeric, got {type(val).__name__}")
            if math.isnan(val) or math.isinf(val):
                raise ValueError(f"BBox coordinate {i} must be finite, got {val}")
        
        x1, y1, x2, y2 = bbox
        
        if bbox_format == BBoxFormat.XYXY:
            # Pixel coordinates -> normalized
            if frame_width is None or frame_height is None:
                raise ValueError("Frame dimensions required for pixel bbox conversion")
            x = x1 / frame_width
            y = y1 / frame_height
            w = (x2 - x1) / frame_width
            h = (y2 - y1) / frame_height
        elif bbox_format == BBoxFormat.XYWH:
            # Pixel coordinates -> normalized
            if frame_width is None or frame_height is None:
                raise ValueError("Frame dimensions required for pixel bbox conversion")
            x = x1 / frame_width
            y = y1 / frame_height
            w = x2 / frame_width
            h = y2 / frame_height
        elif bbox_format == BBoxFormat.XYXY_NORM:
            # Already normalized
            x = x1
            y = y1
            w = x2 - x1
            h = y2 - y1
        elif bbox_format == BBoxFormat.XYWH_NORM:
            # Already normalized xywh
            x, y, w, h = x1, y1, x2, y2
        else:
            raise ValueError(f"Unknown bbox format: {bbox_format}")
        
        # Validate BEFORE clipping (to catch invalid inputs) - only when clipping is enabled
        if self.clip_bbox:
            if not (0 <= x <= 1 and 0 <= y <= 1 and 0 <= w <= 1 and 0 <= h <= 1):
                raise ValueError(f"Invalid normalized bbox: x={x}, y={y}, w={w}, h={h}")
            
            # Additional check: bbox must not exceed frame boundaries
            if x + w > 1.0 + 1e-6 or y + h > 1.0 + 1e-6:
                raise ValueError(f"BBox extends beyond frame: x+w={x+w:.4f}, y+h={y+h:.4f}")
            
            # Clip if enabled
            x = max(0.0, min(1.0, x))
            y = max(0.0, min(1.0, y))
            w = max(0.0, min(1.0 - x, w))
            h = max(0.0, min(1.0 - y, h))
        
        return x, y, w, h
    
    def normalize_quality(self, quality: str | None) -> str:
        """Map provider quality to canonical quality state."""
        if quality is None:
            return DetectionQuality.UNKNOWN
        q = quality.upper()
        if q in ["GOOD", "HIGH", "EXCELLENT", "CLEAR"]:
            return DetectionQuality.GOOD
        elif q in ["LIMITED", "MEDIUM", "FAIR", "PARTIAL"]:
            return DetectionQuality.LIMITED
        elif q in ["POOR", "LOW", "BAD", "UNCLEAR"]:
            return DetectionQuality.POOR
        return DetectionQuality.UNKNOWN
    
    def normalize_occlusion(self, occlusion: float | str | None) -> str:
        """Map provider occlusion to canonical occlusion state."""
        if occlusion is None:
            return DetectionOcclusion.UNKNOWN
        if isinstance(occlusion, str):
            o = occlusion.upper()
            if o in ["LOW", "NONE", "MINIMAL"]:
                return DetectionOcclusion.LOW
            elif o in ["MEDIUM", "MODERATE", "PARTIAL"]:
                return DetectionOcclusion.MEDIUM
            elif o in ["HIGH", "SEVERE", "HEAVY"]:
                return DetectionOcclusion.HIGH
            return DetectionOcclusion.UNKNOWN
        # Numeric 0-1
        if occlusion <= 0.2:
            return DetectionOcclusion.LOW
        elif occlusion <= 0.5:
            return DetectionOcclusion.MEDIUM
        else:
            return DetectionOcclusion.HIGH
    
    def normalize_state(self, confidence: float | None, quality: str, occlusion: str) -> str:
        """Determine canonical detection state."""
        if confidence is None:
            return DetectionState.UNKNOWN
        if confidence < 0.3:
            return DetectionState.LOW_CONFIDENCE
        if quality in [DetectionQuality.POOR, DetectionQuality.LIMITED]:
            return DetectionState.LOW_CONFIDENCE
        if occlusion in [DetectionOcclusion.HIGH, DetectionOcclusion.MEDIUM]:
            return DetectionState.OCCLUDED
        return DetectionState.DETECTED
    
    def normalize_confidence(self, confidence: float | None) -> float | None:
        """Validate and clamp confidence."""
        if confidence is None:
            return None
        import math
        if math.isnan(confidence) or math.isinf(confidence):
            raise ValueError(f"Confidence must be finite, got {confidence}")
        if confidence < 0 or confidence > 1:
            raise ValueError(f"Confidence must be in [0, 1], got {confidence}")
        return round(confidence, 4)
    
    def normalize_timestamp(self, timestamp: str | None) -> str:
        """
        Ensure timestamp is ISO format with timezone.

        A missing timestamp is stamped with the current time (the detection is
        being observed now). An unparseable timestamp raises instead of being
        silently replaced — a wrong clock value must never be presented as the
        observation time.
        """
        if timestamp is None:
            return datetime.now(timezone.utc).isoformat()
        if isinstance(timestamp, str):
            # Ensure timezone
            if timestamp.endswith("Z"):
                timestamp = timestamp[:-1] + "+00:00"
            # Try parsing
            try:
                dt = datetime.fromisoformat(timestamp)
            except ValueError as exc:
                raise ValueError(f"Unparseable timestamp: {timestamp!r}") from exc
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.isoformat()
        raise ValueError(f"Timestamp must be an ISO string, got {type(timestamp).__name__}")
    
    def compute_payload_hash(self, detection_data: dict[str, Any]) -> str:
        """Compute hash for edge sync idempotency."""
        import hashlib
        import json
        # Use only canonical fields for hash
        canonical_fields = [
            "camera_id", "frame_id", "class_name", "bbox_x", "bbox_y",
            "bbox_width", "bbox_height", "confidence", "observed_at"
        ]
        hash_data = {k: detection_data.get(k) for k in canonical_fields if k in detection_data}
        content = json.dumps(hash_data, sort_keys=True, default=str)
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def normalize_result(
        self,
        result: InferenceResult,
        camera_id: str,
        frame_width: int | None = None,
        frame_height: int | None = None,
        camera_health_context: dict[str, Any] | None = None,
        edge_config: dict[str, Any] | None = None,
    ) -> list[NormalizedDetection]:
        """
        Normalize an entire inference result to canonical detections.
        
        Args:
            result: Raw inference result from provider
            camera_id: Camera identifier
            frame_width: Frame width in pixels (for pixel bbox conversion)
            frame_height: Frame height in pixels
            camera_health_context: Optional camera health snapshot
            edge_config: Optional edge sync configuration
            
        Returns:
            List of normalized detections ready for storage
        """
        if frame_width is None or frame_height is None:
            # Try to get from first detection's frame metadata
            pass
        
        normalized = []
        received_at = datetime.now(timezone.utc).isoformat()
        
        # Determine frame dimensions from frame shape if available
        # This would need to be passed from the frame source
        
        for raw_det in result.detections:
            try:
                # Normalize class
                canonical_class, provider_class = self.normalize_class(raw_det.class_name)
                
                # Normalize bbox
                bbox_x, bbox_y, bbox_w, bbox_h = self.normalize_bbox(
                    raw_det.bbox,
                    raw_det.bbox_format,
                    frame_width,
                    frame_height,
                )
                
                # Normalize confidence
                confidence = self.normalize_confidence(raw_det.confidence)
                
                # Normalize quality and occlusion
                quality = self.normalize_quality(raw_det.quality)
                occlusion = self.normalize_occlusion(raw_det.occlusion)
                
                # Determine detection state
                det_state = self.normalize_state(confidence, quality, occlusion)
                
                # Normalize timestamps
                observed_at = self.normalize_timestamp(result.timestamp)
                processed_at = datetime.now(timezone.utc).isoformat()
                
                # Camera health context
                ch_state = None
                ch_reliability = None
                ch_viewpoint = None
                ch_captured = None
                if camera_health_context:
                    ch_state = camera_health_context.get("state")
                    ch_reliability = camera_health_context.get("reliability")
                    ch_viewpoint = camera_health_context.get("viewpoint_shift")
                    ch_captured = camera_health_context.get("captured_at")
                
                # Edge sync config
                sync_state = DetectionSyncState.UNKNOWN
                sync_hash = None
                edge_device = None
                source_event_id = None
                source_sequence = None
                if edge_config:
                    sync_state = edge_config.get("sync_state", DetectionSyncState.LOCAL_ONLY)
                    sync_hash = edge_config.get("payload_hash")
                    edge_device = edge_config.get("edge_device_id")
                    source_event_id = edge_config.get("source_event_id")
                    source_sequence = edge_config.get("source_sequence")
                
                # Generate detection ID
                detection_id = f"DET-{uuid4().hex[:10].upper()}"
                
                # Build detection dict
                detection = NormalizedDetection(
                    detection_id=detection_id,
                    camera_id=camera_id,
                    frame_id=result.frame_id,
                    class_name=canonical_class,
                    class_id=raw_det.class_id,
                    taxonomy_version=self.taxonomy_version,
                    provider_class=provider_class,
                    confidence=confidence,
                    quality_state=quality,
                    occlusion_state=occlusion,
                    detection_state=det_state,
                    bbox_x=bbox_x,
                    bbox_y=bbox_y,
                    bbox_width=bbox_w,
                    bbox_height=bbox_h,
                    frame_width=frame_width,
                    frame_height=frame_height,
                    source=result.provider.upper() if result.provider else "UNKNOWN",
                    provider=result.provider,
                    model_name=result.model_name,
                    model_version=result.model_version,
                    runtime_version=result.runtime_version,
                    device=result.device,
                    inference_mode="batch" if len(result.detections) > 1 else "single",
                    postprocess_version="1.0",
                    schema_version=self.schema_version,
                    region_profile=None,
                    sector_id=None,
                    camera_health_state=ch_state,
                    camera_health_reliability=ch_reliability,
                    camera_viewpoint_shift=ch_viewpoint,
                    camera_health_captured_at=ch_captured,
                    sync_state=sync_state,
                    sync_payload_hash=sync_hash,
                    edge_device_id=edge_device,
                    source_event_id=source_event_id,
                    source_sequence=source_sequence,
                    observed_at=observed_at,
                    received_at=datetime.now(timezone.utc).isoformat(),
                    processed_at=processed_at,
                    inference_latency_ms=result.inference_latency_ms,
                    queue_latency_ms=None,
                    payload_json=None,
                )
                
                normalized.append(detection)
                
            except Exception as e:
                # Log error and skip invalid detection
                # In production, this should be logged with proper context
                print(f"Failed to normalize detection: {e}")
                continue
        
        return normalized


# Global normalizer instance
default_normalizer = DetectionNormalizer()