# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR Component 4 — Event Correlation Domain
# ─────────────────────────────────────────────────────────────────────────────
from .temporal_engine import temporal_engine, TemporalRelationEngine, TemporalEvent, TemporalRelation
from .spatial_engine import spatial_engine, SpatialRelationEngine, SpatialEvent, SpatialRelation
from .entity_engine import entity_engine, EntityRelationEngine, EntityRelation, ReIDCandidate
from .compatibility import (
    get_compatibility,
    get_event_type_compatibility,
    DEFAULT_COMPATIBILITY_MATRIX,
)
from .rule_engine import (
    CorrelationRuleEngine,
    CorrelationRuleEngine as CorrelationRuleEngineClass,
    CorrelationResult,
    CorrelationCandidate,
    rule_engine,
)
from .group_service import (
    CorrelationService,
    ingest_event,
    get_correlation_group,
    list_correlation_groups,
    CorrelationService,
)
from .group_service import CorrelationService as CorrelationServiceClass

__all__ = [
    "temporal_engine",
    "TemporalRelationEngine",
    "TemporalEvent",
    "TemporalRelation",
    "spatial_engine",
    "SpatialRelationEngine",
    "SpatialEvent",
    "SpatialRelation",
    "entity_engine",
    "EntityRelationEngine",
    "EntityRelation",
    "ReIDCandidate",
    "get_compatibility",
    "get_event_type_compatibility",
    "DEFAULT_COMPATIBILITY_MATRIX",
    "CorrelationRuleEngine",
    "CorrelationResult",
    "CorrelationCandidate",
    "rule_engine",
    "CorrelationService",
    "ingest_event",
    "get_correlation_group",
    "list_correlation_groups",
    "CorrelationService",
]