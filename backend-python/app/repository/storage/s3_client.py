"""aioboto3 wrapper for S3-compatible object storage.

DRD §8.3: video files served via signed URLs with 24h expiry.
DRD §8.4: audio files via signed URLs (same TTL).
"""
from __future__ import annotations

from typing import Any, AsyncIterator

import aioboto3

from app.shared.config import settings

# Per DRD §8.3 — generated media URLs expire in 24 hours.
_DEFAULT_SIGNED_URL_TTL_S = 86_400


class S3Client:
    """Lightweight wrapper around aioboto3's resource client.

    Holds no persistent connection; aioboto3 manages pooling internally. Each
    method opens its own session — cheap because the underlying httpx client
    is reused via boto's connection pool.
    """

    def __init__(self, bucket: str | None = None) -> None:
        self._bucket = bucket or settings.s3_bucket
        self._session = aioboto3.Session()

    def _client_kwargs(self) -> dict[str, Any]:
        return {
            "endpoint_url": settings.s3_endpoint or None,
            "aws_access_key_id": settings.s3_access_key.get_secret_value(),
            "aws_secret_access_key": settings.s3_secret_key.get_secret_value(),
            "region_name": settings.s3_region,
        }

    async def upload_video(
        self,
        key: str,
        body: bytes | AsyncIterator[bytes],
        content_type: str = "video/mp4",
    ) -> str:
        """Upload bytes (or an async stream) and return the s3:// URI."""
        async with self._session.client("s3", **self._client_kwargs()) as client:
            if isinstance(body, bytes):
                await client.put_object(
                    Bucket=self._bucket,
                    Key=key,
                    Body=body,
                    ContentType=content_type,
                )
            else:
                await client.upload_fileobj(_AsyncIterReader(body), self._bucket, key)
        return f"s3://{self._bucket}/{key}"

    async def generate_signed_url(
        self,
        key: str,
        expires_in: int = _DEFAULT_SIGNED_URL_TTL_S,
    ) -> str:
        async with self._session.client("s3", **self._client_kwargs()) as client:
            return await client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self._bucket, "Key": key},
                ExpiresIn=expires_in,
            )


class _AsyncIterReader:
    """Adapt an async byte iterator to boto's file-like read() interface."""

    def __init__(self, source: AsyncIterator[bytes]) -> None:
        self._source = source
        self._buffer = b""

    async def read(self, size: int = -1) -> bytes:
        if size < 0:
            chunks = [self._buffer]
            self._buffer = b""
            async for chunk in self._source:
                chunks.append(chunk)
            return b"".join(chunks)
        while len(self._buffer) < size:
            try:
                self._buffer += await self._source.__anext__()
            except StopAsyncIteration:
                break
        out, self._buffer = self._buffer[:size], self._buffer[size:]
        return out
