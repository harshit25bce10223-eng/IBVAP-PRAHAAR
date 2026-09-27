# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR — Evidence Hasher (SHA-256 Streaming)
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import hashlib
from typing import BinaryIO


DEFAULT_CHUNK_SIZE = 64 * 1024  # 64KB chunks for streaming


class EvidenceHasher:
    """SHA-256 hasher with streaming support for large files."""

    ALGORITHM = "SHA-256"
    ALGORITHM_VERSION = "SHA-256"

    def __init__(self, chunk_size: int = DEFAULT_CHUNK_SIZE):
        self.chunk_size = chunk_size

    def hash_bytes(self, data: bytes) -> str:
        """Hash a bytes object directly."""
        return hashlib.sha256(data).hexdigest()

    def hash_stream(self, stream: BinaryIO) -> str:
        """
        Hash a stream in chunks to avoid loading entire file into memory.

        Args:
            stream: A file-like object opened in binary mode

        Returns:
            Hex digest of SHA-256 hash
        """
        hasher = hashlib.sha256()
        while True:
            chunk = stream.read(self.chunk_size)
            if not chunk:
                break
            hasher.update(chunk)
        return hasher.hexdigest()

    def hash_file(self, file_path: str) -> str:
        """
        Hash a file on disk.

        Args:
            file_path: Path to the file

        Returns:
            Hex digest of SHA-256 hash
        """
        with open(file_path, "rb") as f:
            return self.hash_stream(f)

    def verify_hash(self, stream: BinaryIO, expected_hash: str) -> bool:
        """
        Verify a stream against an expected hash.

        Args:
            stream: A file-like object opened in binary mode
            expected_hash: Expected hex digest

        Returns:
            True if hash matches, False otherwise
        """
        computed = self.hash_stream(stream)
        return computed == expected_hash


# Global hasher instance
evidence_hasher = EvidenceHasher()