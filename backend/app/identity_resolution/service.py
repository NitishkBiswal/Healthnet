from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher

from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.identity.models import (
    DuplicateReview,
    IdentityStatus,
    PatientIdentity,
    PatientIdentifier,
    PatientLocationHistory,
)
from app.identity.schemas import PatientRegistrationRequest
from app.identity_resolution.models import (
    IdentityMatch,
    IdentityMatchConfiguration,
    IdentityMergeEvent,
)


@dataclass(frozen=True)
class MatchThresholds:
    name_weight: float = 0.45
    date_of_birth_weight: float = 0.30
    sex_weight: float = 0.05
    phone_weight: float = 0.10
    email_weight: float = 0.10
    medium_confidence: float = 0.70
    high_confidence: float = 0.90


@dataclass(frozen=True)
class MatchResult:
    patient: PatientIdentity
    confidence: float
    band: str


class IdentityResolutionService:
    def __init__(self, session: AsyncSession):
        self.session = session

    @staticmethod
    def _normalise(value: str | None) -> str:
        return "".join((value or "").casefold().split())

    @staticmethod
    def soundex(value: str | None) -> str:
        normalized = "".join(char for char in (value or "").upper() if char.isalpha())
        if not normalized:
            return ""
        codes = {
            **dict.fromkeys("BFPV", "1"),
            **dict.fromkeys("CGJKQSXZ", "2"),
            **dict.fromkeys("DT", "3"),
            "L": "4",
            **dict.fromkeys("MN", "5"),
            "R": "6",
        }
        result = [normalized[0]]
        previous = codes.get(normalized[0], "")
        for char in normalized[1:]:
            code = codes.get(char, "")
            if code and code != previous:
                result.append(code)
            if code:
                previous = code
            elif char not in "HW":
                previous = ""
            if len(result) == 4:
                break
        return "".join(result).ljust(4, "0")

    @classmethod
    def _similarity(
        cls,
        request: PatientRegistrationRequest,
        patient: PatientIdentity,
        thresholds: MatchThresholds | None = None,
    ) -> float:
        thresholds = thresholds or MatchThresholds()
        request_name = f"{request.given_name} {request.family_name}"
        patient_name = f"{patient.given_name} {patient.family_name}"
        lexical = SequenceMatcher(
            None, cls._normalise(request_name), cls._normalise(patient_name)
        ).ratio()
        request_given = cls.soundex(request.given_name)
        request_family = cls.soundex(request.family_name)
        patient_given = cls.soundex(patient.given_name)
        patient_family = cls.soundex(patient.family_name)
        phonetic = float(
            bool(request_given and request_family)
            and request_given == patient_given
            and request_family == patient_family
        )
        name = (0.8 * lexical) + (0.2 * phonetic)
        dob = float(request.date_of_birth == patient.date_of_birth)
        sex = float(
            bool(
                request.sex
                and patient.sex
                and cls._normalise(request.sex) == cls._normalise(patient.sex)
            )
        )
        phone = float(
            bool(
                request.phone
                and patient.phone
                and cls._normalise(request.phone) == cls._normalise(patient.phone)
            )
        )
        email = float(
            bool(
                request.email
                and patient.email
                and cls._normalise(request.email) == cls._normalise(patient.email)
            )
        )
        total_weight = (
            thresholds.name_weight
            + thresholds.date_of_birth_weight
            + thresholds.sex_weight
            + thresholds.phone_weight
            + thresholds.email_weight
        )
        if total_weight <= 0:
            raise ValueError("Identity match weights must sum to a positive value")
        score = (
            name * thresholds.name_weight
            + dob * thresholds.date_of_birth_weight
            + sex * thresholds.sex_weight
            + phone * thresholds.phone_weight
            + email * thresholds.email_weight
        ) / total_weight
        return round(score, 4)

    async def get_thresholds(self) -> MatchThresholds:
        row = await self.session.get(IdentityMatchConfiguration, "default")
        if row is None:
            return MatchThresholds()
        return MatchThresholds(
            name_weight=row.name_weight,
            date_of_birth_weight=row.date_of_birth_weight,
            sex_weight=row.sex_weight,
            phone_weight=row.phone_weight,
            email_weight=row.email_weight,
            medium_confidence=row.medium_confidence,
            high_confidence=row.high_confidence,
        )

    async def _find_deterministic_match(
        self, request: PatientRegistrationRequest
    ) -> PatientIdentity | None:
        for identifier in request.identifiers:
            patient = await self.session.scalar(
                select(PatientIdentity)
                .join(
                    PatientIdentifier,
                    PatientIdentifier.patient_id == PatientIdentity.id,
                )
                .where(
                    PatientIdentity.status == IdentityStatus.ACTIVE.value,
                    PatientIdentifier.identifier_type == identifier.identifier_type,
                    func.lower(PatientIdentifier.identifier_value)
                    == self._normalise(identifier.identifier_value),
                    PatientIdentity.date_of_birth == request.date_of_birth,
                )
                .limit(1)
            )
            if patient is not None:
                return patient
        return None

    async def _candidate_patients(
        self, request: PatientRegistrationRequest
    ) -> list[PatientIdentity]:
        result = await self.session.scalars(
            select(PatientIdentity)
            .where(
                PatientIdentity.status == IdentityStatus.ACTIVE.value,
                or_(
                    PatientIdentity.date_of_birth == request.date_of_birth,
                    func.lower(PatientIdentity.family_name)
                    == self._normalise(request.family_name),
                ),
            )
            .limit(100)
        )
        return list(result.all())

    async def match(
        self, request: PatientRegistrationRequest
    ) -> list[MatchResult]:
        deterministic = await self.deterministic_match(request)
        if deterministic is not None:
            return [deterministic]
        return await self.probabilistic_match(request)

    async def deterministic_match(
        self, request: PatientRegistrationRequest
    ) -> MatchResult | None:
        patient = await self._find_deterministic_match(request)
        return MatchResult(patient, 1.0, "HIGH") if patient is not None else None

    async def probabilistic_match(
        self, request: PatientRegistrationRequest
    ) -> list[MatchResult]:
        thresholds = await self.get_thresholds()
        matches = []
        for patient in await self._candidate_patients(request):
            confidence = self._similarity(request, patient, thresholds)
            if confidence >= thresholds.medium_confidence:
                band = (
                    "HIGH"
                    if confidence >= thresholds.high_confidence
                    else "MEDIUM"
                )
                matches.append(MatchResult(patient, confidence, band))
        return sorted(matches, key=lambda match: match.confidence, reverse=True)

    async def flag_for_adjudication(
        self,
        request: PatientRegistrationRequest,
        match: MatchResult,
        requesting_subject: str | None,
    ) -> DuplicateReview:
        review = DuplicateReview(
            candidate_patient_id=match.patient.id,
            requesting_subject=requesting_subject,
            proposed_given_name=request.given_name,
            proposed_family_name=request.family_name,
            proposed_date_of_birth=request.date_of_birth,
            proposed_sex=request.sex,
            proposed_phone=request.phone,
            proposed_email=request.email,
            proposed_issuing_jurisdiction=request.issuing_jurisdiction,
            proposed_identifiers=[
                identifier.model_dump(mode="json")
                for identifier in request.identifiers
            ],
            confidence=match.confidence,
        )
        self.session.add(review)
        await self.session.flush()
        return review

    async def merge_identities(
        self,
        source_patient_id,
        target_patient_id,
        authorized_by: str,
        reviewer_note: str | None = None,
    ) -> PatientIdentity:
        if source_patient_id == target_patient_id:
            raise ValueError("Source and target identities must differ")
        source = await self.session.get(PatientIdentity, source_patient_id)
        target = await self.session.get(PatientIdentity, target_patient_id)
        if source is None or target is None:
            raise ValueError("Both identities must exist")
        if (
            source.status != IdentityStatus.ACTIVE.value
            or target.status != IdentityStatus.ACTIVE.value
        ):
            raise ValueError("Both identities must be active")
        await self.session.execute(
            update(PatientIdentifier)
            .where(PatientIdentifier.patient_id == source.id)
            .values(patient_id=target.id)
        )
        await self.session.execute(
            update(PatientLocationHistory)
            .where(PatientLocationHistory.patient_id == source.id)
            .values(patient_id=target.id)
        )
        source.status = IdentityStatus.SUPERSEDED.value
        source.superseded_by = target.id
        self.session.add(
            IdentityMergeEvent(
                source_patient_id=source.id,
                source_health_id=source.display_health_id,
                target_patient_id=target.id,
                target_health_id=target.display_health_id,
                authorized_by=authorized_by,
                reviewer_note=reviewer_note,
            )
        )
        await self.session.flush()
        return target

    async def recheck_existing_identities(self, batch_size: int = 5000) -> int:
        from sqlalchemy.orm import aliased

        left = aliased(PatientIdentity)
        right = aliased(PatientIdentity)
        pairs = await self.session.execute(
            select(left, right)
            .where(
                left.id < right.id,
                left.status == IdentityStatus.ACTIVE.value,
                right.status == IdentityStatus.ACTIVE.value,
                or_(
                    left.date_of_birth == right.date_of_birth,
                    func.lower(left.family_name) == func.lower(right.family_name),
                ),
            )
            .limit(batch_size)
        )
        thresholds = await self.get_thresholds()
        created = 0
        for candidate, existing in pairs:
            request = PatientRegistrationRequest(
                given_name=candidate.given_name,
                family_name=candidate.family_name,
                date_of_birth=candidate.date_of_birth,
                sex=candidate.sex,
                phone=candidate.phone,
                email=candidate.email,
                issuing_jurisdiction=candidate.issuing_jurisdiction,
            )
            confidence = self._similarity(request, existing, thresholds)
            if confidence < thresholds.medium_confidence:
                continue
            already_reviewed = await self.session.scalar(
                select(DuplicateReview.id).where(
                    DuplicateReview.candidate_patient_id == existing.id,
                    DuplicateReview.proposed_given_name == candidate.given_name,
                    DuplicateReview.proposed_family_name == candidate.family_name,
                    DuplicateReview.proposed_date_of_birth == candidate.date_of_birth,
                    DuplicateReview.status == "PENDING",
                )
            )
            if already_reviewed is not None:
                continue
            self.session.add(
                DuplicateReview(
                    candidate_patient_id=existing.id,
                    proposed_given_name=candidate.given_name,
                    proposed_family_name=candidate.family_name,
                    proposed_date_of_birth=candidate.date_of_birth,
                    proposed_sex=candidate.sex,
                    proposed_phone=candidate.phone,
                    proposed_email=candidate.email,
                    proposed_issuing_jurisdiction=candidate.issuing_jurisdiction,
                    proposed_identifiers=[],
                    requesting_subject=candidate.owner_subject,
                    confidence=confidence,
                )
            )
            self.session.add(
                IdentityMatch(
                    candidate_health_id=existing.display_health_id,
                    match_method="BATCH_PROBABILISTIC",
                    confidence=confidence,
                    band="HIGH" if confidence >= thresholds.high_confidence else "MEDIUM",
                    outcome="DUPLICATE_REVIEW",
                )
            )
            created += 1
        await self.session.flush()
        return created
