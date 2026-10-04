import asyncio
import os
from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context
from app.core.database import Base
from app.consent import models as consent_models  # noqa: F401
from app.audit import models as audit_models  # noqa: F401
from app.emergency import models as emergency_models  # noqa: F401
from app.identity import models as identity_models  # noqa: F401
from app.jurisdiction_policy import models as jurisdiction_policy_models  # noqa: F401
from app.provenance import models as provenance_models  # noqa: F401
from app.provider_trust import models as provider_trust_models  # noqa: F401
from app.record_locator import models as record_locator_models  # noqa: F401
from app.repository import models as repository_models  # noqa: F401

config=context.config
if config.config_file_name is not None: fileConfig(config.config_file_name)
target_metadata=Base.metadata

def get_url()->str:
    url=os.environ.get("DATABASE_URL")
    if url is None:
        from app.core.config import settings
        url=settings.DATABASE_URL
    return url.replace("postgresql+psycopg2://","postgresql+asyncpg://",1)

def run_migrations_offline()->None:
    context.configure(url=get_url(),target_metadata=target_metadata,literal_binds=True,dialect_opts={"paramstyle":"named"})
    with context.begin_transaction(): context.run_migrations()

def do_run_migrations(connection:Connection)->None:
    context.configure(connection=connection,target_metadata=target_metadata)
    with context.begin_transaction(): context.run_migrations()

async def run_async_migrations()->None:
    configuration=config.get_section(config.config_ini_section,{})
    configuration["sqlalchemy.url"]=get_url()
    connectable=async_engine_from_config(configuration,prefix="sqlalchemy.",poolclass=pool.NullPool)
    async with connectable.connect() as connection: await connection.run_sync(do_run_migrations)
    await connectable.dispose()

def run_migrations_online()->None: asyncio.run(run_async_migrations())
if context.is_offline_mode(): run_migrations_offline()
else: run_migrations_online()
