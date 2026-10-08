import hashlib
import json
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.fhir.client import FHIRClient
from app.migration.models import (
    TransferAuthorizationToken,
    TransferManifest,
    TransferRequest,
)
from app.migration.schemas import MigrationState, TransferExecuteRequest, TransferRequestCreate
from app.record_locator.models import RecordLocator
from app.identity.models import PatientIdentity
from app.repository.models import EHRCustody, Repository, RepositoryStatus


class MigrationService:
    """Controls repository-to-repository custody migration without centralizing clinical data."""

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
            raise ValueError("Source or destination repositories not found")
        if (
            source.status == RepositoryStatus.OFFLINE
            or destination.status == RepositoryStatus.OFFLINE
        ):
            raise ValueError("Source and destination repositories must be available")

        current = await self.session.scalar(
            select(RecordLocator).where(
                RecordLocator.health_id == request.health_id,
                RecordLocator.status == "ACTIVE",
            )
        )
        if current is None:
            raise ValueError("Patient has no current repository assignment")
        if current.repository_id != source.id:
            raise ValueError(
                f"Source repository {source.code} is not the patient's current repository"
            )

        item = TransferRequest(
            **request.model_dump(),
            requested_by=actor_id,
            state=MigrationState.REQUESTED.value,
        )
        self.session.add(item)
        await self.session.flush()
        await self.session.refresh(item)
        return item

    async def authorize_transfer(
        self, transfer_id: UUID, actor_id: str, authorization_reference: str
    ) -> TransferRequest:
        item = await self.session.get(TransferRequest, transfer_id)
        if item is None:
            raise ValueError("Transfer request not found")
        if item.state != MigrationState.REQUESTED.value:
            raise ValueError("Transfer is not awaiting authorization")

        patient = await self.session.scalar(
            select(PatientIdentity).where(PatientIdentity.owner_subject == actor_id)
        )
        if patient is None or patient.display_health_id != item.health_id:
            raise ValueError("Only the patient who owns this Health ID can authorize the transfer")

        item.state = MigrationState.PATIENT_AUTHORIZED.value
        item.authorization_reference = authorization_reference
        await self.session.flush()
        await self.session.refresh(item)
        return item

    async def issue_transfer_token(
        self, transfer_id: UUID, actor_id: str
    ) -> tuple[TransferAuthorizationToken, str]:
        item = await self.session.get(TransferRequest, transfer_id)
        if item is None:
            raise ValueError("Transfer request not found")
        if item.state not in (
            MigrationState.PATIENT_AUTHORIZED.value,
            MigrationState.TRANSFER_AUTH_ISSUED.value,
        ):
            raise ValueError("Patient authorization is required before issuing a transfer token")

        # Re-issuing after a failed transfer invalidates any previous token.
        await self.session.execute(
            update(TransferAuthorizationToken)
            .where(
                TransferAuthorizationToken.transfer_request_id == item.id,
                TransferAuthorizationToken.active.is_(True),
            )
            .values(active=False)
        )
        token = secrets.token_urlsafe(32)
        record = TransferAuthorizationToken(
            transfer_request_id=item.id,
            token_hash=hashlib.sha256(token.encode()).hexdigest(),
            issued_by=actor_id,
            expires_at=datetime.now(UTC) + timedelta(minutes=30),
        )
        item.state = MigrationState.TRANSFER_AUTH_ISSUED.value
        self.session.add(record)
        await self.session.flush()
        return record, token

    async def execute_transfer(
        self, transfer_id: UUID, request: TransferExecuteRequest
    ) -> TransferManifest:
        item = await self.session.get(TransferRequest, transfer_id)
        if item is None:
            raise ValueError("Transfer request not found")
        if item.state != MigrationState.TRANSFER_AUTH_ISSUED.value:
            raise ValueError("Transfer authorization must be issued first")

        now = datetime.now(UTC)
        token_record = await self.session.scalar(
            select(TransferAuthorizationToken)
            .where(
                TransferAuthorizationToken.transfer_request_id == item.id,
                TransferAuthorizationToken.active.is_(True),
            )
            .order_by(TransferAuthorizationToken.created_at.desc())
            .with_for_update()
        )
        supplied_hash = hashlib.sha256(request.authorization_token.encode()).hexdigest()
        if (
            token_record is None
            or token_record.expires_at <= now
            or not secrets.compare_digest(token_record.token_hash, supplied_hash)
        ):
            raise ValueError("Transfer authorization token is invalid, expired, or already consumed")

        source = await self.session.get(Repository, item.source_repository_id)
        destination = await self.session.get(Repository, item.destination_repository_id)
        if source is None or destination is None:
            raise ValueError("Source or destination repository not found")
        if source.status == RepositoryStatus.OFFLINE or destination.status == RepositoryStatus.OFFLINE:
            raise ValueError("Source and destination repositories must be available")

        current = await self.session.scalar(
            select(RecordLocator)
            .where(
                RecordLocator.health_id == item.health_id,
                RecordLocator.status == "ACTIVE",
            )
            .order_by(RecordLocator.created_at.desc())
            .with_for_update()
        )
        if current is None or current.repository_id != source.id:
            raise ValueError("Patient is no longer assigned to the requested source repository")

        source_client = FHIRClient(current.endpoint or source.base_url)
        destination_client = FHIRClient(destination.base_url)
        resource_types = [
            value.strip()
            for value in current.resource_types.split(",")
            if value.strip()
        ] or ["Patient", "Observation"]

        def canonical(resources: list[dict]) -> str:
            ordered = sorted(resources, key=lambda value: (value.get("resourceType", ""), value.get("id", "")))
            return json.dumps(ordered, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

        def without_server_metadata(resource: dict) -> dict:
            return {key: value for key, value in resource.items() if key != "meta"}

        item.state = MigrationState.FHIR_EXPORT.value
        await self.session.flush()

        # Export only resources associated with this Health ID. Patient resources
        # are found by the HealthNet identifier; clinical resources by patient reference.
        exported_by_key: dict[tuple[str, str], dict] = {}
        for resource_type in resource_types:
            try:
                if resource_type == "Patient":
                    bundle = await source_client.search(
                        "Patient",
                        {"identifier": f"urn:healthnet:health-id|{item.health_id}"},
                    )
                    entries = bundle.get("entry", [])
                    patients = [
                        entry.get("resource")
                        for entry in entries
                        if isinstance(entry, dict) and isinstance(entry.get("resource"), dict)
                    ]
                    if not patients:
                        try:
                            patients = [await source_client.get_resource("Patient", item.health_id)]
                        except Exception:
                            patients = []
                    for resource in patients:
                        identifiers = resource.get("identifier", [])
                        if any(
                            identifier.get("system") == "urn:healthnet:health-id"
                            and identifier.get("value") == item.health_id
                            for identifier in identifiers
                            if isinstance(identifier, dict)
                        ):
                            if not resource.get("id"):
                                raise ValueError("Source Patient resource has no FHIR id")
                            exported_by_key[("Patient", resource["id"])] = resource
                    continue

                bundle = await source_client.search(resource_type, {"patient": item.health_id})
                for entry in bundle.get("entry", []):
                    resource = entry.get("resource") if isinstance(entry, dict) else None
                    if not isinstance(resource, dict):
                        continue
                    reference = resource.get("subject") or resource.get("patient")
                    reference_value = reference.get("reference") if isinstance(reference, dict) else None
                    if reference_value != f"Patient/{item.health_id}":
                        continue
                    resource_id = resource.get("id")
                    if not resource_id:
                        raise ValueError(f"{resource_type} resource has no FHIR id")
                    exported_by_key[(resource_type, resource_id)] = resource
            except ValueError:
                raise
            except Exception as exc:
                raise ValueError(
                    f"Could not export {resource_type} from source repository {source.code}: {type(exc).__name__}"
                ) from exc

        exported = list(exported_by_key.values())
        if not exported:
            raise ValueError("Source repository returned no FHIR resources for this patient")
        if request.resource_count and request.resource_count != len(exported):
            raise ValueError(
                f"Resource count mismatch: request specified {request.resource_count}, source contains {len(exported)}"
            )

        item.state = MigrationState.VALIDATION.value
        package_hash = hashlib.sha256(canonical([without_server_metadata(resource) for resource in exported]).encode()).hexdigest()
        item.package_hash = package_hash
        item.state = MigrationState.HASH_GENERATION.value
        await self.session.flush()

        # FHIR PUT preserves resource IDs and makes retries idempotent. If both
        # logical repositories share one endpoint in the demo, this is a verified
        # in-place upsert; separate endpoints perform a real copy.
        item.state = MigrationState.ENCRYPTED_TRANSFER.value
        for resource in exported:
            resource_type = resource["resourceType"]
            resource_id = resource["id"]
            try:
                await destination_client.put_resource(resource_type, resource_id, resource)
            except Exception as exc:
                raise ValueError(
                    f"Destination import failed for {resource_type}/{resource_id}: {type(exc).__name__}"
                ) from exc

        item.state = MigrationState.DESTINATION_VALIDATION.value
        verified: list[dict] = []
        for resource in exported:
            try:
                saved = await destination_client.get_resource(
                    resource["resourceType"], resource["id"]
                )
            except Exception as exc:
                raise ValueError(
                    f"Destination verification failed for {resource['resourceType']}/{resource['id']}"
                ) from exc
            if without_server_metadata(saved) != without_server_metadata(resource):
                raise ValueError(
                    f"Destination content differs for {resource['resourceType']}/{resource['id']}"
                )
            verified.append(without_server_metadata(saved))

        item.state = MigrationState.HASH_VERIFICATION.value
        verified_hash = hashlib.sha256(canonical(verified).encode()).hexdigest()
        if not secrets.compare_digest(package_hash, verified_hash):
            raise ValueError("Destination package hash does not match the exported source package")

        item.state = MigrationState.IMPORT_COMPLETED.value
        manifest_hash = hashlib.sha256(
            f"{item.id}|{len(exported)}|{package_hash}".encode()
        ).hexdigest()
        shared_endpoint = (
            (current.endpoint or source.base_url).rstrip("/")
            == destination.base_url.rstrip("/")
        )
        manifest = TransferManifest(
            transfer_request_id=item.id,
            resource_count=len(exported),
            manifest_hash=manifest_hash,
            package_hash=package_hash,
            validation_status="VALID_SHARED_ENDPOINT" if shared_endpoint else "VALID",
        )
        self.session.add(manifest)

        # Switch the authoritative mapping only after the destination package has
        # been read back and verified. The row lock serializes this with ingestion.
        await self.session.execute(
            update(RecordLocator)
            .where(
                RecordLocator.health_id == item.health_id,
                RecordLocator.status == "ACTIVE",
            )
            .values(status="INACTIVE")
        )
        finished_at = datetime.now(UTC)
        self.session.add(
            EHRCustody(
                health_id=item.health_id,
                repository_id=source.id,
                resource_types=",".join(resource_types),
                custody_start=current.created_at,
                custody_end=finished_at,
            )
        )
        self.session.add(
            RecordLocator(
                health_id=item.health_id,
                repository_id=destination.id,
                endpoint=destination.base_url,
                resource_types=",".join(resource_types),
                status="ACTIVE",
                notes=f"Verified migration from {source.code}; manifest {manifest_hash}",
                last_verified_at=finished_at,
            )
        )
        self.session.add(
            EHRCustody(
                health_id=item.health_id,
                repository_id=destination.id,
                resource_types=",".join(resource_types),
                custody_start=finished_at,
                custody_end=None,
            )
        )

        token_record.active = False
        item.state = MigrationState.SOURCE_ARCHIVED_READONLY.value
        item.state = MigrationState.COMPLETED.value
        item.error_message = None
        await self.session.flush()
        await self.session.refresh(manifest)
        return manifest

    async def get_patient_transfers(self, actor_id: str) -> list[TransferRequest]:
        patient = await self.session.scalar(
            select(PatientIdentity).where(PatientIdentity.owner_subject == actor_id)
        )
        if patient is None:
            return []
        result = await self.session.scalars(
            select(TransferRequest)
            .where(TransferRequest.health_id == patient.display_health_id)
            .order_by(TransferRequest.created_at.desc())
        )
        return list(result.all())

    async def get_status(self, transfer_id: UUID) -> TransferRequest | None:
        return await self.session.get(TransferRequest, transfer_id)

    async def get_manifest(self, transfer_id: UUID) -> TransferManifest | None:
        return await self.session.scalar(
            select(TransferManifest)
            .where(TransferManifest.transfer_request_id == transfer_id)
            .order_by(TransferManifest.created_at.desc())
        )
