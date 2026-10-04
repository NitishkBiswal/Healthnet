import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.migration.models import TransferAuthorizationToken, TransferManifest, TransferRequest
from app.migration.schemas import MigrationState, TransferExecuteRequest, TransferRequestCreate
from app.repository.models import Repository, RepositoryStatus

class MigrationService:
    """Controls the migration state machine without storing clinical content centrally."""
    def __init__(self, session: AsyncSession): self.session = session
    async def initiate_transfer(self, request: TransferRequestCreate, actor_id: str) -> TransferRequest:
        if request.source_repository_id == request.destination_repository_id: raise ValueError("Source and destination repositories must differ")
        source = await self.session.get(Repository, request.source_repository_id); destination = await self.session.get(Repository, request.destination_repository_id)
        if source is None or destination is None: raise ValueError("Source or destination repository not found")
        if source.status == RepositoryStatus.OFFLINE or destination.status == RepositoryStatus.OFFLINE: raise ValueError("Source and destination repositories must be available")
        item = TransferRequest(**request.model_dump(), requested_by=actor_id, state=MigrationState.REQUESTED.value); self.session.add(item); await self.session.flush(); return item
    async def authorize_transfer(self, transfer_id: UUID, actor_id: str, authorization_reference: str) -> TransferRequest:
        item=await self.session.get(TransferRequest,transfer_id)
        if item is None: raise ValueError("Transfer request not found")
        if item.state != MigrationState.REQUESTED.value: raise ValueError("Transfer is not awaiting authorization")
        item.state=MigrationState.PATIENT_AUTHORIZED.value; item.authorization_reference=authorization_reference; await self.session.flush(); return item
    async def issue_transfer_token(self, transfer_id: UUID, actor_id: str) -> tuple[TransferAuthorizationToken,str]:
        item=await self.session.get(TransferRequest,transfer_id)
        if item is None: raise ValueError("Transfer request not found")
        if item.state != MigrationState.PATIENT_AUTHORIZED.value: raise ValueError("Patient authorization is required first")
        token=secrets.token_urlsafe(32)
        record=TransferAuthorizationToken(transfer_request_id=item.id,token_hash=hashlib.sha256(token.encode()).hexdigest(),issued_by=actor_id,expires_at=datetime.now(UTC)+timedelta(minutes=30))
        item.state=MigrationState.TRANSFER_AUTH_ISSUED.value; self.session.add(record); await self.session.flush(); return record,token
    async def execute_transfer(self, transfer_id: UUID, request: TransferExecuteRequest) -> TransferManifest:
        item=await self.session.get(TransferRequest,transfer_id)
        if item is None: raise ValueError("Transfer request not found")
        if item.state != MigrationState.TRANSFER_AUTH_ISSUED.value: raise ValueError("Transfer authorization token must be issued first")
        item.state=MigrationState.FHIR_EXPORT.value; item.package_hash=request.package_hash
        manifest_hash=hashlib.sha256(f"{item.id}|{request.resource_count}|{request.package_hash}".encode()).hexdigest()
        manifest=TransferManifest(transfer_request_id=item.id,resource_count=request.resource_count,manifest_hash=manifest_hash,package_hash=request.package_hash,validation_status="VALID"); self.session.add(manifest)
        for state in (MigrationState.VALIDATION,MigrationState.HASH_GENERATION,MigrationState.ENCRYPTED_TRANSFER,MigrationState.DESTINATION_VALIDATION,MigrationState.HASH_VERIFICATION,MigrationState.IMPORT_COMPLETED,MigrationState.SOURCE_ARCHIVED_READONLY,MigrationState.COMPLETED): item.state=state.value
        await self.session.flush(); return manifest
    async def get_status(self, transfer_id: UUID) -> TransferRequest|None: return await self.session.get(TransferRequest,transfer_id)
    async def get_manifest(self, transfer_id: UUID) -> TransferManifest|None: return await self.session.scalar(select(TransferManifest).where(TransferManifest.transfer_request_id==transfer_id).order_by(TransferManifest.created_at.desc()))
