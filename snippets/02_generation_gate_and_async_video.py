"""KinoWeave Studio Core — Fail-Closed Generation Gate & Async Video Orchestration (Excerpt).

Selected excerpt from `src/kinoweave/generation_gate.py` and `src/kinoweave/video_generation.py`
demonstrating:
1. Seven-check read-only Generation Gate with snapshot/review/route revalidation and
   rejection of secret-keyed generation parameters.
2. Config-pinned asynchronous video submission and monotonic state checkpoints that treat
   uncertain outcomes as UNKNOWN / RECONCILIATION_REQUIRED rather than blindly retrying.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Literal, Protocol

import jsonschema
from pydantic import Field
from sqlalchemy import select

from .db import Event, GenerationAttempt, GenerationJob, now
from .errors import StudioError
from .generation_submission import GenerationSubmissionService
from .providers import ProviderRegistry
from .schemas import Contract, Identifier, digest
from .video_provider import VideoCancellation, VideoObservation, VideoRequest, VideoTask

GATE_VERSION = "1.0"
_SECRET_KEY = re.compile(r"(api[_-]?key|token|secret|password|credential|authorization)", re.I)


class ImageGenerationIntent(Contract):
    snapshot_id: str = Field(pattern=r"^psnap-[0-9a-f]{64}$")
    expected_snapshot_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    project_id: Identifier
    shot_id: Identifier
    requested_provider_id: Identifier
    requested_model_id: str = Field(min_length=1, max_length=256)
    operation: Literal["generate", "edit"] = "generate"
    generation_parameters: dict[str, Any] = Field(default_factory=dict)


class GateCheck(Contract):
    name: Identifier
    status: Literal["PASS", "FAIL", "NOT_VERIFIABLE", "NOT_APPLICABLE"]
    code: str
    detail: str


class GenerationGateResult(Contract):
    status: Literal["ALLOWED", "DENIED"]
    allowed: bool
    checks: tuple[GateCheck, ...]
    issues: tuple[str, ...]
    snapshot_id: str | None = None
    snapshot_sha256: str | None = None
    project_id: str | None = None
    shot_id: str | None = None
    review_id: str | None = None
    decision_id: str | None = None
    provider_id: str | None = None
    model_id: str | None = None
    route_revision: int | None = None
    route_sha256: str | None = None
    parameter_fingerprint: str | None = None
    gate_version: str = GATE_VERSION
    checked_at: str


@dataclass(frozen=True)
class PinnedRoute:
    provider_id: str
    model_id: str
    route_revision: int | None = None
    route_sha256: str | None = None
    project_id: str | None = None


class PinnedRouteSource(Protocol):
    def resolve_image_route(self, project_id: str) -> PinnedRoute | None: ...


class GenerationGateVerifier:
    """Read-only, fail-closed pre-submission authorization checks (excerpt)."""

    prompt_type = "IMAGE"
    modality = "image"

    def __init__(self, studio, *, snapshot_index, review_service, provider_registry: ProviderRegistry):
        self.studio = studio
        self.snapshot_index = snapshot_index
        self.review_service = review_service
        self.provider_registry = provider_registry

    def verify_parameters_and_route(
        self,
        request: ImageGenerationIntent,
        route: PinnedRoute,
        capability,
        checks: list[GateCheck],
    ) -> bool:
        """Reject secret-keyed fields and mismatching provider routes before execution."""
        if _SECRET_KEY.search(" ".join(str(k) for k in request.generation_parameters)):
            checks.append(
                GateCheck(
                    name="model_parameters",
                    status="FAIL",
                    code="PARAMETER_SECRET_NOT_ALLOWED",
                    detail="Secret-valued fields are not accepted as generation parameters",
                )
            )
            return False

        if (route.provider_id, route.model_id) != (
            request.requested_provider_id,
            request.requested_model_id,
        ):
            checks.append(
                GateCheck(
                    name="pinned_route",
                    status="FAIL",
                    code="PINNED_ROUTE_MISMATCH",
                    detail="Requested Provider/Model differs from the configured project pin",
                )
            )
            return False

        try:
            jsonschema.Draft202012Validator(capability.parameter_schema).validate(
                request.generation_parameters
            )
        except (jsonschema.ValidationError, jsonschema.SchemaError, TypeError, ValueError):
            checks.append(
                GateCheck(
                    name="model_capability",
                    status="FAIL",
                    code="MODEL_PARAMETERS_UNSUPPORTED",
                    detail="Generation parameters do not satisfy the registered model schema",
                )
            )
            return False

        checks.append(
            GateCheck(
                name="model_capability",
                status="PASS",
                code="MODEL_CAPABILITY_VERIFIED",
                detail="Registered model capability and parameter schema accepted the request",
            )
        )
        return True


class AsyncVideoOrchestratorExcerpt:
    """Immutable manifest pinning & single-flight submission boundary (excerpt)."""

    def __init__(self, studio, jobs, leases, *, usage_ledger=None):
        self.studio, self.jobs, self.leases = studio, jobs, leases
        self.usage_ledger = usage_ledger

    def verify_pinned_request(self, job, adapter) -> VideoRequest:
        """Ensure an in-flight Job cannot be redirected across provider configurations."""
        manifest = self.jobs.read_manifest(job.job_id)
        if manifest.get("modality") != "VIDEO":
            raise StudioError("SCOPE", "VIDEO execution requires a VIDEO Job")
        request = VideoRequest.model_validate(manifest["video_request"])
        if (
            request.project_id != job.project_id
            or request.provider_id != job.provider_id
            or request.model_id != job.model_id
            or request.snapshot_sha256 != job.snapshot_sha256
            or request.prompt != manifest["compiled_prompt"]
        ):
            raise StudioError("BINDING_MISMATCH", "VIDEO request differs from immutable Job")
        identity_of = getattr(adapter, "config_identity", None)
        bound = manifest.get("provider_config")
        if bound is not None and callable(identity_of) and identity_of() != bound:
            raise StudioError(
                "PROVIDER_CONFIG_CHANGED",
                "VIDEO Job is bound to a different Provider configuration",
            )
        return request

    def submit_once_with_budget_reservation(
        self, context, reservation, adapter, request: VideoRequest, *, timeout_seconds: float = 30
    ):
        """Consume budget reservation prior to a single external submit; never auto-retry."""
        job = self.jobs.get_job_by_id(context.job_id)
        with self.leases._write() as session:
            current = session.get(GenerationJob, job.job_id)
            attempt = session.get(GenerationAttempt, context.attempt_id)
            GenerationSubmissionService._assert_reservation(current, attempt, context, reservation)
            if attempt.provider_status is not None:
                raise StudioError("SUBMISSION_CONFLICT", "VIDEO submit boundary was already consumed")
            if self.usage_ledger is None or self.usage_ledger.policy.provider_id != job.provider_id:
                raise StudioError("PROVIDER_BUDGET", "Matching persistent VIDEO usage ledger required")
            self.usage_ledger.reserve(
                context.attempt_id,
                project_id=job.project_id,
                operation=request.operation,
                model_id=job.model_id,
                endpoint=self.usage_ledger.policy.endpoint,
                request_sha256=digest(request.model_dump(mode="json")),
            )
            attempt.provider_status = "SDK_SUBMISSION_STARTED"
            attempt.sdk_submission_started_at = now()
            attempt.state_revision += 1
            self.studio._event(
                session,
                job.project_id,
                "generation.attempt.sdk_submission_started",
                attempt.attempt_id,
                "Durably consume VIDEO Reservation before exactly one submission call",
                {"job_id": job.job_id, "reservation_id": reservation.reservation_id, "automatic_retries": 0},
            )
        try:
            observation = VideoObservation.model_validate(
                adapter.submit(request, timeout_seconds=timeout_seconds).model_dump()
            )
            if (observation.provider_id, observation.model_id) != (job.provider_id, job.model_id):
                raise StudioError("BINDING_MISMATCH", "VIDEO acceptance belongs to a different Provider/Model")
            task = VideoTask(
                task_id=observation.task_id,
                project_id=job.project_id,
                provider_id=job.provider_id,
                model_id=job.model_id,
                request_sha256=digest(request.model_dump()),
            )
            return task.observe(observation)
        except Exception:
            # Ambiguous errors after crossing the call boundary mark UNKNOWN; never auto-resubmit.
            GenerationSubmissionService(self.studio, self.jobs, self.leases)._record_failure(
                context, reservation, "VIDEO_ACCEPTANCE_UNKNOWN", called_sdk=True
            )
            raise StudioError(
                "RECONCILIATION_REQUIRED",
                "VIDEO acceptance is unknown; no automatic resubmission",
            ) from None
