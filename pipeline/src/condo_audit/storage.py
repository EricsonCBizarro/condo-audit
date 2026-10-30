"""Object storage (bronze layer). Any S3-compatible service works."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from condo_audit.settings import Settings

if TYPE_CHECKING:
    from mypy_boto3_s3 import S3Client


class DocumentStore(Protocol):
    def get(self, key: str) -> bytes: ...


class S3DocumentStore:
    def __init__(self, client: S3Client, bucket: str) -> None:
        self._client = client
        self._bucket = bucket

    @classmethod
    def from_settings(cls, settings: Settings) -> S3DocumentStore:
        client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url,
            aws_access_key_id=settings.s3_access_key.get_secret_value(),
            aws_secret_access_key=settings.s3_secret_key.get_secret_value(),
            region_name=settings.s3_region,
            config=Config(s3={"addressing_style": "path"}, retries={"max_attempts": 5, "mode": "standard"}),
        )
        return cls(client, settings.s3_bucket)

    def get(self, key: str) -> bytes:
        return self._client.get_object(Bucket=self._bucket, Key=key)["Body"].read()

    def put(self, key: str, data: bytes) -> None:
        self._client.put_object(Bucket=self._bucket, Key=key, Body=data)

    def ensure_bucket(self) -> bool:
        """Create the bucket if missing. Returns True when it was created."""
        try:
            self._client.head_bucket(Bucket=self._bucket)
            return False
        except ClientError:
            self._client.create_bucket(Bucket=self._bucket)
            return True
