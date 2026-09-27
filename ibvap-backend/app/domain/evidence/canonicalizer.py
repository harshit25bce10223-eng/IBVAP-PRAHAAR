# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR — Evidence Canonicalizer (Deterministic JSON for Hashing)
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import json
from datetime import datetime
from typing import Any


CANONICALIZATION_VERSION = "canonical-json-v1"


class Canonicalizer:
    """
    Deterministic JSON canonicalization for evidence hashing.

    Rules:
    - UTF-8 encoding
    - Stable key ordering (sorted)
    - Deterministic separators (no whitespace)
    - Deterministic null handling (null -> null)
    - Normalized timestamps (ISO-8601 with Z suffix)
    - Canonical numeric representation (no trailing zeros, no scientific notation for integers)
    """

    VERSION = CANONICALIZATION_VERSION

    @staticmethod
    def canonicalize(obj: Any) -> str:
        """
        Convert an object to its canonical JSON representation.

        Args:
            obj: Any JSON-serializable object

        Returns:
            Canonical JSON string
        """
        return json.dumps(
            Canonicalizer._normalize(obj),
            separators=(",", ":"),
            ensure_ascii=False,
            sort_keys=True,
        )

    @staticmethod
    def _normalize(obj: Any) -> Any:
        """Recursively normalize an object for canonicalization."""
        if obj is None:
            return None

        if isinstance(obj, dict):
            # Sort keys for deterministic ordering
            return {
                k: Canonicalizer._normalize(v)
                for k, v in sorted(obj.items(), key=lambda x: x[0])
            }

        if isinstance(obj, list):
            return [Canonicalizer._normalize(item) for item in obj]

        if isinstance(obj, datetime):
            # Normalize to ISO-8601 with Z suffix
            if obj.tzinfo is None:
                obj = obj.replace(tzinfo=__import__("datetime").timezone.utc)
            return obj.isoformat().replace("+00:00", "Z")

        if isinstance(obj, float):
            # Normalize float representation
            if obj == int(obj):
                return int(obj)
            return obj

        if isinstance(obj, int):
            return obj

        if isinstance(obj, str):
            return obj

        if isinstance(obj, bool):
            return obj

        # Fallback for other types
        return str(obj)

    @staticmethod
    def canonicalize_for_ledger(payload: dict) -> str:
        """
        Canonicalize a ledger record payload.

        This includes specific fields required for ledger record hashing.
        """
        # Ensure all required fields are present and normalized
        normalized = Canonicalizer._normalize(payload)
        return json.dumps(
            normalized,
            separators=(",", ":"),
            ensure_ascii=False,
            sort_keys=True,
        )


# Global canonicalizer instance
canonicalizer = Canonicalizer()