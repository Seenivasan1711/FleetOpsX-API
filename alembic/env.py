import os
import sys
from logging.config import fileConfig

from sqlalchemy import create_engine, engine_from_config
from sqlalchemy import pool

from alembic import context

# Add the app directory to the path so we can import models and settings
sys.path.append(os.getcwd())

from app.core.config import settings

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Do NOT use config.set_main_option here — ConfigParser chokes on % in URLs (e.g. %40 for @).
# We pass settings.DATABASE_URL directly to the engine in both offline and online modes below.

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
from app.models import Base
target_metadata = Base.metadata

# Exclude PostGIS system schemas and tables from autogenerate
EXCLUDED_SCHEMAS = {"tiger", "tiger_data", "topology"}

def include_object(object, name, type_, reflected, compare_to):
    """Exclude PostGIS system tables from autogenerate."""
    if type_ == "table" and object.schema in EXCLUDED_SCHEMAS:
        return False
    # Exclude known PostGIS/TIGER system tables in the public schema
    POSTGIS_TABLES = {
        "spatial_ref_sys", "layer", "topology",
        "geocode_settings", "geocode_settings_default",
        "pagc_gaz", "pagc_lex", "pagc_rules",
        "loader_platform", "loader_variables", "loader_lookuptables",
        "zip_lookup", "zip_lookup_all", "zip_lookup_base",
        "zip_state", "zip_state_loc",
        "county", "county_lookup",
        "cousub", "countysub_lookup",
        "edges", "faces", "featnames", "addr", "addrfeat",
        "place", "place_lookup",
        "state", "state_lookup",
        "street_type_lookup", "secondary_unit_lookup",
        "direction_lookup",
        "tract", "tabblock", "tabblock20", "bg", "zcta5",
    }
    if type_ == "table" and name in POSTGIS_TABLES:
        return False
    return True


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    context.configure(
        url=settings.DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = create_engine(settings.DATABASE_URL, poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
