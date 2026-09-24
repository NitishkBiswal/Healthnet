from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
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

router = APIRouter(tags=["Identity"])


@router.post("/register", response_model=RegistrationResult, status_code=status.HTTP_201_CREATED)
async def register_patient(
    request: PatientRegistrationRequest,
    session: AsyncSession = Depends(get_db),
) -> RegistrationResult:
    service = IdentityService(session)
    outcome, patient, matches, review = await service.register_patient(request)
    if outcome == "REGISTERED":
        await session.commit()
    elif review:
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
        patient=patient,
        matches=candidates,
        duplicate_review_id=review.id if review else None,
    )


@router.get("/{health_id}", response_model=PatientResponse)
async def get_patient(
    health_id: str,
    session: AsyncSession = Depends(get_db),
) -> PatientResponse:
    patient = await IdentityService(session).get_patient_by_health_id(health_id)
    if patient is None:
        raise HTTPException(status_code=404, detail="Health ID not found")
    return patient


@router.get("/{health_id}/identifiers")
async def get_patient_identifiers(
    health_id: str,
    session: AsyncSession = Depends(get_db),
) -> list[dict[str, str | None]]:
    service = IdentityService(session)
    patient = await service.get_patient_by_health_id(health_id)
    if patient is None:
        raise HTTPException(status_code=404, detail="Health ID not found")
    identifiers = await service.get_identifiers(patient.id)
    return [
        {
            "identifier_type": item.identifier_type,
            "identifier_value": item.identifier_value,
            "issuing_authority": item.issuing_authority,
        }
        for item in identifiers
    ]


@router.post("/{health_id}/locations", status_code=status.HTTP_201_CREATED)
async def add_location_history(
    health_id: str,
    request: LocationHistoryRequest,
    session: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    service = IdentityService(session)
    patient = await service.get_patient_by_health_id(health_id)
    if patient is None:
        raise HTTPException(status_code=404, detail="Health ID not found")
    await service.add_location(patient.id, request)
    await session.commit()
    return {"health_id": health_id, "status": "recorded"}


@router.get("/duplicate-reviews", response_model=list[DuplicateReviewResponse])
async def list_duplicate_reviews(
    session: AsyncSession = Depends(get_db),
) -> list[DuplicateReviewResponse]:
    from app.identity.models import DuplicateReview

    result = await session.execute(select(DuplicateReview).order_by(DuplicateReview.created_at.desc()))
    return list(result.scalars().all())


@router.post("/duplicate-reviews/{review_id}/decision", response_model=DuplicateReviewResponse)
async def decide_duplicate_review(
    review_id: UUID,
    decision: DuplicateReviewDecision,
    session: AsyncSession = Depends(get_db),
) -> DuplicateReviewResponse:
    review = await IdentityService(session).decide_duplicate(
        review_id, decision.decision, decision.reviewer_note
    )
    if review is None:
        raise HTTPException(status_code=404, detail="Pending duplicate review not found")
    await session.commit()
    return review


@router.post("/merge", response_model=PatientResponse)
async def merge_identities(
    request: IdentityMergeRequest,
    session: AsyncSession = Depends(get_db),
) -> PatientResponse:
    try:
        target = await IdentityService(session).merge_identities(
            request.source_patient_id, request.target_patient_id
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await session.commit()
    return target
