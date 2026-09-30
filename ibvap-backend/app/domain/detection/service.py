# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR Component 5 — Detection Domain Service
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4
import asyncio
import random

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.detection.inference_provider import (
    DetectionInferenceProvider,
    InferenceResult,
    create_provider,
)
from app.domain.detection.normalizer import DetectionNormalizer, NormalizedDetection
from app.repositories.detection import DetectionRepository, DetectionConfigRepository
from app.repositories.detection.detection_repository import DetectionRepository as DetectionRepo
from app.models.detection import Detection, DetectionConfig, DetectionSyncState
from app.core.config import settings
from app.core.errors import IBVAPError, IBVAPErrorCode
from app.core.logging import get_logger

logger = get_logger(__name__)


class DetectionService:
    """
    Main orchestration service for detection processing.
    
    Handles:
    - Provider management
    - Frame processing pipeline
    - Normalization
    - Storage
    - Edge sync
    - Event adapter integration
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.detection_repo = DetectionRepository(session)
        self.config_repo = DetectionConfigRepository(session)
        self.normalizer = DetectionNormalizer()
        self._providers: dict[str, DetectionInferenceProvider] = {}
        
        # ─── Bounded Inference Queue with DROP_OLDEST Backpressure ────────────────
        self._inference_queues: dict[str, asyncio.Queue] = {}
        self._queue_workers: dict[str, asyncio.Task] = {}
        self._queue_stats: dict[str, dict] = {}
        
        # Metrics
        self._frames_received = 0
        self._frames_processed = 0
        self._frames_dropped = 0
        self._backpressure_events = 0
    
    # ─────────────────────────────────────────────────────────────────────────
    # Provider Management
    # ─────────────────────────────────────────────────────────────────────────
    
    async def initialize_provider(self, camera_id: str, config: DetectionConfig) -> DetectionInferenceProvider:
        """Initialize and cache a provider for a camera."""
        if camera_id in self._providers:
            return self._providers[camera_id]
        
        provider_config = {
            "model_name": config.model_name,
            "model_version": config.model_version,
            "device": "cuda" if settings.USE_GPU else "cpu",
            "confidence_threshold": config.confidence_threshold,
            "iou_threshold": config.iou_threshold,
            "max_detections": config.max_detections,
        }
        
        provider_type = config.provider.lower()
        provider = await create_provider(provider_type, provider_config)
        await provider.load()
        await provider.warmup()
        
        self._providers[camera_id] = provider
        return provider
    
    async def get_provider(self, camera_id: str) -> DetectionInferenceProvider | None:
        return self._providers.get(camera_id)
    
    async def shutdown_provider(self, camera_id: str) -> None:
        if camera_id in self._providers:
            await self._providers[camera_id].shutdown()
            del self._providers[camera_id]
    
    async def shutdown_all_providers(self) -> None:
        for camera_id in list(self._providers.keys()):
            await self.shutdown_provider(camera_id)
    
    # ─────────────────────────────────────────────────────────────────────────
    # Inference Queue & Backpressure Management
    # ─────────────────────────────────────────────────────────────────────────
    
    def _get_or_create_queue(self, camera_id: str, queue_size_limit: int) -> asyncio.Queue:
        """Get or create inference queue for a camera."""
        if camera_id not in self._inference_queues:
            self._inference_queues[camera_id] = asyncio.Queue(maxsize=queue_size_limit)
            self._queue_stats[camera_id] = {
                "frames_accepted": 0,
                "frames_dropped": 0,
                "backpressure_events": 0,
                "queue_depth_max": 0,
            }
        return self._inference_queues[camera_id]
    
    async def _ensure_queue_worker(self, camera_id: str, config: DetectionConfig):
        """Ensure queue worker is running for camera."""
        if camera_id in self._queue_workers and not self._queue_workers[camera_id].done():
            return
        
        self._queue_workers[camera_id] = asyncio.create_task(
            self._process_queue(camera_id, config)
        )
    
    async def _process_queue(self, camera_id: str, config: DetectionConfig):
        """Background worker that processes frames from the inference queue."""
        queue = self._inference_queues.get(camera_id)
        if not queue:
            return
        
        while True:
            try:
                # Get frame from queue with timeout
                frame_data = await asyncio.wait_for(queue.get(), timeout=1.0)
                
                frame = frame_data["frame"]
                frame_id = frame_data["frame_id"]
                observed_at = frame_data["observed_at"]
                edge_config = frame_data.get("edge_config")
                camera_health_context = frame_data.get("camera_health_context")
                
                # Update queue depth metric
                self._queue_stats[camera_id]["queue_depth_max"] = max(
                    self._queue_stats[camera_id]["queue_depth_max"],
                    queue.qsize()
                )
                
                # Process frame
                try:
                    await self._process_frame_direct(
                        frame, camera_id, frame_id,
                        frame_width=frame_data.get("frame_width", 1280),
                        frame_height=frame_data.get("frame_height", 720),
                        observed_at=observed_at,
                        edge_config=edge_config,
                        camera_health_context=camera_health_context,
                    )
                    self._frames_processed += 1
                except Exception as e:
                    # Log error but continue processing
                    import logging
                    logging.error(f"Frame processing failed for {camera_id}: {e}")
                finally:
                    queue.task_done()
                    
            except asyncio.TimeoutError:
                # No frames in queue, continue waiting
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                import logging
                logging.error(f"Queue worker error for {camera_id}: {e}")
                continue
    
    async def _process_frame_direct(
        self,
        frame: Any,
        camera_id: str,
        frame_id: str,
        frame_width: int,
        frame_height: int,
        observed_at: str | None = None,
        edge_config: dict[str, Any] | None = None,
        camera_health_context: dict[str, Any] | None = None,
    ) -> list[Any]:
        """
        Process a single frame directly (used by queue worker).
        """
        config = await self.config_repo.get_by_camera(camera_id)
        if not config or not config.active:
            raise IBVAPError(
                IBVAPErrorCode.CONFIG_NOT_FOUND,
                f"No active detection config for camera {camera_id}",
            )
        
        provider = await self.initialize_provider(camera_id, config)
        
        # Run inference with timeout protection (same contract as process_frame)
        eff_timeout = getattr(config, "inference_timeout_sec", 10.0)
        try:
            inference_result = await asyncio.wait_for(
                provider.infer(frame, frame_id, camera_id),
                timeout=eff_timeout,
            )
        except asyncio.TimeoutError:
            raise IBVAPError(
                IBVAPErrorCode.INFERENCE_TIMEOUT,
                f"Inference timed out after {eff_timeout}s for camera {camera_id}",
            )
        
        # Prefer explicit frame dimensions (passed by the caller); fall back to
        # the frame shape only when the caller did not provide them.
        shape = getattr(frame, "shape", None)
        eff_frame_width = frame_width if frame_width else (shape[1] if shape is not None and len(shape) > 1 else None)
        eff_frame_height = frame_height if frame_height else (shape[0] if shape is not None and len(shape) > 0 else None)
        
        normalized = self.normalizer.normalize_result(
            inference_result,
            camera_id=camera_id,
            frame_width=eff_frame_width,
            frame_height=eff_frame_height,
            camera_health_context=camera_health_context,
            edge_config=edge_config,
        )
        
        # Apply confidence threshold filtering
        filtered = [
            d for d in normalized
            if d.confidence is None or d.confidence >= config.confidence_threshold
        ]
        
        # Apply sampling
        if config.sample_rate < 1.0:
            import random
            filtered = [d for d in filtered if random.random() < config.sample_rate]
        
        # Apply max detections limit
        if len(filtered) > config.max_detections:
            filtered.sort(key=lambda x: x.confidence or 0, reverse=True)
            filtered = filtered[:config.max_detections]
        
        # Edge idempotency (same contract as process_frame)
        filtered = await self._filter_edge_duplicates(filtered, camera_id, edge_config)
        
        if not filtered:
            return []
        
        # Convert to dict for batch insert
        detection_dicts = []
        for det in filtered:
            def parse_dt(s: str | None) -> datetime | None:
                if not s:
                    return None
                if isinstance(s, str):
                    s = s.replace("Z", "+00:00")
                    dt = datetime.fromisoformat(s)
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    return dt
                return s
            
            det_dict = {
                "detection_id": det.detection_id,
                "camera_id": det.camera_id,
                "frame_id": det.frame_id,
                "event_id": det.event_id,
                "track_id": det.track_id,
                "incident_id": det.incident_id,
                "evidence_id": det.evidence_id,
                "class_name": det.class_name,
                "class_id": det.class_id,
                "provider_class": det.provider_class,
                "confidence": det.confidence,
                "quality_state": det.quality_state,
                "occlusion_state": det.occlusion_state,
                "detection_state": det.detection_state,
                "bbox_x": det.bbox_x,
                "bbox_y": det.bbox_y,
                "bbox_width": det.bbox_width,
                "bbox_height": det.bbox_height,
                "frame_width": det.frame_width,
                "frame_height": det.frame_height,
                "source": det.source,
                "provider": det.provider,
                "model_name": det.model_name,
                "model_version": det.model_version,
                "runtime_version": det.runtime_version,
                "device": det.device,
                "inference_mode": det.inference_mode,
                "postprocess_version": det.postprocess_version,
                "schema_version": det.schema_version,
                "taxonomy_version": det.taxonomy_version,
                "region_profile": det.region_profile,
                "sector_id": det.sector_id,
                "camera_health_state": det.camera_health_state,
                "camera_health_reliability": det.camera_health_reliability,
                "camera_viewpoint_shift": det.camera_viewpoint_shift,
                "camera_health_captured_at": parse_dt(det.camera_health_captured_at),
                "sync_state": det.sync_state,
                "sync_payload_hash": det.sync_payload_hash,
                "edge_device_id": det.edge_device_id,
                "source_event_id": det.source_event_id,
                "source_sequence": det.source_sequence,
                "observed_at": parse_dt(det.observed_at),
                "received_at": parse_dt(det.received_at),
                "processed_at": parse_dt(det.processed_at),
                "inference_latency_ms": det.inference_latency_ms,
                "queue_latency_ms": det.queue_latency_ms,
                "payload_json": det.payload_json,
            }
            detection_dicts.append(det_dict)
        
        if not detection_dicts:
            return []
        
        created = await self.detection_repo.create_batch(detection_dicts)
        await self._create_detection_events(created)
        
        return created

    async def _filter_edge_duplicates(
        self,
        detections: list[NormalizedDetection],
        camera_id: str,
        edge_config: dict[str, Any] | None,
    ) -> list[NormalizedDetection]:
        """
        Drop detections already ingested for the same edge event/payload.

        Shared by both processing paths so edge idempotency is identical
        whether a frame arrives synchronously or through the inference queue.
        """
        if not edge_config:
            return detections
        
        final: list[NormalizedDetection] = []
        for det in detections:
            # Check edge idempotency
            if edge_config.get("source_event_id") and edge_config.get("source_sequence"):
                existing = await self.detection_repo.get_by_source_event(
                    camera_id,
                    edge_config["source_event_id"],
                    edge_config["source_sequence"],
                )
                if existing:
                    # Compare payload hash for content mismatch
                    if edge_config.get("payload_hash") and existing.sync_payload_hash != edge_config["payload_hash"]:
                        raise IBVAPError(
                            IBVAPErrorCode.DETECTION_ID_CONTENT_MISMATCH,
                            f"Detection ID {existing.detection_id} has different payload",
                        )
                    continue  # Skip duplicate
            
            # Check payload hash deduplication
            if edge_config.get("payload_hash"):
                existing = await self.detection_repo.get_by_payload_hash(
                    camera_id, edge_config["payload_hash"]
                )
                if existing:
                    if existing.sync_payload_hash != edge_config["payload_hash"]:
                        raise IBVAPError(
                            IBVAPErrorCode.DETECTION_ID_CONTENT_MISMATCH,
                            f"Detection ID {existing.detection_id} has different payload",
                        )
                    continue
            
            final.append(det)
        
        return final

    async def process_frame(
        self,
        frame: Any,
        camera_id: str,
        frame_id: str,
        frame_width: int,
        frame_height: int,
        observed_at: str | None = None,
        edge_config: dict[str, Any] | None = None,
        camera_health_context: dict[str, Any] | None = None,
        timeout_sec: float | None = None,
    ) -> list[Any]:
        """
        Process a single frame synchronously through the detection pipeline.
        
        Returns list of created Detection ORM objects.
        """
        # Get camera config
        config = await self.config_repo.get_by_camera(camera_id)
        if not config or not config.active:
            raise IBVAPError(
                IBVAPErrorCode.CONFIG_NOT_FOUND,
                f"No active detection config for camera {camera_id}",
            )
        
        # Get or initialize provider
        provider = await self.initialize_provider(camera_id, config)
        
        # Run inference with timeout protection
        eff_timeout = timeout_sec or getattr(config, "inference_timeout_sec", 10.0)
        try:
            inference_result = await asyncio.wait_for(
                provider.infer(frame, frame_id, camera_id),
                timeout=eff_timeout,
            )
        except asyncio.TimeoutError:
            raise IBVAPError(
                IBVAPErrorCode.INFERENCE_TIMEOUT,
                f"Inference timed out after {eff_timeout}s for camera {camera_id}",
            )
        
        # Normalize detections
        normalized = self.normalizer.normalize_result(
            inference_result,
            camera_id=camera_id,
            frame_width=frame_width,
            frame_height=frame_height,
            camera_health_context=camera_health_context,
            edge_config=edge_config,
        )
        
        # Apply confidence threshold filtering
        filtered = [
            d for d in normalized
            if d.confidence is None or d.confidence >= config.confidence_threshold
        ]
        
        # Apply sampling
        if config.sample_rate < 1.0:
            import random
            filtered = [d for d in filtered if random.random() < config.sample_rate]
        
        # Apply max detections limit
        if len(filtered) > config.max_detections:
            filtered.sort(key=lambda x: x.confidence or 0, reverse=True)
            filtered = filtered[:config.max_detections]
        
        # Check for duplicates (edge idempotency)
        final_detections = await self._filter_edge_duplicates(filtered, camera_id, edge_config)
        
        if not final_detections:
            return []
        
        # Convert to dict for batch insert
        detection_dicts = []
        for det in final_detections:
            def parse_dt(s: str | None) -> datetime | None:
                if not s:
                    return None
                if isinstance(s, str):
                    s = s.replace("Z", "+00:00")
                    dt = datetime.fromisoformat(s)
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    return dt
                return s
            
            det_dict = {
                "detection_id": det.detection_id,
                "camera_id": det.camera_id,
                "frame_id": det.frame_id,
                "event_id": det.event_id,
                "track_id": det.track_id,
                "incident_id": det.incident_id,
                "evidence_id": det.evidence_id,
                "class_name": det.class_name,
                "class_id": det.class_id,
                "provider_class": det.provider_class,
                "confidence": det.confidence,
                "quality_state": det.quality_state,
                "occlusion_state": det.occlusion_state,
                "detection_state": det.detection_state,
                "bbox_x": det.bbox_x,
                "bbox_y": det.bbox_y,
                "bbox_width": det.bbox_width,
                "bbox_height": det.bbox_height,
                "frame_width": det.frame_width,
                "frame_height": det.frame_height,
                "source": det.source,
                "provider": det.provider,
                "model_name": det.model_name,
                "model_version": det.model_version,
                "runtime_version": det.runtime_version,
                "device": det.device,
                "inference_mode": det.inference_mode,
                "postprocess_version": det.postprocess_version,
                "schema_version": det.schema_version,
                "taxonomy_version": det.taxonomy_version,
                "region_profile": det.region_profile,
                "sector_id": det.sector_id,
                "camera_health_state": det.camera_health_state,
                "camera_health_reliability": det.camera_health_reliability,
                "camera_viewpoint_shift": det.camera_viewpoint_shift,
                "camera_health_captured_at": parse_dt(det.camera_health_captured_at),
                "sync_state": det.sync_state,
                "sync_payload_hash": det.sync_payload_hash,
                "edge_device_id": det.edge_device_id,
                "source_event_id": det.source_event_id,
                "source_sequence": det.source_sequence,
                "observed_at": parse_dt(det.observed_at),
                "received_at": parse_dt(det.received_at),
                "processed_at": parse_dt(det.processed_at),
                "inference_latency_ms": det.inference_latency_ms,
                "queue_latency_ms": det.queue_latency_ms,
                "payload_json": det.payload_json,
            }
            detection_dicts.append(det_dict)
        
        if not final_detections:
            return []
        
        # Batch insert
        created = await self.detection_repo.create_batch(detection_dicts)
        
        # Create events for eligible detections (Component 4 integration)
        await self._create_detection_events(created)
        
        return created

    async def enqueue_frame(
        self,
        frame: Any,
        camera_id: str,
        frame_id: str,
        frame_width: int,
        frame_height: int,
        observed_at: str | None = None,
        edge_config: dict[str, Any] | None = None,
        camera_health_context: dict[str, Any] | None = None,
    ) -> bool:
        """
        Enqueue a frame for asynchronous inference processing.
        
        Returns True if frame was accepted, False if dropped due to backpressure.
        """
        config = await self.config_repo.get_by_camera(camera_id)
        if not config or not config.active:
            raise IBVAPError(
                IBVAPErrorCode.CONFIG_NOT_FOUND,
                f"No active detection config for camera {camera_id}",
            )
        
        self._frames_received += 1
        
        queue = self._get_or_create_queue(camera_id, config.queue_size_limit)
        
        frame_data = {
            "frame": frame,
            "frame_id": frame_id,
            "frame_width": frame_width,
            "frame_height": frame_height,
            "observed_at": observed_at or datetime.now(timezone.utc).isoformat(),
            "edge_config": edge_config,
            "camera_health_context": camera_health_context,
        }
        
        # Ensure worker is running
        await self._ensure_queue_worker(camera_id, config)
        
        # Try to enqueue with DROP_OLDEST backpressure
        try:
            queue.put_nowait(frame_data)
            self._queue_stats[camera_id]["frames_accepted"] += 1
            return True
        except asyncio.QueueFull:
            # DROP_OLDEST: remove oldest pending frame
            try:
                queue.get_nowait()
                # Balance the queue's unfinished-task count for the dropped
                # frame — it will never be processed and never task_done()'d.
                queue.task_done()
                self._frames_dropped += 1
                self._backpressure_events += 1
                self._queue_stats[camera_id]["frames_dropped"] += 1
                self._queue_stats[camera_id]["backpressure_events"] += 1
            except asyncio.QueueEmpty:
                # Queue was concurrently drained; treat as a plain backpressure event
                self._backpressure_events += 1
                self._queue_stats[camera_id]["backpressure_events"] += 1
            
            # Place the new frame (single producer: space now guaranteed unless
            # the worker re-filled between get and put)
            try:
                queue.put_nowait(frame_data)
                self._queue_stats[camera_id]["frames_accepted"] += 1
                return True
            except asyncio.QueueFull:
                self._frames_dropped += 1
                self._queue_stats[camera_id]["frames_dropped"] += 1
                return False
    
    async def shutdown_camera_queue(self, camera_id: str):
        """Shutdown queue and worker for a camera."""
        if camera_id in self._queue_workers:
            self._queue_workers[camera_id].cancel()
            try:
                await self._queue_workers[camera_id]
            except asyncio.CancelledError:
                pass
            del self._queue_workers[camera_id]
        
        if camera_id in self._inference_queues:
            del self._inference_queues[camera_id]
    
    async def _create_detection_events(self, detections: list[Any]) -> None:
        """
        Create detection-derived events for Component 4 integration.
        
        This is the handoff point from Component 5 to Component 4.
        """
        # This will be implemented when Component 4 event adapter is ready
        # For now, we just ensure the detections have event_id set when they are
        # associated with an event through the event adapter
        pass
    
    # ─────────────────────────────────────────────────────────────────────────
    # Edge Sync
    # ─────────────────────────────────────────────────────────────────────────
    
    async def get_unsynced_detections(self, limit: int = 100) -> list[Any]:
        """Get detections pending sync to central."""
        return await self.detection_repo.get_unsynced(limit)
    
    async def mark_synced(self, detection_ids: list[str], sync_hash: str) -> int:
        return await self.detection_repo.mark_synced(detection_ids, sync_hash)
    
    async def mark_sync_failed(self, detection_ids: list[str]) -> int:
        return await self.detection_repo.mark_sync_failed(detection_ids)
    
    # ─────────────────────────────────────────────────────────────────────────
    # Query / Read
    # ─────────────────────────────────────────────────────────────────────────
    
    async def list_detections(self, **kwargs) -> tuple[list[Any], int]:
        return await self.detection_repo.list_detections(**kwargs)
    
    async def list_camera_detections(self, camera_id: str, **kwargs) -> list[Any]:
        return await self.detection_repo.list_camera_detections(camera_id, **kwargs)
    
    async def get_camera_summary(self, camera_id: str, **kwargs) -> dict[str, Any]:
        return await self.detection_repo.get_camera_summary(camera_id, **kwargs)
    
    async def get_recent(self, **kwargs) -> list[Any]:
        return await self.detection_repo.get_recent(**kwargs)
    
    async def get_detection(self, detection_id: str) -> Any | None:
        return await self.detection_repo.get(detection_id)
    
    async def get_by_event(self, event_id: str) -> list[Any]:
        return await self.detection_repo.get_by_event(event_id)
    
    async def get_by_track(self, track_id: str) -> list[Any]:
        return await self.detection_repo.get_by_track(track_id)
    
    async def get_by_incident(self, incident_id: str) -> list[Any]:
        return await self.detection_repo.get_by_incident(incident_id)
    
    # ─────────────────────────────────────────────────────────────────────────
    # Health / Metrics
    # ─────────────────────────────────────────────────────────────────────────
    
    async def get_provider_health(self, camera_id: str) -> dict[str, Any] | None:
        provider = await self.get_provider(camera_id)
        if not provider:
            # No live provider in this process. Consult the stored config and
            # exercise the actual provider boundary before answering — a config
            # whose provider cannot be loaded reports UNAVAILABLE; it is never
            # silently replaced by demo output.
            config = await self.config_repo.get_by_camera(camera_id)
            if not config:
                return None
            try:
                provider = await self.initialize_provider(camera_id, config)
            except Exception as exc:
                logger.warning("Provider unavailable for camera %s: %s", camera_id, exc)
                return {
                    "camera_id": camera_id,
                    "state": "UNAVAILABLE",
                    "last_successful_inference": None,
                    "recent_failures": 0,
                    "queue_depth": 0,
                    "avg_latency_ms": 0.0,
                    "model_name": config.model_name,
                    "model_version": config.model_version,
                }
        health = await provider.health()
        return {
            "camera_id": camera_id,
            "state": health.state,
            "last_successful_inference": health.last_successful_inference,
            "recent_failures": health.recent_failures,
            "queue_depth": health.queue_depth,
            "avg_latency_ms": health.avg_latency_ms,
            "model_name": health.model_name,
            "model_version": health.model_version,
        }
    
    async def get_all_provider_health(self) -> dict[str, dict[str, Any]]:
        # Live providers plus cameras that have an active detection config —
        # a configured camera must not disappear from the health view just
        # because its provider is not cached in this process.
        camera_ids = set(self._providers.keys())
        for config in await self.config_repo.list_active():
            camera_ids.add(config.camera_id)
        health: dict[str, dict[str, Any]] = {}
        for camera_id in sorted(camera_ids):
            result = await self.get_provider_health(camera_id)
            if result is not None:
                health[camera_id] = result
        return health
    
    async def get_inference_metrics(self, hours: int = 24) -> dict[str, Any]:
        from_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        counts = await self.detection_repo.count_by_camera(from_time=from_time)
        by_class = await self.detection_repo.count_by_class(from_time=from_time)
        
        return {
            "period_hours": hours,
            "total_detections": sum(counts.values()),
            "by_camera": counts,
            "by_class": by_class,
        }


# Module-level service factory
async def create_detection_service(session: AsyncSession) -> DetectionService:
    """Create and initialize a DetectionService."""
    service = DetectionService(session)
    return service