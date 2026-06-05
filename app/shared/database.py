"""
数据库连接管理

支持 SQLite（开发）和 PostgreSQL（生产）。
使用 SQLAlchemy 2.x 同步模式保持与现有代码兼容。
"""

import os
import sys
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool, QueuePool
from contextlib import contextmanager
from pathlib import Path
from typing import Generator
from loguru import logger

from app.shared.models import Base


class DatabaseManager:
    """
    数据库管理器 - 支持 SQLite 和 PostgreSQL

    SQLite: 使用 StaticPool，单文件数据库，WAL 模式
    PostgreSQL: 使用 QueuePool，连接池，MVCC
    """

    def __init__(
        self,
        db_url: str,
        pool_size: int = 5,
        max_overflow: int = 10,
        pool_recycle: int = 1800,
        echo: bool = False
    ):
        self.db_url = db_url
        self.is_sqlite = db_url.startswith("sqlite")
        self.is_postgresql = "postgresql" in db_url

        # 转换为同步驱动 URL
        sync_url = db_url
        if self.is_sqlite:
            # SQLite: 去掉 +aiosqlite 前缀（同步驱动）
            sync_url = db_url.replace("sqlite+aiosqlite", "sqlite")
            # 确保数据库目录存在
            if sync_url.startswith("sqlite:///"):
                sqlite_path = sync_url.split("sqlite:///")[-1]
                Path(sqlite_path).parent.mkdir(parents=True, exist_ok=True)
        else:
            # PostgreSQL: 将 +asyncpg 替换为 +psycopg2（同步驱动）
            sync_url = sync_url.replace("postgresql+asyncpg", "postgresql+psycopg2")

        if self.is_sqlite:
            # SQLite 配置 - StaticPool 允许多线程
            self.engine = create_engine(
                sync_url,
                connect_args={"check_same_thread": False},
                poolclass=StaticPool,
                echo=echo,
            )
            # 启用 SQLite WAL 模式和外键约束
            @event.listens_for(self.engine, "connect")
            def set_sqlite_pragma(dbapi_conn, _):
                cursor = dbapi_conn.cursor()
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()
        else:
            # PostgreSQL 配置 - QueuePool 连接池
            self.engine = create_engine(
                sync_url,
                poolclass=QueuePool,
                pool_size=pool_size,
                max_overflow=max_overflow,
                pool_recycle=pool_recycle,
                pool_pre_ping=True,  # 连接健康检查
                echo=echo,
            )

        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )

        db_type = 'SQLite' if self.is_sqlite else 'PostgreSQL'
        logger.info(f"数据库引擎初始化完成: {db_type}")

    def init_db(self):
        """初始化数据库，创建所有表"""
        Base.metadata.create_all(bind=self.engine)

    def get_session(self) -> Session:
        """获取数据库 Session"""
        return self.SessionLocal()

    @contextmanager
    def session_scope(self) -> Generator[Session, None, None]:
        """Session 上下文管理器，自动提交/回滚"""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()


# 全局数据库实例
_db_manager: DatabaseManager | None = None


def get_db_manager() -> DatabaseManager:
    """获取数据库管理器实例（单例）"""
    global _db_manager
    if _db_manager is None:
        from app.shared.config import get_config
        config = get_config()
        _db_manager = DatabaseManager(
            db_url=config.database.get_effective_url(),
            pool_size=config.database.pool_size,
            max_overflow=config.database.max_overflow,
            pool_recycle=config.database.pool_recycle,
            echo=config.database.echo,
        )
    return _db_manager


def get_db() -> Generator[Session, None, None]:
    """获取数据库 Session (用于 FastAPI Depends)"""
    db_manager = get_db_manager()
    with db_manager.session_scope() as session:
        yield session