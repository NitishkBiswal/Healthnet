from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.rate_limit import identity_registration_limit
from app.audit.schemas import AuditEventCreate, AuditEventType
from app.audit.service import AuditService
from app.identity.models import DuplicateReview, PatientIdentity
from app.identity.schemas import (
    DuplicateReviewDecision,
    DuplicateReviewResponse,
    IdentityMergeRequest,
    LocationHistoryRequest,
    MatchCandidate,
    PatientRegistrationRequest,
    PatientResponse,
    RegistrationResult,
)
from app.identity.service import IdentityService
from app.identity_resolution.models import IdentityMatchConfiguration
from app.identity_resolution.schemas import (
    MatchConfigurationResponse,
    MatchConfigurationUpdate,
)
from app.identity_resolution.service import IdentityResolutionService
from app.security.dependencies import get_current_user
from app.security.rbac import Role

router = APIRouter(tags=["Identity"])


def _validate_match_configuration(configuration: MatchConfigurationUpdate) -> None:
    weights = (
        configuration.name_weight
        + configuration.date_of_birth_weight
        + configuration.sex_weight
        + configuration.phone_weight
        + configuration.email_weight
    )
    if weights <= 0:
        raise HTTPException(422, "At least one match weight must be greater than zero")
    if configuration.high_confidence <= configuration.medium_confidence:
        raise HTTPException(
            422, "High confidence threshold must exceed medium confidence threshold"
        )


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


@router.get(
    "/match-configuration", response_model=MatchConfigurationResponse
)
async def get_match_configuration(
    _: dict = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
) -> MatchConfigurationResponse:
    configuration = await session.get(IdentityMatchConfiguration, "default")
    if configuration is None:
        configuration = IdentityMatchConfiguration(config_key="default")
        session.add(configuration)
        await session.commit()
        await session.refresh(configuration)
    return MatchConfigurationResponse.model_validate(configuration)


@router.put(
    "/match-configuration", response_model=MatchConfigurationResponse
)
async def update_match_configuration(
    request: MatchConfigurationUpdate,
    _: dict = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
) -> MatchConfigurationResponse:
    _validate_match_configuration(request)
    configuration = await session.get(IdentityMatchConfiguration, "default")
    if configuration is None:
        configuration = IdentityMatchConfiguration(config_key="default")
        session.add(configuration)
    for key, value in request.model_dump().items():
        setattr(configuration, key, value)
    await session.commit()
    await session.refresh(configuration)
    return MatchConfigurationResponse.model_validate(configuration)


@router.post("/duplicate-reviews/recheck")
async def recheck_duplicate_candidates(
    _: dict = Depends(require_admin),
    session: AsyncSession = Depends(get_db),
) -> dict[str, int]:
    created = await IdentityResolutionService(session).recheck_existing_identities()
    await session.commit()
    return {"reviews_created": created}


@router.post(
    "/register",
    response_model=RegistrationResult,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(identity_registration_limit)],
)
async def register_patient(
    request: PatientRegistrationRequest,
    user: dict = Depends(require_patient_or_admin),
    session: AsyncSession = Depends(get_db),
) -> RegistrationResult:
    roles = set(user.get("roles", []))
    requesting_subject = str(user.get("sub")) if Role.PATIENT.value in roles else None
    outcome, patient, matches, review = await IdentityService(session).register_patient(
        request, requesting_subject=requesting_subject
    )
    await session.commit()
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
    return list(result.scalars().all())


@router.get("/duplicate-reviews/mine", response_model=list[DuplicateReviewResponse])
async def list_my_duplicate_reviews(
    user: dict = Depends(require_patient),
    session: AsyncSession = Depends(get_db),
) -> list[DuplicateReviewResponse]:
    reviews = await IdentityService(session).list_duplicate_reviews(str(user.get("sub")))
    return [DuplicateReviewResponse.model_validate(review) for review in reviews]


@router.post("/duplicate-reviews/{review_id}/decision", response_model=DuplicateReviewResponse)
async def decide_duplicate_review(
    review_id: UUID,
    decision: DuplicateReviewDecision,
    _: dict = Depends(require_auditor),
    session: AsyncSession = Depends(get_db),
) -> DuplicateReviewResponse:
    review = await IdentityService(session).decide_duplicate(
        review_id, decision.decision, decision.reviewer_note
    )
    if review is None:
        raise HTTPException(status_code=404, detail="Pending duplicate review not found")
    await session.commit()
    return DuplicateReviewResponse.model_validate(review)


@router.post("/merge", response_model=PatientResponse)
async def merge_identities(
    request: IdentityMergeRequest,
    user: dict = Depends(require_auditor),
    session: AsyncSession = Depends(get_db),
) -> PatientResponse:
    try:
        target = await IdentityService(session).merge_identities(
            request.source_patient_id,
            request.target_patient_id,
            str(user.get("sub", "unknown")),
            request.reviewer_note,
        )
        await AuditService(session).log_event(
            AuditEventCreate(
                event_type=AuditEventType.IDENTITY_MERGE,
                health_id=target.display_health_id,
                actor_id=str(user.get("sub", "unknown")),
                action="patient identities merged",
                payload={
                    "source_patient_id": str(request.source_patient_id),
                    "target_patient_id": str(request.target_patient_id),
                },
            )
        )
    except ValueError as exc:
        await session.rollback()
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


@router.get("/{health_id}", response_model=PatientResponse)
async def get_patient(
    health_id: str,
    user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> PatientResponse:
    patient = await IdentityService(session).get_patient_by_health_id(health_id)
    if patient is None:
        raise HTTPException(status_code=404, detail="Health ID not found")
    if Role.PATIENT.value in user.get("roles", []) and patient.owner_subject != str(user.get("sub")):
        approved = await session.scalar(
            select(DuplicateReview.id).where(
                DuplicateReview.requesting_subject == str(user.get("sub")),
                DuplicateReview.candidate_patient_id == patient.id,
                DuplicateReview.status == "APPROVED_DUPLICATE",
            )
        )
        if approved is None:
            raise HTTPException(status_code=403, detail="Patients can only access their own Health ID")
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
