from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from difflib import SequenceMatcher
from uuid import UUID

from sqlalchemy import func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.identity.models import (
    DuplicateReview,
    DuplicateReviewStatus,
    IdentityStatus,
    PatientIdentifier,
    PatientIdentity,
    PatientLocationHistory,
)
from app.identity.schemas import LocationHistoryRequest, PatientRegistrationRequest


@dataclass(frozen=True)
class MatchResult:
    patient: PatientIdentity
    confidence: float
    band: str


class IdentityService:
    HIGH_CONFIDENCE = 0.90
    MEDIUM_CONFIDENCE = 0.70

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @staticmethod
    def _normalise(value: str | None) -> str:
        return "".join((value or "").lower().split())

    @classmethod
    def _similarity(cls, request: PatientRegistrationRequest, patient: PatientIdentity) -> float:
        name = SequenceMatcher(
            None,
            cls._normalise(f"{request.given_name}{request.family_name}"),
            cls._normalise(f"{patient.given_name}{patient.family_name}"),
        ).ratio()
        dob = float(request.date_of_birth == patient.date_of_birth)
        sex = float(bool(request.sex and patient.sex and cls._normalise(request.sex) == cls._normalise(patient.sex)))
        phone = float(bool(request.phone and patient.phone and cls._normalise(request.phone) == cls._normalise(patient.phone)))
        email = float(bool(request.email and patient.email and cls._normalise(request.email) == cls._normalise(patient.email)))
        return round((name * 0.45) + (dob * 0.30) + (sex * 0.05) + (phone * 0.10) + (email * 0.10), 4)

    async def _find_deterministic_match(self, request: PatientRegistrationRequest) -> PatientIdentity | None:
        for identifier in request.identifiers:
            result = await self.session.execute(
                select(PatientIdentity)
                .join(PatientIdentifier, PatientIdentifier.patient_id == PatientIdentity.id)
                .where(
                    PatientIdentity.status == IdentityStatus.ACTIVE.value,
                    PatientIdentifier.identifier_type == identifier.identifier_type,
                    func.lower(PatientIdentifier.identifier_value) == self._normalise(identifier.identifier_value),
                    PatientIdentity.date_of_birth == request.date_of_birth,
                )
                .limit(1)
            )
            patient = result.scalar_one_or_none()
            if patient:
                return patient
        return None

    async def _candidate_patients(self, request: PatientRegistrationRequest) -> list[PatientIdentity]:
        result = await self.session.execute(
            select(PatientIdentity)
            .where(
                PatientIdentity.status == IdentityStatus.ACTIVE.value,
                or_(
                    PatientIdentity.date_of_birth == request.date_of_birth,
                    func.lower(PatientIdentity.family_name) == self._normalise(request.family_name),
                ),
            )
            .limit(100)
        )
        return list(result.scalars().all())

    async def match(self, request: PatientRegistrationRequest) -> list[MatchResult]:
        deterministic = await self._find_deterministic_match(request)
        if deterministic:
            return [MatchResult(deterministic, 1.0, "HIGH")]
        matches = []
        for patient in await self._candidate_patients(request):
            confidence = self._similarity(request, patient)
            if confidence >= self.MEDIUM_CONFIDENCE:
                band = "HIGH" if confidence >= self.HIGH_CONFIDENCE else "MEDIUM"
                matches.append(MatchResult(patient, confidence, band))
        return sorted(matches, key=lambda item: item.confidence, reverse=True)

    @staticmethod
    def health_id_prefix(jurisdiction: str) -> str:
        normalized = jurisdiction.upper().replace("-", "").replace("_", "")
        return normalized[:8]

    async def _next_health_id(self, jurisdiction: str) -> str:
        prefix = self.health_id_prefix(jurisdiction)
        result = await self.session.execute(
            text("SELECT nextval('healthnet.health_id_sequence')")
        )
        number = int(result.scalar_one())
        return f"{prefix}{number:06d}"

    async def register_patient(
        self, request: PatientRegistrationRequest
    ) -> tuple[str, PatientIdentity | None, list[MatchResult], DuplicateReview | None]:
        matches = await self.match(request)
        if matches:
            top = matches[0]
            review = None
            if top.band == "MEDIUM":
                review = DuplicateReview(
                    candidate_patient_id=top.patient.id,
                    proposed_given_name=request.given_name,
                    proposed_family_name=request.family_name,
                    proposed_date_of_birth=request.date_of_birth,
                    proposed_sex=request.sex,
                    proposed_phone=request.phone,
                    proposed_email=request.email,
                    confidence=top.confidence,
                )
                self.session.add(review)
                await self.session.flush()
                return "DUPLICATE_REVIEW", None, matches, review
            return "LIKELY_DUPLICATE", None, matches, None

        patient = PatientIdentity(
            display_health_id=await self._next_health_id(request.issuing_jurisdiction),
            issuing_jurisdiction=request.issuing_jurisdiction,
            given_name=request.given_name,
            family_name=request.family_name,
            date_of_birth=request.date_of_birth,
            sex=request.sex,
            phone=request.phone,
            email=request.email,
            address=request.address,
        )
        self.session.add(patient)
        await self.session.flush()
        for identifier in request.identifiers:
            self.session.add(
                PatientIdentifier(
                    patient_id=patient.id,
                    identifier_type=identifier.identifier_type,
                    identifier_value=identifier.identifier_value,
                    issuing_authority=identifier.issuing_authority,
                )
            )
        await self.session.flush()
        return "REGISTERED", patient, [], None

    async def get_patient_by_health_id(self, health_id: str) -> PatientIdentity | None:
        result = await self.session.execute(
            select(PatientIdentity).where(PatientIdentity.display_health_id == health_id)
        )
        return result.scalar_one_or_none()

    async def get_identifiers(self, patient_id: UUID) -> list[PatientIdentifier]:
        result = await self.session.execute(
            select(PatientIdentifier).where(PatientIdentifier.patient_id == patient_id)
        )
        return list(result.scalars().all())

    async def add_location(self, patient_id: UUID, request: LocationHistoryRequest) -> PatientLocationHistory:
        location = PatientLocationHistory(
            patient_id=patient_id,
            jurisdiction=request.jurisdiction,
            movement_type=request.movement_type,
            started_at=request.started_at,
            ended_at=request.ended_at,
        )
        self.session.add(location)
        await self.session.flush()
        return location

    async def decide_duplicate(
        self, review_id: UUID, decision: str, reviewer_note: str | None
    ) -> DuplicateReview | None:
        review = await self.session.get(DuplicateReview, review_id)
        if review is None or review.status != DuplicateReviewStatus.PENDING.value:
            return None
        review.status = decision
        review.reviewer_note = reviewer_note
        review.reviewed_at = datetime.now(timezone.utc)
        return review

    async def merge_identities(self, source_patient_id: UUID, target_patient_id: UUID) -> PatientIdentity:
        if source_patient_id == target_patient_id:
            raise ValueError("Source and target identities must differ")
        source = await self.session.get(PatientIdentity, source_patient_id)
        target = await self.session.get(PatientIdentity, target_patient_id)
        if source is None or target is None:
            raise ValueError("Both identities must exist")
        if source.status != IdentityStatus.ACTIVE.value or target.status != IdentityStatus.ACTIVE.value:
            raise ValueError("Both identities must be active")
        source.status = IdentityStatus.SUPERSEDED.value
        source.superseded_by = target.id
        return target
