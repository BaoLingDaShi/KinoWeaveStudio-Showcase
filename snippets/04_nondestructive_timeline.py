"""KinoWeave Studio Core — Frame-Exact Non-Destructive Timeline Model (Excerpt).

Selected excerpt from `src/kinoweave/editing.py` illustrating rational frame-rate
normalization, non-overlapping track/clip invariants, immutable source-Asset SHA-256
binding, and optimistic revision locking without mutating registered source media.
"""
from __future__ import annotations

from fractions import Fraction
import hashlib
from math import gcd
from threading import RLock
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator
from sqlalchemy import select

from .db import Asset, EditingRevision, EditingSequence
from .errors import StudioError
from .schemas import canonical, identifier

Frame = Annotated[int, Field(ge=0, le=10_368_000)]
PositiveFrame = Annotated[int, Field(gt=0, le=10_368_000)]
Id = Annotated[str, Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{0,79}$")]


class DTO(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class FrameRate(DTO):
    num: Annotated[int, Field(ge=1, le=120000)]
    den: Annotated[int, Field(ge=1, le=1001)]

    @model_validator(mode="after")
    def valid(self) -> FrameRate:
        if gcd(self.num, self.den) != 1 or not 1 <= Fraction(self.num, self.den) <= 120:
            raise ValueError("Frame rate must be normalized and between 1 and 120")
        return self


class EditingClip(DTO):
    id: Id
    asset_id: Id
    asset_sha256: Annotated[str, Field(pattern="^[0-9a-f]{64}$")]
    kind: Literal["image", "video", "audio"]
    start: Frame
    source_in: Frame
    duration: PositiveFrame
    gain: Annotated[float, Field(ge=0, le=1)] = 1.0


class EditingTrack(DTO):
    id: Id
    name: Annotated[str, Field(min_length=1, max_length=80)]
    kind: Literal["visual", "audio"]
    locked: bool = False
    muted: bool = False
    clips: Annotated[list[EditingClip], Field(max_length=200)]


class EditingDocument(DTO):
    schema_version: Literal[1] = 1
    name: Annotated[str, Field(min_length=1, max_length=120)]
    fps: FrameRate
    tracks: Annotated[list[EditingTrack], Field(min_length=1, max_length=16)]

    @model_validator(mode="after")
    def valid(self) -> EditingDocument:
        ids: list[str] = []
        for track in self.tracks:
            ids.append(track.id)
            end = 0
            for clip in sorted(track.clips, key=lambda c: c.start):
                ids.append(clip.id)
                if (
                    clip.start < end
                    or clip.start + clip.duration > 10_368_000
                    or (track.kind == "audio") != (clip.kind == "audio")
                ):
                    raise ValueError("Overlap, bounds or track/media mismatch")
                end = clip.start + clip.duration
                if clip.kind == "image" and clip.source_in:
                    raise ValueError("Still images have no source clock")
        if len(ids) != len(set(ids)) or len(ids) - len(self.tracks) > 200:
            raise ValueError("Duplicate identity or clip limit")
        return self


class SaveEditing(DTO):
    project_id: Id
    sequence_id: Id
    expected_revision: Annotated[int, Field(ge=0, le=2147483646)]
    document: EditingDocument


class TimelineValidationExcerpt:
    """Excerpts of Core's immutable snapshot hashing and source-extent checks."""

    def __init__(self, studio) -> None:
        self.studio = studio
        self._media_cache: dict[tuple[str, str, str], dict] = {}
        self._cache_lock = RLock()

    @staticmethod
    def verify_snapshot_digest(row: EditingRevision) -> dict:
        if hashlib.sha256(canonical(row.document).encode()).hexdigest() != row.sha256:
            raise StudioError("STATE_INCONSISTENT", "Editing snapshot hash mismatch")
        return {
            "project_id": row.project_id,
            "sequence_id": row.sequence_id,
            "revision": row.revision,
            "document": row.document,
            "sha256": row.sha256,
            "created_at": row.created_at,
        }

    def save_revision(self, payload: dict, measure_media, *, authorize=lambda: None) -> dict:
        """Persist a new immutable EditingRevision with optimistic concurrency and asset pinning."""
        try:
            command = SaveEditing.model_validate(payload)
        except ValidationError:
            raise StudioError("VALIDATION", "Invalid editing document") from None
        doc = command.document
        measurements = {}
        for track in doc.tracks:
            for clip in track.clips:
                if clip.asset_id not in measurements:
                    authorize()
                    measurements[clip.asset_id] = measure_media(command.project_id, clip.asset_id)
                media = measurements[clip.asset_id]
                if media["sha256"] != clip.asset_sha256 or media["kind"] != clip.kind:
                    raise StudioError("VALIDATION", "Clip Asset identity mismatch")
                if media["duration"] is not None:
                    extent = Fraction(media["duration"]["num"], media["duration"]["den"])
                    if Fraction((clip.source_in + clip.duration) * doc.fps.den, doc.fps.num) > extent:
                        raise StudioError("VALIDATION", "Clip exceeds measured source extent")
        authorize()
        with self.studio._write() as session:
            self.studio._project(session, command.project_id, True)
            sequence = session.get(EditingSequence, command.sequence_id)
            if sequence is not None and (
                sequence.project_id != command.project_id
                or sequence.archived
                or sequence.revision != command.expected_revision
            ):
                raise StudioError("CONFLICT", "Editing revision changed; reload before saving")
            if sequence is None:
                if command.expected_revision != 0:
                    raise StudioError("CONFLICT", "Sequence no longer exists")
                sequence = EditingSequence(
                    id=command.sequence_id, project_id=command.project_id, name=doc.name, revision=1
                )
                session.add(sequence)
                session.flush()
            else:
                previous = session.scalar(
                    select(EditingRevision).where(
                        EditingRevision.sequence_id == sequence.id,
                        EditingRevision.revision == sequence.revision,
                    )
                )
                self.verify_snapshot_digest(previous)
                if previous.document["fps"] != doc.fps.model_dump():
                    raise StudioError("VALIDATION", "Sequence frame rate is immutable")
                sequence.revision += 1
                sequence.name = doc.name
            for asset_id, media in measurements.items():
                row = session.get(Asset, asset_id)
                if row is None or row.project_id != command.project_id or row.sha256 != media["sha256"]:
                    raise StudioError("VALIDATION", "Registered Asset changed during save")
            document = doc.model_dump(mode="json")
            snap_digest = hashlib.sha256(canonical(document).encode()).hexdigest()
            session.add(
                EditingRevision(
                    project_id=command.project_id,
                    sequence_id=sequence.id,
                    revision=sequence.revision,
                    document=document,
                    sha256=snap_digest,
                )
            )
            authorize()
        return {"sequence_id": sequence.id, "revision": sequence.revision, "sha256": snap_digest}
