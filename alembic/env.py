import sys
from os.path import abspath, dirname
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

# Chemin du projet
sys.path.insert(0, dirname(dirname(abspath(__file__))))

# Importez vos configurations
from app.config import settings
from app.models import SQLBase

# Configuration Alembic
config = context.config
fileConfig(config.config_file_name) if config.config_file_name else None
target_metadata = SQLBase.metadata

def get_url():
    """Convertit l'URL de la base de données en string si nécessaire"""
    db_url = settings.DATABASE_URL
    return str(db_url) if hasattr(db_url, '__str__') else db_url

def run_migrations_offline():
    """Mode hors-ligne"""
    context.configure(
        url=get_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    """Mode en ligne"""
    connectable = engine_from_config(
        {"sqlalchemy.url": get_url()},
        prefix="sqlalchemy.",
        poolclass=pool.NullPool
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True
        )
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()