from logging.config import fileConfig
from alembic import context
from sqlalchemy import engine_from_config, pool

import os
import sys
from pathlib import Path

# --------------------------------------------------
# Add backend/ to PYTHONPATH so `app.*` imports work
# --------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))
sys.path.append("/app")  # In case the container uses /app as the working directory

# --------------------------------------------------
# Alembic Config
# --------------------------------------------------
config = context.config

# Logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# --------------------------------------------------
# Import application settings and Base
# --------------------------------------------------
from backend.app.core.config import settings
from backend.app.core.database import Base
from backend.app.models import models  # IMPORTANT: forces model imports


# --------------------------------------------------
# Override DB URL using app settings
# --------------------------------------------------
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# --------------------------------------------------
# Metadata for autogenerate
# --------------------------------------------------
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in offline mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in online mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
