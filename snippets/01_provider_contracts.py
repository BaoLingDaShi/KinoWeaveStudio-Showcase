"""KinoWeave Studio Core — Provider Capability Protocols & Versioned Model Contracts (Excerpt).

Selected excerpt from `src/kinoweave/providers.py` and `src/kinoweave/model_contracts.py`
illustrating KinoWeave Studio's fail-closed Provider registry (no silent fallback) and
versioned OutputPolicy enforcement separating APPROVED contracts from CANDIDATE rules.
"""
from __future__ import annotations

from fractions import Fraction
from typing import Annotated, Any, Literal, Protocol, runtime_checkable

import jsonschema
from pydantic import Field, model_validator

from .errors import StudioError
from .schemas import Contract, Identifier, digest, validate, validate_local_schema

ModelId = Annotated[str, Field(min_length=1, max_length=256, pattern=r"^[^\s\x00-\x1f\x7f]+$")]


class ModelCapability(Contract):
    model_id: ModelId
    modality: Literal["image", "video"]
    operations: list[Literal["generate", "edit"]] = Field(min_length=1)
    parameter_schema: dict[str, Any] = Field(
        default_factory=lambda: {"type": "object", "additionalProperties": False}
    )


class ProviderCapability(Contract):
    provider_id: Identifier
    models: list[ModelCapability] = Field(min_length=1)
    asynchronous: bool
    cancellation: bool


class ProviderRequest(Contract):
    model_id: ModelId
    operation: Literal["generate", "edit"] = "generate"
    prompt: str = Field(min_length=1, max_length=100000)
    input_asset_ids: list[str] = Field(default_factory=list)
    parameters: dict[str, Any] = Field(default_factory=dict)


class SubmissionResult(Contract):
    task_id: str
    status: Literal["QUEUED", "SUCCEEDED"]
    model_id: str


class ProviderStatus(Contract):
    task_id: str
    status: Literal["QUEUED", "RUNNING", "SUCCEEDED", "FAILED", "CANCELLED", "UNKNOWN"]


class ProviderResult(Contract):
    task_id: str
    model_id: str
    artifacts: list[dict[str, str]]
    mock: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)


class CancelResult(Contract):
    task_id: str
    status: Literal["CANCELLED", "UNSUPPORTED", "ALREADY_FINISHED"]


@runtime_checkable
class ImageProvider(Protocol):
    def capabilities(self) -> ProviderCapability: ...
    def submit(self, request: ProviderRequest) -> SubmissionResult: ...
    def get_status(self, task_id: str) -> ProviderStatus: ...
    def fetch_result(self, task_id: str) -> ProviderResult: ...
    def cancel(self, task_id: str) -> CancelResult: ...


@runtime_checkable
class VideoProvider(ImageProvider, Protocol):
    """Modality lives in capability data; no invented video parameters."""


class ProviderRegistry:
    """Explicit provider/model registry with strict no-fallback resolution."""

    def __init__(self) -> None:
        self._providers: dict[str, ImageProvider | VideoProvider] = {}
        self._capabilities: dict[str, ProviderCapability] = {}

    def register(self, provider: ImageProvider | VideoProvider) -> None:
        if not isinstance(provider, ImageProvider):
            raise StudioError("VALIDATION", "Provider does not implement the minimum protocol")
        raw = provider.capabilities()
        if not isinstance(raw, ProviderCapability):
            raise StudioError("VALIDATION", "Provider must return a ProviderCapability object")
        capability = validate(ProviderCapability, raw.model_dump())
        if capability.provider_id in self._providers:
            raise StudioError("CONFLICT", "Provider ID is already registered")
        ids = [model.model_id for model in capability.models]
        if len(ids) != len(set(ids)):
            raise StudioError("CONFLICT", "Duplicate model capability")
        for model in capability.models:
            validate_local_schema(model.parameter_schema)
        self._providers[capability.provider_id] = provider
        self._capabilities[capability.provider_id] = capability

    def resolve(self, provider_id: str, model_id: str, modality: str):
        capability = self._capabilities.get(provider_id)
        if capability is None or not any(
            m.model_id == model_id and m.modality == modality for m in capability.models
        ):
            raise StudioError("MODEL_UNAVAILABLE", "Pinned provider/model/modality unavailable; no fallback")
        return self._providers[provider_id]


class ContractEvidence(Contract):
    level: Literal["DOCUMENTED", "OBSERVED", "OFFLINE_VERIFIED", "UNVERIFIED"]
    source: str = Field(min_length=1, max_length=500)
    detail: str = Field(min_length=1, max_length=1000)
    observed_at: str | None = None


class OutputPolicy(Contract):
    """Bounded interpretation of measured media output; never a silent global relaxation."""

    policy_id: Identifier
    revision: int = Field(gt=0)
    status: Literal["CANDIDATE", "APPROVED", "RETIRED"]
    fps_policy: Literal["PINNED", "DECODED"]
    duration_tolerance_frames: int = Field(ge=0, le=120)
    audio: Literal["SILENT_ONLY", "PROVIDER_NATIVE_ALLOWED_WITH_ACCEPTANCE"]
    require_timing_evidence: bool = True
    require_full_decode: bool = True
    av_duration_tolerance_ms: int = Field(ge=0, le=1000)
    evidence: list[ContractEvidence] = Field(default_factory=list)

    def evaluate(
        self,
        *,
        requested_duration_ms: int,
        requested_fps: Fraction,
        actual_duration: Fraction,
        actual_fps: Fraction,
        frame_count: int,
        audio_present: bool,
        timing_verified: bool,
        timing_mode: str,
        full_decode: bool,
        av_difference_ms: float,
        accepted: bool,
        declared_no_audio: bool = True,
    ) -> None:
        """Return None or raise a deterministic StudioError if output violates policy."""
        if self.status == "CANDIDATE" and not accepted:
            raise StudioError("CONTRACT_NOT_APPROVED", "Candidate contract requires explicit acceptance")
        if self.status == "RETIRED":
            raise StudioError("CONTRACT_RETIRED", "Output policy revision is retired")
        if self.require_timing_evidence and (
            not timing_verified or timing_mode not in ("CFR", "QUANTIZED_CFR")
        ):
            raise StudioError("VIDEO_OUTPUT_MISMATCH", "Decoded timing evidence is incomplete")
        if self.require_full_decode and not full_decode:
            raise StudioError("VIDEO_OUTPUT_MISMATCH", "Full decode did not pass")
        if actual_fps <= 0 or actual_duration <= 0 or frame_count <= 0:
            raise StudioError("VIDEO_OUTPUT_MISMATCH", "Decoded media measurement is incomplete")
        if self.fps_policy == "PINNED" and actual_fps != requested_fps:
            raise StudioError("VIDEO_OUTPUT_MISMATCH", "Decoded frame rate differs from the pinned rate")
        expected_frames = Fraction(requested_duration_ms, 1000) * requested_fps
        if abs(Fraction(frame_count) - expected_frames) > self.duration_tolerance_frames:
            raise StudioError("VIDEO_OUTPUT_MISMATCH", "Decoded frame count exceeds the accepted bound")
        duration_tolerance = Fraction(self.duration_tolerance_frames + 1, 1) / actual_fps
        if abs(actual_duration - Fraction(requested_duration_ms, 1000)) > duration_tolerance:
            raise StudioError("VIDEO_OUTPUT_MISMATCH", "Decoded duration exceeds the accepted bound")
        if audio_present and self.audio != "PROVIDER_NATIVE_ALLOWED_WITH_ACCEPTANCE":
            raise StudioError("VIDEO_OUTPUT_MISMATCH", "Native audio is outside this output policy")
        if audio_present and not accepted:
            raise StudioError("CONTRACT_NOT_APPROVED", "Native audio requires explicit acceptance")
        if audio_present and av_difference_ms > self.av_duration_tolerance_ms:
            raise StudioError("VIDEO_OUTPUT_MISMATCH", "Audio/video extent difference exceeds the bound")
        if not audio_present and not declared_no_audio:
            raise StudioError("VIDEO_OUTPUT_MISMATCH", "Missing required native audio")


class ContractRecord(Contract):
    contract_id: Identifier
    schema_version: Literal[1] = 1
    revision: int = Field(gt=0)
    status: Literal["CANDIDATE", "APPROVED", "RETIRED"]
    modality: Literal["image", "video"]
    provider_id: Identifier
    model_id: ModelId
    operations: list[Literal["generate", "edit"]] = Field(min_length=1)
    verified_operations: list[Literal["generate", "edit"]] = Field(default_factory=list)
    parameter_schema: dict[str, Any] = Field(
        default_factory=lambda: {"type": "object", "additionalProperties": False}
    )
    bounds: dict[str, Any] = Field(default_factory=dict)
    evidence: list[ContractEvidence] = Field(default_factory=list)
    output_policy: OutputPolicy | None = None

    @model_validator(mode="after")
    def coherent(self) -> ContractRecord:
        if len(set(self.operations)) != len(self.operations):
            raise ValueError("duplicate operation")
        if not set(self.verified_operations) <= set(self.operations):
            raise ValueError("verified operation is not declared")
        if self.output_policy is not None and self.modality != "video":
            raise ValueError("output policies apply to video only")
        return self

    def content_sha256(self) -> str:
        return digest(self.model_dump(mode="json"))

    def pin(self, runtime_contract_sha256: str) -> dict[str, Any]:
        policy = None
        if self.output_policy is not None:
            policy = {
                "policy_id": self.output_policy.policy_id,
                "revision": self.output_policy.revision,
                "status": self.output_policy.status,
            }
        return {
            "contract_id": self.contract_id,
            "schema_version": self.schema_version,
            "revision": self.revision,
            "status": self.status,
            "modality": self.modality,
            "provider_id": self.provider_id,
            "model_id": self.model_id,
            "operations": list(self.operations),
            "verified_operations": list(self.verified_operations),
            "content_sha256": self.content_sha256(),
            "runtime_contract_sha256": runtime_contract_sha256,
            "output_policy": policy,
        }
