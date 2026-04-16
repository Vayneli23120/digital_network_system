"""
数据库连接管理
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from pathlib import Path

from .models import Base


class DatabaseManager:
    """数据库管理器"""

    def __init__(self, db_path: str = "./data/nas.db"):
        # 确保目录存在
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        # SQLite 连接字符串
        self.database_url = f"sqlite:///{db_path}"

        # 创建引擎
        self.engine = create_engine(
            self.database_url,
            connect_args={"check_same_thread": False},
            echo=False
        )

        # 创建 Session
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )

    def init_db(self):
        """初始化数据库，创建所有表"""
        Base.metadata.create_all(bind=self.engine)

    def get_session(self) -> Session:
        """获取数据库 Session"""
        return self.SessionLocal()

    @contextmanager
    def session_scope(self):
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
_db_manager = None


def get_db_manager() -> DatabaseManager:
    """获取数据库管理器实例"""
    global _db_manager
    if _db_manager is None:
        from .config import get_config
        config = get_config()
        _db_manager = DatabaseManager(config.database.sqlite_path)
    return _db_manager


def get_db() -> Session:
    """获取数据库 Session (用于 FastAPI Depends)"""
    db_manager = get_db_manager()
    try:
        db = db_manager.get_session()
        yield db
    finally:
        db.close()
