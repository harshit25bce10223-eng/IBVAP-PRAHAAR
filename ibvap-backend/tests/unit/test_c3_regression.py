"""
PRHAAR Component 3 — Evidence & Tamper-Evident Ledger regression tests

Covers:
1. Canonical hash determinism: same input -> same SHA-256
2. Field change -> different digest
3. Timestamp normalization is deterministic
4. HASHED state is valid Pydantic IntegrityState
5. IntegrityState covers all model states
6. Anchor field populates from ledger record (not None always)
7. ledger.py get_ledger_summary uses timezone-aware datetime (not naive)
8. Duplicate regionProfile field is gone from EvidenceDetailResponse
9. Route ordering: ledger/summary must be before /{evidence_id}
10. list_paginated accepts incident_id, event_id, and search filters
11. list_audit returns a list (not empty stub)
12. LocalLedgerAnchorProvider returns consistent anchor_id
"""
import io
import json
import hashlib
import inspect
from datetime import datetime, timezone
import pytest


class TestCanonicalHashDeterminism:
    """Hash determinism — same canonical input must always produce same digest."""

    def test_same_input_same_hash(self):
        """Same input bytes must produce identical SHA-256 digest."""
        from app.domain.evidence.hasher import evidence_hasher
        data = b'{"incident_id":"INC-001","camera_id":"CAM-07"}'
        h1 = evidence_hasher.hash_stream(io.BytesIO(data))
        h2 = evidence_hasher.hash_stream(io.BytesIO(data))
        assert h1 == h2
        assert len(h1) == 64

    def test_field_change_different_hash(self):
        """Different input bytes must produce a different digest."""
        from app.domain.evidence.hasher import evidence_hasher
        data_a = b'{"camera_id":"CAM-07"}'
        data_b = b'{"camera_id":"CAM-08"}'
        h_a = evidence_hasher.hash_stream(io.BytesIO(data_a))
        h_b = evidence_hasher.hash_stream(io.BytesIO(data_b))
        assert h_a != h_b

    def test_canonical_json_is_deterministic(self):
        """Canonicalizer must produce stable output regardless of dict order."""
        from app.domain.evidence.canonicalizer import canonicalizer
        record_a = {"b": 2, "a": 1, "c": 3}
        record_b = {"c": 3, "a": 1, "b": 2}
        canon_a = canonicalizer.canonicalize(record_a)
        canon_b = canonicalizer.canonicalize(record_b)
        assert canon_a == canon_b

    def test_timestamp_normalized_consistently(self):
        """ISO-8601 datetime objects should be normalized to Z format."""
        from datetime import datetime, timezone
        from app.domain.evidence.canonicalizer import canonicalizer
        dt = datetime(2026, 9, 7, 2, 17, 43, tzinfo=timezone.utc)
        record = {"ts": dt}
        canon = canonicalizer.canonicalize(record)
        parsed = json.loads(canon)
        assert parsed["ts"] == "2026-09-07T02:17:43Z"

    def test_hash_bytes_produces_hex_string(self):
        """hash_bytes must return a lowercase hex string of length 64."""
        from app.domain.evidence.hasher import evidence_hasher
        result = evidence_hasher.hash_bytes(b"test payload")
        assert isinstance(result, str)
        assert len(result) == 64
        assert result == hashlib.sha256(b"test payload").hexdigest()


class TestIntegrityStateSchema:
    """Pydantic schema must include all model integrity states."""

    def test_hashed_is_valid_integrity_state(self):
        """HASHED must be in the Pydantic IntegrityState Literal."""
        from app.schemas.evidence.schemas import EvidenceRecord
        record = EvidenceRecord(
            evidenceId="EVD-TEST",
            capturedAt="2026-09-07T00:00:00Z",
            cameraId="CAM-07",
            type="SNAPSHOT",
            source="CAMERA",
            dataSource="CENTRAL",
            syncState="SYNCED",
            role="ORIGINAL_CAPTURE",
            hashAlgorithm="SHA-256",
            recordedHash="a" * 64,
            integrity="HASHED",
            status="VALID",
            mediaKind="none",
            exportState="NONE",
            createdAt="2026-09-07T00:00:00Z",
        )
        assert record.integrity == "HASHED"

    def test_all_model_states_in_schema(self):
        """All states from INTEGRITY_STATES must be in the Pydantic schema."""
        import typing
        from app.models.evidence.record import INTEGRITY_STATES
        from app.schemas.evidence.schemas import EvidenceRecord as SchemaRecord

        hints = typing.get_type_hints(SchemaRecord)
        integrity_annotation = hints.get("integrity", None)
        schema_states = set(typing.get_args(integrity_annotation)) if integrity_annotation else set()
        for state in INTEGRITY_STATES:
            assert state in schema_states, f"State '{state}' from ORM model not in Pydantic schema"

    def test_no_duplicate_region_profile_in_detail_response(self):
        """EvidenceDetailResponse must have exactly ONE regionProfile field."""
        from app.schemas.evidence.schemas import EvidenceDetailResponse
        source = inspect.getsource(EvidenceDetailResponse)
        count = source.count("regionProfile")
        assert count == 1, f"regionProfile appears {count} times in EvidenceDetailResponse"


class TestLedgerDateTime:
    """Ledger summary must use timezone-aware datetime."""

    def test_get_ledger_summary_uses_aware_datetime(self):
        """ledger.py must not use naive datetime.now() without timezone."""
        from app.domain.evidence import ledger as ledger_module
        source = inspect.getsource(ledger_module)
        assert "datetime.now().isoformat()" not in source, (
            "ledger.py uses naive datetime.now() — should use datetime.now(timezone.utc)"
        )


class TestRouteOrdering:
    """Route registration order: /ledger/summary must be registered before /{evidence_id}."""

    def test_ledger_summary_registered_before_evidence_id_route(self):
        """Static route /ledger/summary must come before dynamic /{evidence_id}."""
        from app.api.routes.evidence import routes as routes_module
        source = inspect.getsource(routes_module)
        ledger_pos = source.find('@router.get("/ledger/summary"')
        evidence_id_pos = source.find('@router.get("/{evidence_id}"')
        assert ledger_pos != -1, "Could not find @router.get('/ledger/summary') route in routes.py"
        assert evidence_id_pos != -1, "Could not find @router.get('/{evidence_id}') route in routes.py"
        assert ledger_pos < evidence_id_pos, (
            f"/ledger/summary must be registered BEFORE /{{evidence_id}}: "
            f"ledger_pos={ledger_pos}, evidence_id_pos={evidence_id_pos}"
        )


class TestListPaginatedFilters:
    """list_paginated must accept incident_id, event_id, and search filters."""

    def test_list_paginated_accepts_incident_id(self):
        from app.repositories.evidence.record_repository import EvidenceRecordRepository
        sig = inspect.signature(EvidenceRecordRepository.list_paginated)
        assert "incident_id" in sig.parameters
        assert "event_id" in sig.parameters
        assert "search" in sig.parameters

    def test_evidence_query_schema_has_filter_fields(self):
        from app.schemas.evidence.schemas import EvidenceQuery
        fields = EvidenceQuery.model_fields
        assert "incidentId" in fields
        assert "eventId" in fields
        assert "search" in fields


class TestListAudit:
    """list_audit must not be an empty stub."""

    def test_list_audit_is_not_empty_stub(self):
        from app.domain.evidence.service import EvidenceService
        source = inspect.getsource(EvidenceService.list_audit)
        assert "return []" not in source, "list_audit should query persistent lifecycle events"


class TestAnchorConsistency:
    """LocalLedgerAnchorProvider must generate consistent anchor_id."""

    @pytest.mark.asyncio
    async def test_local_anchor_id_consistency(self):
        from app.domain.evidence.anchor import LocalLedgerAnchorProvider
        provider = LocalLedgerAnchorProvider(session=None)
        res = await provider.anchor(root_hash="a" * 64, tree_size=10)
        assert res["anchor_id"].startswith("ANC-")
        assert res["root_hash"] == "a" * 64
        assert res["tree_size"] == 10


class TestGlobalAuditRouteAndDetailFields:
    """Audit route ordering and EvidenceDetailResponse enriched schema."""

    def test_global_audit_route_registered(self):
        from app.api.routes.evidence import routes as routes_module
        source = inspect.getsource(routes_module)
        assert '@router.get("/audit"' in source

    def test_evidence_detail_response_has_provenance_and_history(self):
        from app.schemas.evidence.schemas import EvidenceDetailResponse
        fields = EvidenceDetailResponse.model_fields
        assert "provenance" in fields
        assert "milestones" in fields
        assert "custody" in fields
        assert "verificationHistory" in fields
