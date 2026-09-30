# PRHAAR C2 probe — F3: verify CameraHealthInput.image/viewpoint never reach
# the state engine even when frames are analyzed.
#
# Method: monkeypatch CameraHealthStateEngine.derive_state on the live
# analyzer class to capture the CameraHealthInput it actually receives, then
# feed a real frame sequence through the public analyze_observation path
# (the same path the live API route
# app/api/routes/camera_health/routes.py:513 uses).
#
# §125: locked code untouched — this probe only wraps a method at runtime;
# the process exits immediately after.
import sys
from datetime import datetime, timedelta

import numpy as np

sys.path.insert(0, r"C:\SIH\ibvap-backend")
BASE = r"C:\SIH\ml\c2_camera_health\benchmark"
sys.path.insert(0, BASE)

from app.domain.camera_health.analyzer import (  # noqa: E402
    CameraHealthAnalyzer,
    CameraHealthStateEngine,
)
from app.domain.camera_health.state_engine import StreamHealthMetrics  # noqa: E402
from gen_c2_corpus import build_samples, materialize_frames  # noqa: E402
from run_c2_benchmark import CONFIG  # noqa: E402

captured = {}
original = CameraHealthStateEngine.derive_state


def spy(self, input_data):
    captured["image"] = input_data.image
    captured["viewpoint"] = input_data.viewpoint
    captured["stream"] = input_data.stream
    return original(self, input_data)


CameraHealthStateEngine.derive_state = spy

sample = next(s for s in build_samples() if s.cls == "ONLINE")
frames = materialize_frames(sample)
assert frames, "ONLINE sample must materialize frames"

analyzer = CameraHealthAnalyzer()
base_ts = datetime.now().replace(microsecond=0)
try:
    for i, f in enumerate(frames):
        analyzer.analyze_observation(
            camera_id="CAM-PROBE-F3", config=CONFIG,
            source_timestamp=base_ts + timedelta(seconds=float(i)),
            received_at=base_ts + timedelta(seconds=float(i)),
            stream=StreamHealthMetrics(
                connected=True, observed_fps=25.0, frame_drop_rate=0.0
            ),
            frame=f,
        )
except Exception as exc:  # expected: locked-code crash (KeyError 'reason')
    captured["exception"] = f"{type(exc).__name__}: {exc}"

print("frames fed          :", len(frames), "first frame shape", frames[0].shape)
print("captured stream     :", type(captured.get("stream")).__name__)
print("captured image      :", captured.get("image"))
print("captured viewpoint  :", captured.get("viewpoint"))
print("engine exception    :", captured.get("exception"))

ok = (
    captured.get("stream") is not None
    and captured.get("image") is None
    and captured.get("viewpoint") is None
)
print("F3 VERIFIED         :", ok)
sys.exit(0 if ok else 1)
