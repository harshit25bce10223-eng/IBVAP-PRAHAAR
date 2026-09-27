import asyncio
from app.db.database import get_db_session
from app.domain.detection.service import DetectionService
from app.repositories.detection import DetectionConfigRepository, DetectionRepository
from app.models.detection import DetectionConfig, DetectionSource
from app.domain.detection.providers.demo import create_demo_provider
from app.domain.detection.normalizer import DetectionNormalizer
from datetime import datetime, timezone
import numpy as np


async def test_e2e():
    async for session in get_db_session():
        # Get or create config
        config_repo = DetectionConfigRepository(session)
        config = await config_repo.get_by_camera('CAM-07')
        if not config:
            config = await config_repo.create(
                camera_id='CAM-07',
                provider='demo',
                model_name='demo-detector',
                model_version='1.0',
                source=DetectionSource.EDGE,
                confidence_threshold=0.3,
                iou_threshold=0.5,
                max_detections=100,
                sample_rate=1.0,
                min_frame_interval_ms=0,
                nms_enabled=True,
                clip_bbox=True,
                queue_size_limit=50,
                enable_edge_sync=False,
                sync_interval_sec=60,
                active=True,
            )
            await session.commit()

        print(f'Config: {config.config_id}')

        # Initialize demo provider
        provider = await create_demo_provider({
            'model_name': 'demo-detector',
            'model_version': '1.0',
            'device': 'cpu',
            'confidence_threshold': 0.3,
        })

        # Process a frame
        frame = np.zeros((720, 1280, 3), dtype=np.uint8)
        frame_id = 'FRM-TEST-001'

        result = await provider.infer(frame, frame_id, 'CAM-07')
        print(f'Inference result: {len(result.detections)} detections')

        # Normalize
        normalizer = DetectionNormalizer()
        normalized = normalizer.normalize_result(
            result,
            camera_id='CAM-07',
            frame_width=1280,
            frame_height=720,
        )
        print(f'Normalized: {len(normalized)} detections')
        for d in normalized:
            print(f'  {d.detection_id}: {d.class_name} conf={d.confidence} bbox=({d.bbox_x:.2f},{d.bbox_y:.2f},{d.bbox_width:.2f},{d.bbox_height:.2f})')

        # Store detections
        service = DetectionService(session)
        service._providers['CAM-07'] = provider
        service.normalizer = normalizer

        created = await service.process_frame(
            frame=frame,
            camera_id='CAM-07',
            frame_id=frame_id,
            frame_width=1280,
            frame_height=720,
            observed_at=datetime.now(timezone.utc).isoformat(),
        )
        print(f'Created {len(created)} detections in DB')
        for d in created:
            print(f'  DB: {d.detection_id}')

        # Get detections from DB
        repo = DetectionRepository(session)
        dets, total = await repo.list_detections(camera_id='CAM-07', limit=10)
        print(f'DB query: {total} total, {len(dets)} returned')

        # Now test the event adapter - create a detection event for Component 4
        for d in created:
            # This is the handoff point to Component 4
            event_data = {
                'event_id': 'EVT-' + d.detection_id[4:],
                'event_type': 'DETECTION',
                'camera_id': d.camera_id,
                'zone_id': 'ZONE-A',
                'sector_id': 'SEC-1',
                'track_id': 'TRK-001',
                'event_time': d.observed_at,
                'source': 'DETECTION_ENGINE',
                'object_type': d.class_name,
                'confidence': d.confidence,
                'is_night': False,
                'multi_camera_confirmed': False,
                'reliability': 'HIGH',
                'reid_candidate': None,
                'payload': {
                    'detection_id': d.detection_id,
                    'class_name': d.class_name,
                    'confidence': d.confidence,
                    'bbox': [d.bbox_x, d.bbox_y, d.bbox_width, d.bbox_height],
                }
            }
            event_id = event_data['event_id']
            print('Event for Component 4: ' + event_id)

            # Ingest into Component 4
            from app.domain.event_correlation import ingest_event
            corr_result = await ingest_event(session, event_data, 'DETECTION_ENGINE')
            print('Component 4 result: ' + str(corr_result))

asyncio.run(test_e2e())