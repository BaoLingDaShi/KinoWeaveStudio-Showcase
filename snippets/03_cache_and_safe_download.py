"""KinoWeave Studio Core — Task-Bound Video Cache & Anti-SSRF Downloader (Excerpt).

Selected excerpt from `src/kinoweave/video_result_cache.py` and `src/kinoweave/video_download.py`
illustrating:
1. Zero-network cache-first video recovery bound to Data Root, Job, Attempt, Manifest,
   Contract, Endpoint, and SHA-256 byte integrity.
2. SSRF-hardened HTTPS downloader with explicit host allowlists, bounded DNS resolution,
   public-IP verification, and atomic exclusive staging publication.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import ipaddress
import json
import os
from pathlib import Path, PurePosixPath
import queue
import re
import socket
import threading
import time
from urllib.parse import urlsplit

from pydantic import Field, model_validator

from .artifacts.contracts import StagingRef
from .errors import StudioError
from .schemas import Contract, Identifier
from .video_provider import VideoOutput

CACHE_VERSION = 1
_dns_slots = threading.BoundedSemaphore(4)


class VideoResultReceipt(Contract):
    """Task-bound receipt binding staged bytes to an exact Job, Attempt, and Contract."""

    schema_version: int = CACHE_VERSION
    project_id: Identifier
    job_id: str
    attempt_id: str
    task_id: str
    provider_id: str
    model_id: str
    manifest_sha256: str
    contract_sha256: str
    endpoint_sha256: str
    staging_ref: StagingRef
    staging_path: str
    source_sha256: str
    size_bytes: int = Field(gt=0, le=512 * 1024 * 1024)
    mime_type: str
    downloaded_at: str
    stage: str = "DOWNLOADED"

    @model_validator(mode="after")
    def safe(self) -> VideoResultReceipt:
        if len(self.manifest_sha256) != 64 or len(self.source_sha256) != 64:
            raise ValueError("cache hashes must be SHA-256")
        parts = PurePosixPath(self.staging_path).parts
        if (
            not self.staging_path.startswith("video_staging/")
            or ".." in parts
            or "\\" in self.staging_path
            or ":" in self.staging_path
        ):
            raise ValueError("cache staging path must remain inside video_staging")
        return self


def verify_cached_receipt(home: Path, *, project_id: str, job, attempt, manifest: dict) -> VideoOutput | None:
    """Load and SHA-256-verify a staged video result without creating any network transport."""
    root = Path(home).resolve()
    receipt_path = (root / "state" / "video-results" / job.job_id / f"{attempt.attempt_id}.json").resolve()
    if not receipt_path.is_relative_to(root):
        raise StudioError("CACHE_PATH", "Cache receipt escapes the Data Root")
    if not receipt_path.exists():
        return None
    receipt = VideoResultReceipt.model_validate(json.loads(receipt_path.read_text("utf-8")))
    provider_config = manifest.get("provider_config") or {}
    if (
        receipt.project_id,
        receipt.job_id,
        receipt.attempt_id,
        receipt.task_id,
        receipt.provider_id,
        receipt.model_id,
        receipt.manifest_sha256,
        receipt.contract_sha256,
        receipt.endpoint_sha256,
    ) != (
        project_id,
        job.job_id,
        attempt.attempt_id,
        attempt.provider_request_id,
        job.provider_id,
        job.model_id,
        job.request_manifest_sha256,
        provider_config.get("contract_sha256"),
        provider_config.get("endpoint_sha256"),
    ):
        raise StudioError("CACHE_BINDING", "Cached receipt belongs to another task or manifest")
    staged = (root / receipt.staging_path).resolve()
    staging_root = (root / "video_staging").resolve()
    if not staged.is_relative_to(staging_root) or staged.is_symlink() or not staged.is_file():
        raise StudioError("CACHE_MISSING", "Cached media is missing or unsafe")
    data = staged.read_bytes()
    if hashlib.sha256(data).hexdigest() != receipt.source_sha256 or len(data) != receipt.size_bytes:
        raise StudioError("CACHE_HASH", "Cached media bytes differ from the receipt")
    return VideoOutput(
        provider_id=receipt.provider_id,
        task_id=receipt.task_id,
        model_id=receipt.model_id,
        staging_ref=receipt.staging_ref,
        sha256=receipt.source_sha256,
        size_bytes=receipt.size_bytes,
        mime_type=receipt.mime_type,
    )


@dataclass(frozen=True)
class DownloadTarget:
    url: str
    hostname: str
    addresses: tuple[str, ...]
    request_path: str
    port: int = 443


def public_address(value: str) -> bool:
    """Reject loopback, private, link-local, multicast, reserved, or mapped IP targets."""
    address = ipaddress.ip_address(value)
    return (
        address.is_global
        and not address.is_multicast
        and not address.is_reserved
        and not address.is_unspecified
        and not address.is_loopback
        and not address.is_link_local
        and not address.is_private
        and getattr(address, "ipv4_mapped", None) is None
        and getattr(address, "sixtofour", None) is None
        and getattr(address, "teredo", None) is None
    )


def bounded_dns(resolver, host: str, timeout: float) -> tuple[str, ...]:
    """Run DNS resolution under a fixed concurrency semaphore and strict deadline."""
    if not _dns_slots.acquire(blocking=False):
        raise StudioError("DOWNLOAD_TIMEOUT", "Video DNS resolution is busy")
    answer: queue.Queue[tuple[bool, tuple[str, ...] | None]] = queue.Queue(maxsize=1)

    def resolve() -> None:
        try:
            answer.put((True, tuple(resolver(host))))
        except Exception:
            answer.put((False, None))
        finally:
            _dns_slots.release()

    threading.Thread(target=resolve, daemon=True).start()
    try:
        ok, result = answer.get(timeout=timeout)
    except queue.Empty:
        raise StudioError("DOWNLOAD_TIMEOUT", "Video DNS resolution deadline expired") from None
    if not ok or result is None:
        raise StudioError("DOWNLOAD_DESTINATION", "Untrusted video download destination")
    return result


def validate_download_destination(url: str, allowed_hosts: frozenset[str], resolver, timeout: float = 30.0) -> DownloadTarget:
    """Allow only HTTPS URLs on explicitly allowlisted hosts resolving exclusively to public IPs."""
    if not isinstance(url, str) or len(url) > 16384 or any(ord(c) <= 32 or ord(c) >= 127 for c in url) or "\\" in url:
        raise StudioError("DOWNLOAD_DESTINATION", "Untrusted video download destination")
    parsed = urlsplit(url)
    host = parsed.hostname
    if (
        parsed.scheme != "https"
        or not host
        or parsed.username is not None
        or parsed.password is not None
        or parsed.port not in (None, 443)
        or parsed.fragment
        or host not in allowed_hosts
        or parsed.netloc.lower() not in (host, host + ":443")
    ):
        raise StudioError("DOWNLOAD_DESTINATION", "Untrusted video download destination")
    addresses = bounded_dns(resolver, host, timeout)
    if not addresses or any(not public_address(addr) for addr in addresses):
        raise StudioError("DOWNLOAD_DESTINATION", "Untrusted video download destination")
    request_path = (parsed.path or "/") + ("?" + parsed.query if parsed.query else "")
    return DownloadTarget(url, host, addresses, request_path, 443)
