import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.fhir.client import FHIRClient, FHIRClientError
from app.identity.models import PatientIdentity
from app.migration.models import (
    TransferAuthorizationToken,
    TransferManifest,
    TransferRequest,
)
from app.migration.schemas import (
    MigrationState,
    TransferExecuteRequest,
    TransferRequestCreate,
)
from app.repository.models import Repository, RepositoryStatus
from app.trust_ledger.schemas import LedgerEntryCreate, LedgerEventType
from app.trust_ledger.service import TrustLedgerService

logger = structlog.get_logger(__name__)


class TransferExecutionError(RuntimeError):
    pass


class MigrationService:
    """Coordinates a FHIR transfer without storing clinical resources in HealthNet."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def initiate_transfer(
        self, request: TransferRequestCreate, actor_id: str
    ) -> TransferRequest:
        if request.source_repository_id == request.destination_repository_id:
            raise ValueError("Source and destination repositories must differ")
        source = await self.session.get(Repository, request.source_repository_id)
        destination = await self.session.get(
            Repository, request.destination_repository_id
        )
        if source is None or destination is None:
            raise ValueError("Source or destination repository not found")
        if (
            source.status == RepositoryStatus.OFFLINE
            or destination.status == RepositoryStatus.OFFLINE
        ):
            raise ValueError("Source and destination repositories must be available")
        item = TransferRequest(
            **request.model_dump(),
            requested_by=actor_id,
            state=MigrationState.REQUESTED.value,
        )
        self.session.add(item)
        await self.session.flush()
        return item

    async def authorize_transfer(
        self,
        transfer_id: UUID,
        actor_id: str,
        authorization_reference: str,
    ) -> TransferRequest:
        item = await self.session.get(TransferRequest, transfer_id)
        if item is None:
            raise ValueError("Transfer request not found")
        patient = await self.session.scalar(
            select(PatientIdentity).where(
                PatientIdentity.display_health_id == item.health_id
            )
        )
        if patient is None or patient.owner_subject != actor_id:
            raise ValueError("Transfer does not belong to this patient")
        if item.state != MigrationState.REQUESTED.value:
            raise ValueError("Transfer is not awaiting authorization")
        item.state = MigrationState.PATIENT_AUTHORIZED.value
        item.authorization_reference = authorization_reference
        await self.session.flush()
        return item

    async def issue_transfer_token(
        self, transfer_id: UUID, actor_id: str
    ) -> tuple[TransferAuthorizationToken, str]:
        item = await self.session.get(TransferRequest, transfer_id)
        if item is None:
            raise ValueError("Transfer request not found")
        if item.state != MigrationState.PATIENT_AUTHORIZED.value:
            raise ValueError("Patient authorization is required first")
        authorization_reference = item.authorization_reference
        if not authorization_reference:
            raise ValueError("Patient authorization is missing")
        raw_token = secrets.token_urlsafe(32)
        token = TransferAuthorizationToken(
            transfer_request_id=item.id,
            token_hash=hashlib.sha256(raw_token.encode()).hexdigest(),
            issued_by=actor_id,
            expires_at=datetime.now(UTC) + timedelta(minutes=30),
        )
        self.session.add(token)
        item.state = MigrationState.TRANSFER_AUTH_ISSUED.value
        await self.session.flush()
        await TrustLedgerService(self.session).record_entry(
            LedgerEntryCreate(
                transaction_id=str(item.id),
                event_type=LedgerEventType.TRANSFER_AUTHORIZED,
                opaque_subject_reference=hashlib.sha256(
                    item.health_id.encode()
                ).hexdigest(),
                source_repository_id=item.source_repository_id,
                destination_repository_id=item.destination_repository_id,
                authorization_reference=hashlib.sha256(
                    authorization_reference.encode()
                ).hexdigest(),
                package_hash=hashlib.sha256(str(token.id).encode()).hexdigest(),
                status="AUTHORIZED",
            )
        )
        return token, raw_token

    async def execute_transfer(
        self, transfer_id: UUID, request: TransferExecuteRequest
    ) -> TransferManifest:
        item = await self.session.get(TransferRequest, transfer_id)
        if item is None:
            raise ValueError("Transfer request not found")
        if item.state != MigrationState.TRANSFER_AUTH_ISSUED.value:
            raise ValueError("Transfer authorization token must be issued first")
        authorization_reference = item.authorization_reference
        if not authorization_reference:
            raise ValueError("Patient authorization is missing")

        token_hash = hashlib.sha256(request.authorization_token.encode()).hexdigest()
        token = await self.session.scalar(
            select(TransferAuthorizationToken).where(
                TransferAuthorizationToken.transfer_request_id == item.id,
                TransferAuthorizationToken.token_hash == token_hash,
                TransferAuthorizationToken.active.is_(True),
                TransferAuthorizationToken.expires_at > datetime.now(UTC),
            )
        )
        if token is None or not hmac.compare_digest(token.token_hash, token_hash):
            raise ValueError("Transfer authorization token is invalid or expired")
        token.active = False

        source = await self.session.get(Repository, item.source_repository_id)
        destination = await self.session.get(
            Repository, item.destination_repository_id
        )
        if (
            source is None
            or destination is None
            or source.status == RepositoryStatus.OFFLINE
            or destination.status == RepositoryStatus.OFFLINE
        ):
            raise ValueError("Source or destination repository is unavailable")
        if (
            settings.ENVIRONMENT.lower() == "production"
            and (
                not source.base_url.startswith("https://")
                or not destination.base_url.startswith("https://")
            )
        ):
            raise ValueError("Production FHIR transfers require HTTPS repositories")

        item.state = MigrationState.FHIR_EXPORT.value
        await self.session.commit()
        phase = "FHIR export"
        try:
            resources, package = await FHIRClient(source.base_url).export_patient(
                item.health_id
            )
            package_hash = hashlib.sha256(package).hexdigest()
            item.package_hash = package_hash
            item.state = MigrationState.VALIDATION.value
            await self.session.commit()

            item.state = MigrationState.HASH_GENERATION.value
            await self.session.commit()
            if hashlib.sha256(package).hexdigest() != package_hash:
                raise TransferExecutionError("FHIR export package hash validation failed")

            phase = "destination validation"
            await FHIRClient(destination.base_url).get_metadata()
            item.state = MigrationState.DESTINATION_VALIDATION.value
            await self.session.commit()

            if source.base_url.startswith("https://") and destination.base_url.startswith(
                "https://"
            ):
                item.state = MigrationState.ENCRYPTED_TRANSFER.value
                await self.session.commit()

            item.state = MigrationState.HASH_VERIFICATION.value
            await self.session.commit()
            if hashlib.sha256(package).hexdigest() != item.package_hash:
                raise TransferExecutionError("FHIR package hash verification failed")

            phase = "FHIR import"
            item.state = MigrationState.FHIR_IMPORT.value
            await self.session.commit()
            import_result = await FHIRClient(destination.base_url).import_resources(
                resources
            )
            self._validate_import_result(import_result)
            item.state = MigrationState.IMPORT_COMPLETED.value
            await self.session.commit()

            manifest_hash = hashlib.sha256(
                f"{item.id}|{len(resources)}|{package_hash}".encode()
            ).hexdigest()
            manifest = TransferManifest(
                transfer_request_id=item.id,
                resource_count=len(resources),
                manifest_hash=manifest_hash,
                package_hash=package_hash,
                validation_status="VALID",
            )
            self.session.add(manifest)
            item.state = MigrationState.COMPLETED.value
            await self.session.flush()
            await TrustLedgerService(self.session).record_entry(
                LedgerEntryCreate(
                    transaction_id=str(item.id),
                    event_type=LedgerEventType.TRANSFER_COMPLETED,
                    opaque_subject_reference=hashlib.sha256(
                        item.health_id.encode()
                    ).hexdigest(),
                    source_repository_id=item.source_repository_id,
                    destination_repository_id=item.destination_repository_id,
                    authorization_reference=hashlib.sha256(
                        authorization_reference.encode()
                    ).hexdigest(),
                    package_hash=package_hash,
                    status="COMPLETED",
                )
            )
            await self.session.commit()
            return manifest
        except Exception as exc:
            await self.session.rollback()
            failed = await self.session.get(TransferRequest, transfer_id)
            if failed is not None:
                failed.state = MigrationState.FAILED.value
                failed.error_message = f"{phase}: {type(exc).__name__}: {exc}"[:512]
                await self.session.commit()
            logger.exception(
                "fhir_transfer_failed",
                transfer_id=str(transfer_id),
                phase=phase,
            )
            if isinstance(exc, (FHIRClientError, TransferExecutionError)):
                raise TransferExecutionError(f"{phase} failed: {exc}") from exc
            raise TransferExecutionError(f"{phase} failed") from exc

    @staticmethod
    def _validate_import_result(bundle: dict) -> None:
        if bundle.get("resourceType") != "Bundle":
            raise TransferExecutionError("FHIR import did not return a Bundle")
        for entry in bundle.get("entry", []):
            response = entry.get("response") if isinstance(entry, dict) else None
            if not isinstance(response, dict):
                continue
            code = str(response.get("status", ""))
            if code[:1] in {"4", "5"}:
                outcome = response.get("outcome")
                diagnostics = ""
                if isinstance(outcome, dict):
                    diagnostics = "; ".join(
                        issue.get("diagnostics", "")
                        for issue in outcome.get("issue", [])
                        if isinstance(issue, dict)
                    )
                raise TransferExecutionError(
                    f"FHIR destination rejected an imported resource ({code}): {diagnostics}"
                )

    async def get_status(self, transfer_id: UUID) -> TransferRequest | None:
        return await self.session.get(TransferRequest, transfer_id)

    async def get_manifest(self, transfer_id: UUID) -> TransferManifest | None:
        return await self.session.scalar(
            select(TransferManifest)
            .where(TransferManifest.transfer_request_id == transfer_id)
            .order_by(TransferManifest.created_at.desc())
        )
