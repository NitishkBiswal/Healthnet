"""API v1 aggregating router — domain modules."""
from fastapi import APIRouter
from app.audit.router import router as audit_router
from app.authorization.router import router as authorization_router
from app.consent.router import router as consent_router
from app.emergency.router import router as emergency_router
from app.fhir.router import router as fhir_router
from app.identity.router import router as identity_router
from app.jurisdiction_policy.router import router as jurisdiction_policy_router
from app.longitudinal.router import router as longitudinal_router
from app.migration.router import router as migration_router
from app.provider_trust.router import router as provider_trust_router
from app.provenance.router import router as provenance_router
from app.record_locator.router import router as record_locator_router
from app.repository.router import router as repository_router
from app.trust_ledger.router import router as trust_ledger_router
api_router=APIRouter()
api_router.include_router(identity_router,prefix="/identity",tags=["Identity"])
api_router.include_router(repository_router,prefix="/repository",tags=["Repositories"])
api_router.include_router(record_locator_router,prefix="/record-locator",tags=["Record Locator"])
api_router.include_router(authorization_router,prefix="/authorization",tags=["Authorization"])
api_router.include_router(consent_router,prefix="/consent",tags=["Consent"])
api_router.include_router(jurisdiction_policy_router,prefix="/jurisdiction-policy",tags=["Jurisdiction Policy"])
api_router.include_router(provider_trust_router,prefix="/provider-trust",tags=["Provider Trust"])
api_router.include_router(fhir_router,prefix="/fhir",tags=["FHIR"])
api_router.include_router(longitudinal_router,prefix="/longitudinal",tags=["Longitudinal"])
api_router.include_router(emergency_router,prefix="/emergency",tags=["Emergency"])
api_router.include_router(audit_router,prefix="/audit",tags=["Audit"])
api_router.include_router(provenance_router,prefix="/provenance",tags=["Provenance"])
api_router.include_router(migration_router,prefix="/migration",tags=["Migration"])
api_router.include_router(trust_ledger_router,prefix="/trust-ledger",tags=["Trust Ledger"])
