"""Component 4 — Correlation Rule Engine Tests."""

from __future__ import annotations

import pytest
from datetime import datetime, timezone

from app.domain.event_correlation.rule_engine import (
    CorrelationRuleEngine,
    CorrelationResult,
    CorrelationCandidate,
    rule_engine,
)


class TestCorrelationRuleEngine:
    """Tests for correlation rule engine."""

    def test_singleton_exists(self):
        """Singleton engine exists."""
        assert rule_engine is not None
        assert isinstance(rule_engine, CorrelationRuleEngine)

    def test_min_correlation_score(self):
        """Minimum correlation score threshold is enforced."""
        assert rule_engine.min_correlation_score == 50

    def test_max_group_duration(self):
        """Maximum group duration is configurable."""
        assert rule_engine.max_group_duration == 300

    def test_config_overrides(self):
        """Configuration can override defaults."""
        custom_engine = CorrelationRuleEngine(config={
            "min_correlation_score": 70,
            "max_group_duration_seconds": 600,
        })
        assert custom_engine.min_correlation_score == 70
        assert custom_engine.max_group_duration == 600


class TestCorrelationResult:
    """Tests for CorrelationResult dataclass."""

    def test_fields(self):
        """Result has required fields."""
        result = CorrelationResult(
            group_id="COR-001",
            status="CORRELATED",
            action="UPDATED",
            revision=2,
            confidence=75,
            completeness="COMPLETE",
            reason="Strong correlation found",
        )
        assert result.group_id == "COR-001"
        assert result.status == "CORRELATED"
        assert result.action == "UPDATED"
        assert result.confidence == 75

    def test_defaults(self):
        """Default values for standalone."""
        result = CorrelationResult()
        assert result.status == "STANDALONE"
        assert result.action == "CREATED"
        assert result.revision == 1
        assert result.completeness == "UNKNOWN"


class TestCorrelationCandidate:
    """Tests for CorrelationCandidate dataclass."""

    def test_creation(self):
        """Create candidate with required fields."""
        c = CorrelationCandidate(
            event_id="e1",
            event_data={"event_id": "e1", "camera_id": "CAM-01"},
        )
        assert c.event_id == "e1"
        assert c.existing_group_id is None
        assert c.compatibility_score == 0

    def test_with_existing_group(self):
        """Candidate can reference existing group."""
        c = CorrelationCandidate(
            event_id="e1",
            event_data={"event_id": "e1"},
            existing_group_id="COR-001",
        )
        assert c.existing_group_id == "COR-001"