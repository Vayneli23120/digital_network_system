"""Alembic environment configuration"""

import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool, create_engine
from alembic import context

# Add app package to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.shared.models import Base  # noqa: E402

# Alembic Config
config = context.config

# Override sqlalchemy.url from environment (Twelve-Factor)
# 支持从配置文件读取或环境变量
try:
    from app.shared.config import get_config
    _config = get_config()
    default_url = _config.database.get_effective_url()
except Exception:
    default_url = f"sqlite:///{os.path.join(os.getcwd(), 'data', 'app.db')}"

db_url = os.getenv('DATABASE_URL', default_url)
# Alembic 使用同步驱动
db_url = db_url.replace("postgresql+asyncpg", "postgresql+psycopg2")
db_url = db_url.replace("sqlite+aiosqlite", "sqlite")

config.set_main_option('sqlalchemy.url', db_url)

# 判断数据库类型
_is_sqlite = 'sqlite' in db_url
_is_postgresql = 'postgresql' in db_url

# Logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Target metadata
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=_is_sqlite,  # 仅 SQLite 需要
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=_is_sqlite,  # 仅 SQLite 需要
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
