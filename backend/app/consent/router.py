from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.consent.schemas import ConsentCheckRequest, ConsentCreateRequest, ConsentResponse
from app.consent.service import ConsentService

router=APIRouter(tags=["Consent"])

def response(x):
    return ConsentResponse(id=x.id,health_id=x.health_id,grantee_type=x.grantee_type,grantee_id=x.grantee_id,purpose=x.purpose,
        scopes=x.scopes.split(",") if x.scopes else [],status=x.status,valid_from=x.valid_from,valid_until=x.valid_until,revoked_at=x.revoked_at,reason=x.reason)

@router.post("/consents",response_model=ConsentResponse,status_code=status.HTTP_201_CREATED)
async def create_consent(request:ConsentCreateRequest,session:AsyncSession=Depends(get_db)):
    try:x=await ConsentService(session).create_consent(request);await session.commit();return response(x)
    except ValueError as exc:raise HTTPException(400,str(exc)) from exc

@router.get("/consents/{consent_id}",response_model=ConsentResponse)
async def get_consent(consent_id:UUID,session:AsyncSession=Depends(get_db)):
    x=await ConsentService(session).get_consent(consent_id)
    if x is None:raise HTTPException(404,"Consent not found")
    return response(x)

@router.delete("/consents/{consent_id}",response_model=ConsentResponse)
async def revoke_consent(consent_id:UUID,session:AsyncSession=Depends(get_db)):
    x=await ConsentService(session).revoke_consent(consent_id)
    if x is None:raise HTTPException(404,"Consent not found")
    await session.commit();return response(x)

@router.get("/patients/{health_id}/consents",response_model=list[ConsentResponse])
async def get_patient_consents(health_id:str,session:AsyncSession=Depends(get_db)):
    return [response(x) for x in await ConsentService(session).get_patient_consents(health_id)]

@router.post("/consents/check")
async def check_consent(request:ConsentCheckRequest,session:AsyncSession=Depends(get_db)):
    allowed=await ConsentService(session).check_consent(request.health_id,request.grantee_id,request.purpose,request.scope,request.at)
    return {"allowed":allowed}
