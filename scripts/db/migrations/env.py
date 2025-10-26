import os
from dotenv import load_dotenv
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool
import sqlalchemy as sa

from alembic import context


config = context.config

# Interpret the config file for Python's standard logging.
fileConfig(config.config_file_name)
target_metadata = None

# Load environment variables from .env file (for local development)
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
CONFIG_FILENAME = 'connect_to_postgres.env'

# Load the environment file using the full path
load_result = load_dotenv(os.path.join(ROOT_DIR, CONFIG_FILENAME), override=True)


# Function to get the database URL
def get_url():
    # Use os.getenv() to read the environment variable
    url = os.getenv("DATABASE_URL")
    print(url)

    if url is None:
        raise Exception("DATABASE_URL environment variable is not set.")

    return url


def run_migrations_offline():
    """Run migrations in 'offline' mode. (Only generates SQL or checks environment.)"""
    # This URL retrieval is correct:
    url = get_url()

    context.configure(
        url=url, target_metadata=target_metadata, literal_binds=True, dialect_opts={"paramstyle": "named"}
    )

    # print(context.get_current_revision())
    pass


def run_migrations_online():
    """Run migrations in 'online' mode."""
    connectable = sa.create_engine(get_url())

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
