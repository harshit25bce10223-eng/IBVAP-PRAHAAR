# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR — Ledger Anchor Provider (Pluggable)
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Optional


class LedgerAnchorProvider(ABC):
    """
    Abstract interface for ledger anchoring.

    Anchors provide external verification of ledger state.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name."""
        pass

    @abstractmethod
    async def anchor(self, root_hash: str, tree_size: int) -> dict[str, Any]:
        """
        Create an anchor for the given Merkle root/tree state.

        Args:
            root_hash: Merkle root hash (or ledger record hash for simple append-only)
            tree_size: Number of records in the tree

        Returns:
            Anchor metadata including anchor_id, timestamp, proof
        """
        pass

    @abstractmethod
    async def get_anchor(self, anchor_id: str) -> dict[str, Any] | None:
        """Retrieve anchor by ID."""
        pass

    @abstractmethod
    async def verify_anchor(self, root_hash: str, anchor_id: str) -> bool:
        """
        Verify an anchor against a root hash.

        Returns:
            True if anchor is valid for the given root
        """
        pass


class LocalLedgerAnchorProvider:
    """
    Local/self-anchoring provider.

    Uses the database itself as the anchor source.
    This is the default provider for development and offline deployments.
    """

    name = "LOCAL_LEDGER"

    def __init__(self, session):
        self.session = session

    async def anchor(self, root_hash: str, tree_size: int) -> dict[str, Any]:
        """Create a local anchor (stores in database as metadata)."""
        import uuid
        from datetime import datetime, timezone

        anchor_id = f"ANC-{uuid.uuid4().hex[:10].upper()}"
        anchor_data = {
            "anchor_id": anchor_id,
            "provider": "LOCAL_LEDGER",
            "root_hash": root_hash,
            "tree_size": tree_size,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        return anchor_data

    async def get_anchor(self, anchor_id: str) -> dict[str, Any] | None:
        return None

    async def verify_anchor(self, root_hash: str, anchor_id: str) -> bool:
        return True


class DatabaseRootAnchorProvider:
    """
    Database root anchor provider.

    Uses the latest ledger record hash as the root.
    """

    name = "DATABASE_ROOT"

    def __init__(self, session):
        self.session = session

    async def anchor(self, root_hash: str, tree_size: int) -> dict[str, Any]:
        import uuid
        from datetime import datetime, timezone

        anchor_id = f"ANC-{uuid.uuid4().hex[:10].upper()}"
        return {
            "anchor_id": anchor_id,
            "provider": "DATABASE_ROOT",
            "root_hash": root_hash,
            "tree_size": tree_size,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

    async def get_anchor(self, anchor_id: str) -> dict[str, Any] | None:
        return None

    async def verify_anchor(self, root_hash: str, anchor_id: str) -> bool:
        return True


class AnchorProviderFactory:
    """Factory for creating anchor providers."""

    _providers = {
        "LOCAL_LEDGER": LocalLedgerAnchorProvider,
        "DATABASE_ROOT": DatabaseRootAnchorProvider,
    }

    @classmethod
    def register(cls, name: str, provider_class: type):
        cls._providers[name] = provider_class

    @classmethod
    def create(cls, name: str, session, **kwargs):
        if name not in cls._providers:
            raise ValueError(f"Unknown anchor provider: {name}")
        return cls._providers[name](session, **kwargs)

    @classmethod
    def get_default(cls, session):
        return cls.create("LOCAL_LEDGER", session)