from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.identity.models import (
    DuplicateReview,
    DuplicateReviewStatus,
    PatientIdentifier,
    PatientIdentity,
    PatientLocationHistory,
)
from app.identity.schemas import LocationHistoryRequest, PatientRegistrationRequest
from app.identity_resolution.models import IdentityMatch
from app.identity_resolution.service import (
    IdentityResolutionService,
    MatchThresholds,
)


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
    def _similarity(request: PatientRegistrationRequest, patient: PatientIdentity) -> float:
        return IdentityResolutionService._similarity(request, patient, MatchThresholds())

    async def match(self, request: PatientRegistrationRequest) -> list[MatchResult]:
        matches = await IdentityResolutionService(self.session).match(request)
        return [
            MatchResult(item.patient, item.confidence, item.band)
            for item in matches
        ]

    @staticmethod
    def health_id_prefix(jurisdiction: str) -> str:
        normalized = jurisdiction.upper().replace("-", "").replace("_", "")
        return normalized[:8]

    async def _next_health_id(self, jurisdiction: str) -> str:
        prefix = self.health_id_prefix(jurisdiction)
        result = await self.session.execute(text("SELECT nextval('healthnet.health_id_sequence')"))
        return f"{prefix}{int(result.scalar_one()):06d}"

    async def register_patient(
        self,
        request: PatientRegistrationRequest,
        requesting_subject: str | None = None,
    ) -> tuple[str, PatientIdentity | None, list[MatchResult], DuplicateReview | None]:
        if requesting_subject:
            existing = await self.session.scalar(
                select(PatientIdentity).where(PatientIdentity.owner_subject == requesting_subject)
            )
            if existing:
                return "ALREADY_REGISTERED", existing, [], None

        matches = await self.match(request)
        if matches:
            top = matches[0]
            outcome = (
                "DUPLICATE_REVIEW" if top.band == "MEDIUM" else "LIKELY_DUPLICATE"
            )
            review = None
            if top.band == "MEDIUM":
                review = await IdentityResolutionService(
                    self.session
                ).flag_for_adjudication(
                    request,
                    top,
                    requesting_subject,
                )
            for match in matches:
                self.session.add(
                    IdentityMatch(
                        candidate_health_id=match.patient.display_health_id,
                        match_method=(
                            "DETERMINISTIC"
                            if match.confidence == 1.0
                            else "PROBABILISTIC"
                        ),
                        confidence=match.confidence,
                        band=match.band,
                        outcome=outcome,
                        duplicate_review_id=review.id if review else None,
                    )
                )
            await self.session.flush()
            if outcome == "DUPLICATE_REVIEW":
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
            owner_subject=requesting_subject,
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
        result = await self.session.execute(select(PatientIdentity).where(PatientIdentity.display_health_id == health_id))
        return result.scalar_one_or_none()

    async def get_identifiers(self, patient_id: UUID) -> list[PatientIdentifier]:
        result = await self.session.execute(select(PatientIdentifier).where(PatientIdentifier.patient_id == patient_id))
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

    async def list_duplicate_reviews(self, requesting_subject: str | None = None) -> list[DuplicateReview]:
        stmt = select(DuplicateReview).order_by(DuplicateReview.created_at.desc())
        if requesting_subject:
            stmt = stmt.where(DuplicateReview.requesting_subject == requesting_subject)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def decide_duplicate(self, review_id: UUID, decision: str, reviewer_note: str | None) -> DuplicateReview | None:
        review = await self.session.get(DuplicateReview, review_id)
        if review is None or review.status != DuplicateReviewStatus.PENDING.value:
            return None
        review.status = decision
        review.reviewer_note = reviewer_note
        review.reviewed_at = datetime.now(UTC)
        return review

    async def merge_identities(
        self,
        source_patient_id: UUID,
        target_patient_id: UUID,
        authorized_by: str = "system",
        reviewer_note: str | None = None,
    ) -> PatientIdentity:
        return await IdentityResolutionService(self.session).merge_identities(
            source_patient_id, target_patient_id, authorized_by, reviewer_note
        )
