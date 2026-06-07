"""Tencent COS upload helper for cloud image providers."""

from __future__ import annotations

import asyncio
import mimetypes
import uuid
from pathlib import Path

from qcloud_cos import CosConfig, CosS3Client

from .settings_service import get_cos_settings


class CosStorageError(Exception):
    pass


def cos_is_configured() -> bool:
    settings = get_cos_settings()
    return bool(
        settings["secret_id"]
        and settings["secret_key"]
        and settings["bucket"]
        and settings["region"]
    )


async def upload_reference_for_url(file_path: str, order_id: int | str = "shared") -> str:
    return await asyncio.to_thread(_upload_reference_for_url_sync, file_path, order_id)


def _upload_reference_for_url_sync(file_path: str, order_id: int | str) -> str:
    settings = get_cos_settings()
    if not cos_is_configured():
        raise CosStorageError(
            "COS is not configured. Fill SecretId, SecretKey, Bucket and Region in Settings first."
        )

    path = Path(file_path)
    if not path.exists() or not path.is_file():
        raise CosStorageError(f"Reference image does not exist: {file_path}")

    key = f"cuddlekine/reference/{order_id}/{uuid.uuid4().hex}{path.suffix.lower() or '.png'}"
    client = _client(settings)
    content_type = mimetypes.guess_type(str(path))[0] or "image/png"

    client.upload_file(
        Bucket=settings["bucket"],
        LocalFilePath=str(path),
        Key=key,
        EnableMD5=False,
        ContentType=content_type,
    )

    try:
        expires = int(settings["url_expire_seconds"] or "3600")
    except ValueError:
        expires = 3600

    return client.get_presigned_url(
        Method="GET",
        Bucket=settings["bucket"],
        Key=key,
        Expired=max(300, min(expires, 86400)),
    )


def _client(settings: dict[str, str]) -> CosS3Client:
    config = CosConfig(
        Region=settings["region"],
        SecretId=settings["secret_id"],
        SecretKey=settings["secret_key"],
        Scheme="https",
    )
    return CosS3Client(config)
