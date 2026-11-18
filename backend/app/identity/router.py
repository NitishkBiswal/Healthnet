from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.identity.models import DuplicateReview, PatientIdentity
from app.identity.identifiers import encrypt_aadhaar
from app.audit.schemas import AuditEventCreate, AuditEventType
from app.audit.service import AuditService
from app.identity.schemas import (
    AadhaarStatusResponse,
    AadhaarUpdateRequest,
    DuplicateReviewDecision,
    DuplicateReviewResponse,
    IdentityMergeRequest,
    LocationHistoryRequest,
    MatchCandidate,
    PatientRegistrationRequest,
    PatientProfileUpdate,
    ProfileUpdateResult,
    PatientResponse,
    RegistrationResult,
)
from app.identity.service import IdentityService
from app.consent.models import Consent
from app.provider_trust.models import Provider
from app.security.dependencies import get_current_user
from app.security.rbac import Role

router = APIRouter(tags=["Identity"])


async def require_admin(user: dict = Depends(get_current_user)) -> dict:
    if Role.ADMIN.value not in user.get("roles", []):
        raise HTTPException(status_code=403, detail="Role ADMIN required")
    return user


async def require_patient(user: dict = Depends(get_current_user)) -> dict:
    if Role.PATIENT.value not in user.get("roles", []):
        raise HTTPException(status_code=403, detail="Role PATIENT required")
    return user


async def require_patient_or_admin(user: dict = Depends(get_current_user)) -> dict:
    roles = set(user.get("roles", []))
    if Role.PATIENT.value not in roles and Role.ADMIN.value not in roles:
        raise HTTPException(status_code=403, detail="Patient or admin role required")
    return user

async def require_auditor(user: dict = Depends(get_current_user)) -> dict:
    if Role.AUDITOR.value not in user.get("roles", []):
        raise HTTPException(status_code=403, detail="Role AUDITOR required")
    return user


@router.post("/register", response_model=RegistrationResult, status_code=status.HTTP_201_CREATED)
async def register_patient(
    request: PatientRegistrationRequest,
    user: dict = Depends(require_patient_or_admin),
    session: AsyncSession = Depends(get_db),
) -> RegistrationResult:
    roles = set(user.get("roles", []))
    requesting_subject = str(user.get("sub")) if Role.PATIENT.value in roles else None
    try:
        outcome, patient, matches, review = await IdentityService(session).register_patient(
            request, requesting_subject=requesting_subject
        )
        await session.commit()
    except ValueError as exc:
        await session.rollback()
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    candidates = [
        MatchCandidate(
            patient_id=item.patient.id,
            health_id=item.patient.display_health_id,
            confidence=item.confidence,
            band=item.band,
        )
        for item in matches
    ]
    return RegistrationResult(
        outcome=outcome,
        patient=PatientResponse.model_validate(patient) if patient else None,
        matches=candidates,
        duplicate_review_id=review.id if review else None,
    )


@router.get("/duplicate-reviews", response_model=list[DuplicateReviewResponse])
async def list_duplicate_reviews(
    _: dict = Depends(require_auditor),
    session: AsyncSession = Depends(get_db),
) -> list[DuplicateReviewResponse]:
    result = await session.execute(
        select(DuplicateReview).order_by(DuplicateReview.created_at.desc())
    )
    reviews = list(result.scalars().all())
    responses: list[DuplicateReviewResponse] = []
    for review in reviews:
        response = DuplicateReviewResponse.model_validate(review).model_dump()
        candidate = await session.get(PatientIdentity, review.candidate_patient_id)
        target = await session.get(PatientIdentity, review.target_patient_id) if review.target_patient_id else None
        response["candidate_health_id"] = candidate.display_health_id if candidate else None
        response["target_health_id"] = target.display_health_id if target else None
        responses.append(DuplicateReviewResponse.model_validate(response))
    return responses


@router.get("/duplicate-reviews/mine", response_model=list[DuplicateReviewResponse])
async def list_my_duplicate_reviews(
    user: dict = Depends(require_patient),
    session: AsyncSession = Depends(get_db),
) -> list[DuplicateReviewResponse]:
    reviews = await IdentityService(session).list_duplicate_reviews(str(user.get("sub")))
    return [DuplicateReviewResponse.model_validate(item) for item in reviews]


@router.post("/duplicate-reviews/{review_id}/decision", response_model=DuplicateReviewResponse)
async def decide_duplicate_review(
    review_id: UUID,
    decision: DuplicateReviewDecision,
    user: dict = Depends(require_auditor),
    session: AsyncSession = Depends(get_db),
) -> DuplicateReviewResponse:
    review = await IdentityService(session).decide_duplicate(
        review_id, decision.decision, decision.reviewer_note
    )
    if review is None:
        raise HTTPException(status_code=404, detail="Pending duplicate review not found")
    if review.review_type == "PROFILE_UPDATE" and review.target_patient_id is not None:
        patient = await session.get(PatientIdentity, review.target_patient_id)
        if patient is not None:
            await AuditService(session).log_event(
                AuditEventCreate(
                    event_type=AuditEventType.ACCESS,
                    health_id=patient.display_health_id,
                    actor_id=str(user.get("sub", "unknown")),
                    action="PATIENT_PROFILE_UPDATE_" + ("APPROVED" if decision.decision == "APPROVED_PROFILE_UPDATE" else "REJECTED"),
                    payload={"review_id": str(review.id), "reviewer_note": decision.reviewer_note},
                )
            )
    await session.commit()
    return DuplicateReviewResponse.model_validate(review)


@router.post("/merge", response_model=PatientResponse)
async def merge_identities(
    request: IdentityMergeRequest,
    _: dict = Depends(require_auditor),
    session: AsyncSession = Depends(get_db),
) -> PatientResponse:
    try:
        target = await IdentityService(session).merge_identities(
            request.source_patient_id, request.target_patient_id
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await session.commit()
    return PatientResponse.model_validate(target)


@router.get("/me", response_model=PatientResponse)
async def get_my_patient(
    user: dict = Depends(require_patient),
    session: AsyncSession = Depends(get_db),
) -> PatientResponse:
    subject = str(user.get("sub"))
    patient = await session.scalar(
        select(PatientIdentity).where(PatientIdentity.owner_subject == subject)
    )
    if patient is None:
        approved_review = await session.scalar(
            select(DuplicateReview)
            .where(
                DuplicateReview.requesting_subject == subject,
                DuplicateReview.status == "APPROVED_DUPLICATE",
            )
            .order_by(DuplicateReview.reviewed_at.desc())
        )
        if approved_review is not None:
            patient = await session.get(PatientIdentity, approved_review.candidate_patient_id)
    if patient is None:
        raise HTTPException(status_code=404, detail="No Health ID is linked to this account")
    return PatientResponse.model_validate(patient)




@router.put("/me/profile", response_model=ProfileUpdateResult)
async def update_my_profile(
    request: PatientProfileUpdate,
    user: dict = Depends(require_patient),
    session: AsyncSession = Depends(get_db),
) -> ProfileUpdateResult:
    subject = str(user.get("sub"))
    patient = await session.scalar(
        select(PatientIdentity).where(PatientIdentity.owner_subject == subject)
    )
    if patient is None:
        approved_review = await session.scalar(
            select(DuplicateReview)
            .where(
                DuplicateReview.requesting_subject == subject,
                DuplicateReview.status == "APPROVED_DUPLICATE",
                DuplicateReview.review_type == "DUPLICATE_REGISTRATION",
            )
            .order_by(DuplicateReview.reviewed_at.desc())
        )
        if approved_review is not None:
            patient = await session.get(PatientIdentity, approved_review.candidate_patient_id)
    if patient is None:
        raise HTTPException(status_code=404, detail="No Health ID is linked to this account")

    pending_review = await session.scalar(
        select(DuplicateReview.id).where(
            DuplicateReview.requesting_subject == subject,
            DuplicateReview.review_type == "PROFILE_UPDATE",
            DuplicateReview.status == "PENDING",
        ).limit(1)
    )
    if pending_review is not None:
        raise HTTPException(
            status_code=409,
            detail="A profile update is already waiting for Auditor review",
        )

    match_request = PatientRegistrationRequest(
        given_name=request.given_name,
        family_name=request.family_name,
        date_of_birth=request.date_of_birth,
        sex=request.sex,
        phone=request.phone,
        email=request.email,
        address=request.address,
        issuing_jurisdiction=patient.issuing_jurisdiction,
    )
    matches = [
        item for item in await IdentityService(session).match(match_request)
        if item.patient.id != patient.id
    ]
    if matches:
        candidate = matches[0]
        review = DuplicateReview(
            review_type="PROFILE_UPDATE",
            target_patient_id=patient.id,
            candidate_patient_id=candidate.patient.id,
            requesting_subject=subject,
            proposed_given_name=request.given_name.strip(),
            proposed_family_name=request.family_name.strip(),
            proposed_date_of_birth=request.date_of_birth,
            proposed_sex=request.sex.strip() if request.sex and request.sex.strip() else None,
            proposed_phone=request.phone.strip() if request.phone and request.phone.strip() else None,
            proposed_email=request.email.strip() if request.email and request.email.strip() else None,
            proposed_address=request.address.strip() if request.address and request.address.strip() else None,
            proposed_issuing_jurisdiction=patient.issuing_jurisdiction,
            confidence=candidate.confidence,
        )
        session.add(review)
        await session.flush()
        await AuditService(session).log_event(
            AuditEventCreate(
                event_type=AuditEventType.ACCESS,
                health_id=patient.display_health_id,
                actor_id=subject,
                action="PATIENT_PROFILE_UPDATE_SUBMITTED_FOR_REVIEW",
                payload={"review_id": str(review.id), "candidate_health_id": candidate.patient.display_health_id},
            )
        )
        await session.commit()
        return ProfileUpdateResult(outcome="PENDING_REVIEW", duplicate_review_id=review.id)

    patient.given_name = request.given_name.strip()
    patient.family_name = request.family_name.strip()
    patient.date_of_birth = request.date_of_birth
    patient.sex = request.sex.strip() if request.sex and request.sex.strip() else None
    patient.phone = request.phone.strip() if request.phone and request.phone.strip() else None
    patient.email = request.email.strip() if request.email and request.email.strip() else None
    patient.address = request.address.strip() if request.address and request.address.strip() else None
    await AuditService(session).log_event(
        AuditEventCreate(
            event_type=AuditEventType.ACCESS,
            health_id=patient.display_health_id,
            actor_id=subject,
            action="PATIENT_PROFILE_UPDATED",
            payload={"fields": ["given_name", "family_name", "date_of_birth", "sex", "phone", "email", "address"]},
        )
    )
    await session.commit()
    await session.refresh(patient)
    return ProfileUpdateResult(outcome="UPDATED", patient=PatientResponse.model_validate(patient))


@router.get("/me/aadhaar", response_model=AadhaarStatusResponse)
async def get_my_aadhaar_status(
    user: dict = Depends(require_patient),
    session: AsyncSession = Depends(get_db),
) -> AadhaarStatusResponse:
    patient = await session.scalar(
        select(PatientIdentity).where(PatientIdentity.owner_subject == str(user.get("sub")))
    )
    if patient is None:
        raise HTTPException(status_code=404, detail="No Health ID is linked to this account")
    return AadhaarStatusResponse(
        has_aadhaar=bool(patient.aadhaar_encrypted),
        masked_value=f"XXXX-XXXX-{patient.aadhaar_last4}" if patient.aadhaar_last4 else None,
    )


@router.put("/me/aadhaar", response_model=AadhaarStatusResponse)
async def update_my_aadhaar(
    request: AadhaarUpdateRequest,
    user: dict = Depends(require_patient),
    session: AsyncSession = Depends(get_db),
) -> AadhaarStatusResponse:
    patient = await session.scalar(
        select(PatientIdentity).where(PatientIdentity.owner_subject == str(user.get("sub")))
    )
    if patient is None:
        raise HTTPException(status_code=404, detail="No Health ID is linked to this account")

    value = request.aadhaar_number.get_secret_value()
    patient.aadhaar_encrypted = encrypt_aadhaar(value)
    patient.aadhaar_last4 = value[-4:]
    await AuditService(session).log_event(
        AuditEventCreate(
            event_type=AuditEventType.ACCESS,
            health_id=patient.display_health_id,
            actor_id=str(user.get("sub", "unknown")),
            action="AADHAAR_IDENTIFIER_UPDATED",
            payload={"identifier_type": "AADHAAR", "masked_value": f"XXXX-XXXX-{value[-4:]}"},
        )
    )
    await session.commit()
    return AadhaarStatusResponse(has_aadhaar=True, masked_value=f"XXXX-XXXX-{value[-4:]}")


@router.get("/{health_id}", response_model=PatientResponse)
async def get_patient(
    health_id: str,
    user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> PatientResponse:
    patient = await IdentityService(session).get_patient_by_health_id(health_id)
    if patient is None:
        raise HTTPException(status_code=404, detail="Health ID not found")
    roles = set(user.get("roles", []))
    subject = str(user.get("sub", ""))

    if Role.PATIENT.value in roles and Role.PROVIDER.value not in roles and patient.owner_subject != subject:
        approved = await session.scalar(
            select(DuplicateReview.id).where(
                DuplicateReview.requesting_subject == subject,
                DuplicateReview.candidate_patient_id == patient.id,
                DuplicateReview.status == "APPROVED_DUPLICATE",
            )
        )
        if approved is None:
            raise HTTPException(status_code=403, detail="Patients can only access their own Health ID")

    # Provider accounts may load demographics only when an active trusted
    # provider record is linked to their login and the patient has granted
    # that provider active consent. Longitudinal clinical data still passes
    # through its stricter purpose-and-scope authorization check.
    if Role.PROVIDER.value in roles:
        provider = await session.scalar(
            select(Provider).where(
                Provider.keycloak_subject == subject,
                Provider.trust_status == "ACTIVE",
            )
        )
        now = datetime.now(UTC)
        consent = None
        if provider is not None:
            consent = await session.scalar(
                select(Consent.id).where(
                    Consent.health_id == health_id,
                    Consent.grantee_type == "PROVIDER",
                    Consent.grantee_id == provider.external_id,
                    Consent.status == "ACTIVE",
                    Consent.valid_from <= now,
                    (Consent.valid_until.is_(None) | (Consent.valid_until >= now)),
                ).limit(1)
            )
        if consent is None:
            raise HTTPException(
                status_code=403,
                detail="No active patient consent is linked to this provider account",
            )

    return PatientResponse.model_validate(patient)


@router.get("/{health_id}/identifiers")
async def get_patient_identifiers(
    health_id: str,
    user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> list[dict[str, str | None]]:
    service = IdentityService(session)
    patient = await service.get_patient_by_health_id(health_id)
    if patient is None:
        raise HTTPException(status_code=404, detail="Health ID not found")
    if Role.PATIENT.value in user.get("roles", []) and patient.owner_subject != str(user.get("sub")):
        raise HTTPException(status_code=403, detail="Patients can only access their own identifiers")
    return [
        {
            "identifier_type": item.identifier_type,
            "identifier_value": item.identifier_value,
            "issuing_authority": item.issuing_authority,
        }
        for item in await service.get_identifiers(patient.id)
    ]


@router.post("/{health_id}/locations", status_code=status.HTTP_201_CREATED)
async def add_location_history(
    health_id: str,
    request: LocationHistoryRequest,
    _: dict = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    service = IdentityService(session)
    patient = await service.get_patient_by_health_id(health_id)
    if patient is None:
        raise HTTPException(status_code=404, detail="Health ID not found")
    await service.add_location(patient.id, request)
    await session.commit()
    return {"health_id": health_id, "status": "recorded"}
