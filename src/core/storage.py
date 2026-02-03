"""Cloud Storage client wrapper for file operations."""

import io
import uuid
from pathlib import Path

from google.cloud import storage

from src.config import get_settings


class StorageClient:
    """Wrapper for Cloud Storage operations."""

    _instance: "StorageClient | None" = None
    _client: storage.Client | None = None
    _bucket: storage.Bucket | None = None

    def __new__(cls) -> "StorageClient":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @property
    def client(self) -> storage.Client:
        """Get or create Storage client."""
        if self._client is None:
            self._client = storage.Client()
        return self._client

    @property
    def bucket(self) -> storage.Bucket:
        """Get or create bucket reference."""
        if self._bucket is None:
            settings = get_settings()
            self._bucket = self.client.bucket(settings.gcs_bucket_name)
        return self._bucket

    async def upload_file(
        self,
        file_content: bytes,
        filename: str,
        content_type: str,
        user_id: str,
    ) -> str:
        """
        Upload file to Cloud Storage.

        Returns:
            Storage path (gs://bucket/path)
        """
        # Generate unique path
        file_ext = Path(filename).suffix
        unique_name = f"{uuid.uuid4()}{file_ext}"
        blob_path = f"documents/{user_id}/{unique_name}"

        blob = self.bucket.blob(blob_path)
        blob.upload_from_string(file_content, content_type=content_type)

        settings = get_settings()
        return f"gs://{settings.gcs_bucket_name}/{blob_path}"

    async def download_file(self, storage_path: str) -> bytes:
        """
        Download file from Cloud Storage.

        Args:
            storage_path: Full gs:// path or blob path

        Returns:
            File content as bytes
        """
        # Extract blob path from gs:// URL
        if storage_path.startswith("gs://"):
            parts = storage_path.replace("gs://", "").split("/", 1)
            blob_path = parts[1] if len(parts) > 1 else ""
        else:
            blob_path = storage_path

        blob = self.bucket.blob(blob_path)
        return blob.download_as_bytes()

    async def download_to_file(self, storage_path: str, local_path: str) -> None:
        """Download file to local path."""
        content = await self.download_file(storage_path)
        with open(local_path, "wb") as f:
            f.write(content)

    async def delete_file(self, storage_path: str) -> None:
        """Delete file from Cloud Storage."""
        if storage_path.startswith("gs://"):
            parts = storage_path.replace("gs://", "").split("/", 1)
            blob_path = parts[1] if len(parts) > 1 else ""
        else:
            blob_path = storage_path

        blob = self.bucket.blob(blob_path)
        blob.delete()

    async def get_signed_url(self, storage_path: str, expiration_minutes: int = 60) -> str:
        """
        Generate a signed URL for temporary access.

        Args:
            storage_path: Full gs:// path or blob path
            expiration_minutes: URL validity in minutes

        Returns:
            Signed URL string
        """
        from datetime import timedelta

        if storage_path.startswith("gs://"):
            parts = storage_path.replace("gs://", "").split("/", 1)
            blob_path = parts[1] if len(parts) > 1 else ""
        else:
            blob_path = storage_path

        blob = self.bucket.blob(blob_path)
        return blob.generate_signed_url(
            version="v4",
            expiration=timedelta(minutes=expiration_minutes),
            method="GET",
        )


def get_storage_client() -> StorageClient:
    """Get Storage client instance (dependency injection)."""
    return StorageClient()
