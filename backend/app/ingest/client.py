from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from uuid import UUID

import aioboto3
from botocore.exceptions import ClientError
from types_aiobotocore_s3.client import S3Client

from app.config import config


class MinioClient:
    def __init__(self) -> None:
        self._session: aioboto3.Session = aioboto3.Session()

    async def ensure_bucket(self) -> None:
        async with self._get_client() as client:
            try:
                await client.head_bucket(Bucket=config.minio.BUCKET)
            except ClientError:
                await client.create_bucket(Bucket=config.minio.BUCKET)

    async def object_exists(self, key: str) -> bool:
        async with self._get_client() as client:
            try:
                await client.head_object(Bucket=config.minio.BUCKET, Key=key)
                return True
            except ClientError:
                return False

    async def put_object(self, key: str, body: bytes, content_type: str) -> None:
        async with self._get_client() as client:
            await client.put_object(
                Bucket=config.minio.BUCKET,
                Key=key,
                Body=body,
                ContentType=content_type,
            )

    async def get_object(self, key: str) -> bytes:
        async with self._get_client() as client:
            response = await client.get_object(Bucket=config.minio.BUCKET, Key=key)
            async with response["Body"] as stream:
                return await stream.read()

    @staticmethod
    def get_stream_object_key(meeting_id: UUID, stream_id: UUID, part: int = 1) -> str:
        suffix = "" if part == 1 else f".part{part}"
        return f"meetings/{meeting_id}/streams/{stream_id}{suffix}.wav"

    @asynccontextmanager
    async def _get_client(self) -> AsyncGenerator[S3Client]:
        async with self._session.client(
            service_name="s3",
            endpoint_url=config.minio.ENDPOINT_URL,
            aws_access_key_id=config.minio.ACCESS_KEY.get_secret_value(),
            aws_secret_access_key=config.minio.SECRET_KEY.get_secret_value(),
        ) as client:
            yield client


minio_client = MinioClient()
