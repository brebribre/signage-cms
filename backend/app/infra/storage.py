"""Cloudflare R2, over the S3 API.

**The only module in the codebase that touches boto3 or constructs a storage URL.** That is
what makes swapping providers a one-file change, and what lets check scripts stub storage by
patching this module's functions.
"""

import logging
from functools import lru_cache

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from app.config import get_settings

logger = logging.getLogger(__name__)


@lru_cache
def _client():
    """Built lazily so importing this module never requires credentials.

    Three settings here are not optional for R2:

    - `region_name="auto"` — R2 has no regions and rejects a real one.
    - `signature_version="s3v4"` — presigned URLs are otherwise signed with v2.
    - the two `*_checksum_*` options — boto3 ≥1.36 sends CRC32 integrity headers by default,
      which several S3-compatible providers reject with an opaque 400. If uploads start
      failing with an unexplained 400 after a boto3 upgrade, look here first.
    """
    settings = get_settings()
    return boto3.client(
        "s3",
        endpoint_url=settings.r2_endpoint_url,
        aws_access_key_id=settings.r2_access_key_id,
        aws_secret_access_key=settings.r2_secret_access_key,
        region_name="auto",
        config=Config(
            signature_version="s3v4",
            request_checksum_calculation="when_required",
            response_checksum_validation="when_required",
        ),
    )


def presign_put(key: str, content_type: str, ttl: int | None = None) -> str:
    """A URL the browser can PUT one object to.

    **Only `Content-Type` is signed**, and the browser must send exactly that value or the
    signature will not match — an error that names nothing useful. No `x-amz-acl`: R2 has no
    ACLs and rejects the header rather than ignoring it.
    """
    settings = get_settings()
    return _client().generate_presigned_url(
        "put_object",
        Params={"Bucket": settings.r2_bucket, "Key": key, "ContentType": content_type},
        ExpiresIn=ttl or settings.presign_put_ttl_seconds,
    )


def presign_get(key: str, ttl: int | None = None, download_name: str | None = None) -> str:
    """A short-lived read URL. The bucket is private; there are no public URLs anywhere.

    `download_name` makes a browser save the file under that name rather than the last part of
    the key — the key is the storage name, which need not be the one a person should see.
    """
    settings = get_settings()
    params = {"Bucket": settings.r2_bucket, "Key": key}
    if download_name:
        params["ResponseContentDisposition"] = f'attachment; filename="{download_name}"'
    return _client().generate_presigned_url(
        "get_object",
        Params=params,
        ExpiresIn=ttl or settings.presign_get_ttl_seconds,
    )


def list_objects(prefix: str) -> list[dict]:
    """Every object under a prefix — key, size, last-modified. Paginated automatically; a
    folder of APK builds will never be large enough for pagination to matter in practice, but
    a silently-truncated first page hiding an old build would be worse than the extra call."""
    paginator = _client().get_paginator("list_objects_v2")
    out: list[dict] = []
    for page in paginator.paginate(Bucket=get_settings().r2_bucket, Prefix=prefix):
        out.extend(page.get("Contents", []))
    return out


def iter_objects(prefix: str = ""):
    """Every object under a prefix, one at a time — for walking the whole bucket without
    holding every listing in memory. Each page of 1,000 is one billed List call."""
    paginator = _client().get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=get_settings().r2_bucket, Prefix=prefix):
        yield from page.get("Contents", [])


def head_object(key: str) -> dict | None:
    """Object metadata, or None if it is not there. Used to confirm an upload really landed."""
    try:
        return _client().head_object(Bucket=get_settings().r2_bucket, Key=key)
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") in {"404", "NoSuchKey", "NotFound"}:
            return None
        raise


def download_file(key: str, path: str) -> None:
    """Copy an object to a local file — for server-side work on an upload (see
    services/video_streams.py). Streams to disk; a large video is never held in memory."""
    _client().download_file(get_settings().r2_bucket, key, path)


def upload_file(path: str, key: str, content_type: str) -> None:
    """The reverse of [download_file]: a local file into the bucket, multipart where large."""
    _client().upload_file(path, get_settings().r2_bucket, key, ExtraArgs={"ContentType": content_type})


def delete_object(key: str) -> None:
    """Best effort.

    Called *after* the database row is committed. If this fails the row is already gone and
    the object is orphaned: log it and move on. An orphan costs storage; a failed delete that
    rolls back a committed row costs correctness. `scripts/sweep_orphans.py` is Phase 14.
    """
    try:
        _client().delete_object(Bucket=get_settings().r2_bucket, Key=key)
    except ClientError:
        logger.exception("could not delete %s from R2 — orphaned object left behind", key)
