import asyncio
from datetime import UTC, datetime, timedelta

import structlog

from app.core.database import async_session_maker
from app.identity_resolution.service import IdentityResolutionService

logger = structlog.get_logger(__name__)


async def nightly_duplicate_scan() -> None:
    while True:
        now = datetime.now(UTC)
        next_run = (now + timedelta(days=1)).replace(
            hour=2, minute=0, second=0, microsecond=0
        )
        await asyncio.sleep((next_run - now).total_seconds())
        if async_session_maker is None:
            logger.error("identity_duplicate_scan_skipped", reason="database_not_initialized")
            continue
        try:
            async with async_session_maker() as session:
                count = await IdentityResolutionService(
                    session
                ).recheck_existing_identities()
                await session.commit()
                logger.info("identity_duplicate_scan_completed", reviews_created=count)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("identity_duplicate_scan_failed")
