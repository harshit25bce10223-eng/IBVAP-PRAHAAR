"""Full API integration flow: zones CRUD + track evaluation + incidents."""
import json


def square(poly: list[tuple[float, float]]) -> list[dict]:
    return [{"x": x, "y": y} for x, y in poly]


def make_zone(client, name="North Restricted Zone", camera_id="CAM-07", polygon=None, rules=None):
    body = {
        "camera_id": camera_id,
        "name": name,
        "polygon": polygon or square([(0.2, 0.2), (0.8, 0.2), (0.8, 0.8), (0.2, 0.8)]),
        "rules": rules or {},
    }
    res = client.post("/api/v1/zones", json=body)
    return res


def track_payload(track_id="TRK-1042", bbox=None, confidence=0.92, is_night=True, **kw):
    base = {
        "track_id": track_id,
        "camera_id": "CAM-07",
        "object_type": "HUMAN",
        "bbox": bbox or {"x": 0.42, "y": 0.35, "width": 0.08, "height": 0.25},
        "confidence": confidence,
        "is_night": is_night,
        "multi_camera_confirmed": True,
        "reliability": "HIGH",
        "timestamp": "2026-09-07T02:17:43Z",
    }
    base.update(kw)
    return base


class TestZoneCRUD:
    def test_create_and_get(self, client):
        r = make_zone(client)
        assert r.status_code == 201
        data = r.json()
        assert "zone_id" in data
        assert data["name"] == "North Restricted Zone"
        assert data["camera_id"] == "CAM-07"
        assert len(data["polygon"]) == 4

        got = client.get(f"/api/v1/zones/{data['zone_id']}")
        assert got.status_code == 200
        assert got.json()["zone_id"] == data["zone_id"]

    def test_list_by_camera(self, client):
        make_zone(client, name="Alpha", camera_id="CAM-07")
        make_zone(client, name="Beta", camera_id="CAM-07")
        make_zone(client, name="Gamma", camera_id="CAM-99")
        zones = client.get("/api/v1/zones", params={"camera_id": "CAM-07"}).json()
        assert [z["name"] for z in zones] == ["Alpha", "Beta"]

    def test_create_rejects_self_intersecting(self, client):
        bowtie = square([(0.2, 0.2), (0.8, 0.6), (0.8, 0.2), (0.2, 0.8)])
        r = make_zone(client, name="Bad", polygon=bowtie)
        assert r.status_code == 400
        body = r.json()
        assert body["error"]["code"] == "INVALID_ZONE_GEOMETRY"
        assert body["error"]["field"] == "polygon"

    def test_create_rejects_degenerate(self, client):
        r = make_zone(client, name="Degenerate", polygon=square([(0.1, 0.4), (0.5, 0.4), (0.9, 0.4)]))
        assert r.status_code == 400

    def test_create_rejects_out_of_range(self, client):
        pts = [{"x": 1.5, "y": 0.1}, {"x": 0.5, "y": 0.5}, {"x": 0.9, "y": 0.1}]
        r = make_zone(client, name="OutOfRange", polygon=pts)
        assert r.status_code == 400

    def test_update_zone_rules(self, client):
        zid = make_zone(client, name="UpdateMe").json()["zone_id"]
        r = client.put(
            f"/api/v1/zones/{zid}",
            json={"rules": {"allowed_object_types": ["VEHICLE"], "active_start": "18:00", "active_end": "06:00"}},
        )
        assert r.status_code == 200
        assert r.json()["rules"]["allowed_object_types"] == ["VEHICLE"]

    def test_update_preserves_fields(self, client):
        zid = make_zone(client, name="Original").json()["zone_id"]
        r = client.put(f"/api/v1/zones/{zid}", json={"name": "Renamed"})
        data = r.json()
        assert data["name"] == "Renamed"
        assert len(data["polygon"]) == 4  # unchanged

    def test_delete(self, client):
        zid = make_zone(client).json()["zone_id"]
        assert client.delete(f"/api/v1/zones/{zid}").status_code == 204
        assert client.get(f"/api/v1/zones/{zid}").status_code == 404

    def test_missing_zone_404(self, client):
        assert client.get("/api/v1/zones/ZONE-DOES-NOT-EXIST").status_code == 404


class TestTrackEvaluation:
    def test_full_flow_creates_incident(self, client):
        make_zone(client)
        r = client.post("/api/v1/evaluation/track_and_evaluate", json=track_payload())
        assert r.status_code == 200
        data = r.json()

        assert data["track"]["track_id"] == "TRK-1042"
        assert data["event"]["created"] is True
        assert data["incident"]["created"] is True
        inc = data["incident"]
        # 25 crossing + 20 night + 15 multi-cam + 15 human + 18 conf = 93 CRITICAL
        assert inc["risk_score"] == 93
        assert inc["severity"] == "CRITICAL"
        assert any(f["code"] == "NIGHT_TIME" for f in inc["factors"])

        zone_eval = data["evaluation"]["zones"][0]
        assert zone_eval["is_inside"] is True
        assert zone_eval["previously_inside"] is False
        assert zone_eval["transition"] == "ENTRY"

    def test_second_frame_same_inside_no_duplicate_incident(self, client):
        make_zone(client)
        p = track_payload()
        first = client.post("/api/v1/evaluation/track_and_evaluate", json=p).json()
        assert first["incident"]["created"] is True

        second = client.post("/api/v1/evaluation/track_and_evaluate", json=p).json()
        assert second["incident"]["created"] is False
        assert second["event"]["created"] is False
        assert second["evaluation"]["zones"][0]["transition"] == "STABLE_INSIDE"

    def test_exit_then_reentry_second_incident(self, client):
        make_zone(client)
        inside = track_payload(bbox={"x": 0.42, "y": 0.35, "width": 0.08, "height": 0.25})
        first = client.post("/api/v1/evaluation/track_and_evaluate", json=inside).json()
        assert first["incident"]["created"] is True

        outside = track_payload(bbox={"x": 0.02, "y": 0.02, "width": 0.05, "height": 0.1})
        exited = client.post("/api/v1/evaluation/track_and_evaluate", json=outside).json()
        assert exited["evaluation"]["zones"][0]["transition"] == "EXIT"
        assert exited["incident"]["created"] is False

        reentered = client.post("/api/v1/evaluation/track_and_evaluate", json=inside).json()
        assert reentered["incident"]["created"] is True
        assert reentered["incident"]["incident_id"] != first["incident"]["incident_id"]

    def test_zone_rule_denies_human(self, client):
        # Zone only allows VEHICLE → a HUMAN crossing must NOT fire.
        make_zone(client, rules={"allowed_object_types": ["VEHICLE", "ANIMAL"]})
        r = client.post("/api/v1/evaluation/track_and_evaluate", json=track_payload())
        data = r.json()
        z = data["evaluation"]["zones"][0]
        assert z["is_inside"] is True
        assert z["rule_passed"] is False
        assert data["incident"]["created"] is False

    def test_inactive_zone_not_evaluated(self, client):
        zid = make_zone(client).json()["zone_id"]
        client.put(f"/api/v1/zones/{zid}", json={"active": False})
        r = client.post("/api/v1/evaluation/track_and_evaluate", json=track_payload())
        data = r.json()
        assert data["incident"]["created"] is False
        zone_eval = data["evaluation"]["zones"][0]
        assert zone_eval["transition"] == "INACTIVE"
        assert zone_eval["is_inside"] is False

    def test_invalid_confidence_422(self, client):
        make_zone(client)
        p = track_payload(confidence=1.7)
        r = client.post("/api/v1/evaluation/track_and_evaluate", json=p)
        assert r.status_code == 422

    def test_invalid_object_type_422(self, client):
        make_zone(client)
        r = client.post(
            "/api/v1/evaluation/track_and_evaluate",
            json=track_payload(object_type="DRONE"),
        )
        assert r.status_code == 422

    def test_invalid_bbox_422(self, client):
        make_zone(client)
        r = client.post(
            "/api/v1/evaluation/track_and_evaluate",
            json=track_payload(bbox={"x": 0.5, "y": 0.5, "width": 0.1}),
        )
        assert r.status_code == 422


class TestMultiZone:
    def test_track_enters_two_zones(self, client):
        make_zone(client, name="Zone A", camera_id="CAM-07", polygon=square([(0.2, 0.2), (0.5, 0.2), (0.5, 0.6), (0.2, 0.6)]))
        make_zone(client, name="Zone B", camera_id="CAM-07", polygon=square([(0.6, 0.2), (0.8, 0.2), (0.8, 0.6), (0.6, 0.6)]))
        # bbox bottom-center → (0.65, 0.40), inside Zone B only.
        p = track_payload(bbox={"x": 0.62, "y": 0.30, "width": 0.06, "height": 0.10})
        r = client.post("/api/v1/evaluation/track_and_evaluate", json=p)
        data = r.json()
        zone_info = {z["zone_name"].split(" ")[1]: z for z in data["evaluation"]["zones"]}
        assert zone_info["A"]["is_inside"] is False
        assert zone_info["B"]["is_inside"] is True
        assert zone_info["B"]["transition"] == "ENTRY"
        assert data["incident"]["created"] is True

    def test_incident_records_zone_name_and_ids(self, client):
        make_zone(client, name="West Perimeter", camera_id="CAM-07")
        p = track_payload()
        data = client.post("/api/v1/evaluation/track_and_evaluate", json=p).json()
        zone_eval = data["evaluation"]["zones"][0]
        assert zone_eval["zone_name"] == "West Perimeter"
        assert "zone_id" in zone_eval
        assert data["track"]["camera_id"] == "CAM-07"


class TestExplainabilityEndpoint:
    def test_incidents_list_factor_breakdown(self, client):
        make_zone(client)
        client.post("/api/v1/evaluation/track_and_evaluate", json=track_payload())
        incidents = client.get("/api/v1/incidents").json()
        assert len(incidents) == 1
        inc = incidents[0]
        assert inc["risk_score"] == 93
        assert inc["severity"] == "CRITICAL"
        assert isinstance(inc["factors"], list)
        factor_codes = [f["code"] for f in inc["factors"]]
        assert factor_codes == [
            "RESTRICTED_ZONE_CROSSING",
            "NIGHT_TIME",
            "MULTI_CAMERA_CONFIRMATION",
            "OBJECT_HUMAN",
            "DETECTION_CONFIDENCE",
        ]
        for f in inc["factors"]:
            assert "evidence" in f

    def test_events_endpoint(self, client):
        make_zone(client)
        client.post("/api/v1/evaluation/track_and_evaluate", json=track_payload())
        events = client.get("/api/v1/events").json()
        assert len(events) == 1
        assert events[0]["event_type"] == "ZONE_ENTRY"

    def test_health(self, client):
        assert client.get("/api/v1/health").json()["status"] == "ok"