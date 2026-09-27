# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR — Evidence Storage Abstraction
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import os
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import BinaryIO, Optional
from pathlib import Path


@dataclass
class StorageMetadata:
    """Metadata about stored evidence."""
    storage_key: str
    storage_backend: str
    file_size_bytes: int
    mime_type: Optional[str] = None
    created_at: Optional[datetime] = None


class EvidenceStorage(ABC):
    """
    Abstract evidence storage interface.

    Implementations can use local filesystem, S3, MinIO, etc.
    """

    @abstractmethod
    def put(self, evidence_id: str, stream: BinaryIO, mime_type: Optional[str] = None) -> StorageMetadata:
        """
        Store evidence content.

        Args:
            evidence_id: Unique evidence identifier
            stream: Content stream
            mime_type: Optional MIME type

        Returns:
            Storage metadata including storage key
        """
        pass

    @abstractmethod
    def get(self, storage_key: str) -> BinaryIO:
        """
        Retrieve evidence content as a stream.

        Args:
            storage_key: Storage key returned from put()

        Returns:
            Binary stream of content
        """
        pass

    @abstractmethod
    def exists(self, storage_key: str) -> bool:
        """Check if evidence exists in storage."""
        pass

    @abstractmethod
    def metadata(self, storage_key: str) -> Optional[StorageMetadata]:
        """Get storage metadata."""
        pass

    @abstractmethod
    def delete(self, storage_key: str) -> bool:
        """Delete evidence from storage (use with caution)."""
        pass


class FilesystemEvidenceStorage(EvidenceStorage):
    """
    Local filesystem evidence storage.

    Uses a configured base directory with evidence_id-based storage keys.
    """

    def __init__(self, base_path: str = "./evidence_storage"):
        self.base_path = Path(base_path).resolve()
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _generate_storage_key(self, evidence_id: str) -> str:
        """Generate a safe storage key from evidence_id."""
        # Use UUID-based path to avoid filesystem issues
        safe_id = evidence_id.replace(":", "_").replace("/", "_")
        return f"{safe_id[:2]}/{safe_id}"

    def put(self, evidence_id: str, stream, mime_type: Optional[str] = None) -> StorageMetadata:
        storage_key = self._generate_storage_key(evidence_id)
        full_path = self.base_path / storage_key
        full_path.parent.mkdir(parents=True, exist_ok=True)

        file_size = 0
        with open(full_path, "wb") as f:
            while True:
                chunk = stream.read(64 * 1024)
                if not chunk:
                    break
                f.write(chunk)
                file_size += len(chunk)

        return StorageMetadata(
            storage_key=storage_key,
            storage_backend="filesystem",
            file_size_bytes=file_size,
            mime_type=mime_type,
            created_at=datetime.now(),
        )

    def get(self, storage_key: str) -> BinaryIO:
        full_path = self.base_path / storage_key
        if not full_path.exists():
            raise FileNotFoundError(f"Evidence not found: {storage_key}")
        return open(full_path, "rb")

    def exists(self, storage_key: str) -> bool:
        full_path = self.base_path / storage_key
        return full_path.exists()

    def metadata(self, storage_key: str) -> Optional[StorageMetadata]:
        full_path = self.base_path / storage_key
        if not full_path.exists():
            return None
        stat = full_path.stat()
        return StorageMetadata(
            storage_key=storage_key,
            storage_backend="filesystem",
            file_size_bytes=stat.st_size,
            created_at=datetime.fromtimestamp(stat.st_ctime),
        )

    def delete(self, storage_key: str) -> bool:
        full_path = self.base_path / storage_key
        if not full_path.exists():
            return False
        full_path.unlink()
        # Clean up empty parent directories
        try:
            full_path.parent.rmdir()
        except OSError:
            pass
        return True


# Global storage instance (can be replaced with S3/MinIO in production)
def create_storage(backend: str = "filesystem", **kwargs) -> EvidenceStorage:
    """Factory function to create storage backend."""
    if backend == "filesystem":
        return FilesystemEvidenceStorage(**kwargs)
    raise ValueError(f"Unknown storage backend: {backend}")


# Default storage instance
default_storage = create_storage("filesystem", base_path="./evidence_storage")