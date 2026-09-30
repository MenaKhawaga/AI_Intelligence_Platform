"""Alembic environment for the AI Intelligence Platform."""

from __future__ import annotations

import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

# Make `app` importable when Alembic is invoked from the project root

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from app.core.config import settings
from app.database.base_class import Base

from app.models.agent_activity import AgentActivity 
from app.models.article import Article  
from app.models.category import Category 
from app.models.entity import Entity 
from app.models.source import Source  
from app.models.summary import Summary 
from app.models.topic import Topic  
from app.models.user import User  


config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _resolve_database_url() -> str:
    """-x db_url=... overrides settings.DATABASE_URL, which overrides alembic.ini."""

    x_args = context.get_x_argument(as_dictionary=True)
    return x_args.get("db_url") or settings.DATABASE_URL


def run_migrations_offline() -> None:
    """Emit SQL to stdout without a live DB connection (``alembic upgrade head --sql``)."""

    url = _resolve_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations against a live database connection (the normal case)."""

    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = _resolve_database_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
