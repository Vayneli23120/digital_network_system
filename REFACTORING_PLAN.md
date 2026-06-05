# 企业级网络自动化平台 — 分阶段重构执行计划

**版本**: 1.0  
**制定日期**: 2026-06-05  
**配套文档**: ENTERPRISE_ARCHITECTURE.md  
**执行原则**: 每次变更必须保证现有功能继续可用，不得破坏 225 个现有测试。

---

## 执行总览

| 阶段 | 名称 | 工期（建议） | 依赖 | 核心目标 |
|---|---|---|---|---|
| Phase 1 | 安全与数据库底座 | 4-6 周 | 无 | PostgreSQL、安全基线、仓库清理 |
| Phase 2 | 自动化平台化 | 6-10 周 | Phase 1 完成 | Job 模型、统一驱动、任务队列、多厂商 |
| Phase 3 | AI 平台化 | 8-12 周 | Phase 1 完成（Phase 2 并行） | RAG、工具治理、AI 工作台 |
| Phase 4 | 前端迁移 | 10-16 周 | Phase 1 完成（可并行） | React+TypeScript+Ant Design |

> **执行优先级**：Phase 1 > Phase 2 与 Phase 3（可并行） > Phase 4（可独立进行）

---

## Phase 1：安全与数据库底座

> **目标**：消除生产不可用的安全缺陷，将数据库从 SQLite 迁移到 PostgreSQL。  
> **接受标准**：Phase 1 完成后，所有现有 225 个测试通过，且在 PostgreSQL 上运行。

---

### Task 1.1：清理双后端仓库结构

**涉及文件**：`backend/` 目录（整体）

**执行步骤**：
1. 将 `backend/` 目录重命名为 `backend/.archived/`，或添加 `backend/README_ARCHIVED.md` 说明此目录已废弃，不再维护，不可运行。
2. 更新根目录 `README.md`，删除对 `backend/` 目录的所有引用。
3. 确认没有 CI/CD 流程依赖 `backend/` 路径。

**注意**：不删除文件，仅标记废弃，保留历史记录。

---

### Task 1.2：修复 CORS 安全配置

**涉及文件**：`app/main.py`、`app/shared/config.py`

**1.2.1 在配置类中增加 CORS 白名单字段**

在 `app/shared/config.py` 中，找到 `class SecurityConfig` 并添加：

```python
class SecurityConfig(BaseModel):
    auth_enabled: bool = False
    jwt_secret: str = "your-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7
    # 新增以下字段
    cors_allowed_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:5173"],
        description="生产环境必须配置为实际域名，禁止使用 * 通配符"
    )
    cors_allow_credentials: bool = True
```

**1.2.2 修改 main.py 的 CORS 中间件**

将 `app/main.py` 中：
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: 生产环境改为具体域名
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    expose_headers=["X-RateLimit-Limit", "X-RateLimit-Remaining", "X-Request-ID"],
)
```

替换为：
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.security.cors_allowed_origins,
    allow_credentials=config.security.cors_allow_credentials,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    expose_headers=["X-RateLimit-Limit", "X-RateLimit-Remaining", "X-Request-ID"],
)
```

**1.2.3 在 config.yaml 示例中添加 CORS 配置说明**

在 `config.example.yaml`（或直接在 README 中）补充：
```yaml
security:
  auth_enabled: true             # 生产必须设为 true
  cors_allowed_origins:
    - "https://your-nas-domain.example.com"
  jwt_secret: "${JWT_SECRET}"    # 从环境变量读取，32+ 字符随机字符串
```

---

### Task 1.3：修复 JWT Secret 生产强制校验

**涉及文件**：`app/shared/config.py`

找到 `SecurityConfig.validate` 方法（在 `Config.validate` 内调用），确认以下逻辑存在，如不存在则添加：

```python
def validate(self) -> "Config":
    if self.security.auth_enabled:
        if self.security.jwt_secret in [
            "your-secret-key-change-in-production", "secret", "password", "changeme", "123456"
        ]:
            print("[CONFIG ERROR] auth_enabled=true 但 jwt_secret 仍为默认值！", file=sys.stderr)
            sys.exit(1)
        if len(self.security.jwt_secret) < 32:
            print("[CONFIG ERROR] jwt_secret 长度不足 32 位，生产环境不允许！", file=sys.stderr)
            sys.exit(1)
        # 强制要求 CORS 不能使用通配符（当 auth 开启时）
        if "*" in self.security.cors_allowed_origins:
            print("[CONFIG ERROR] auth_enabled=true 时 cors_allowed_origins 禁止使用 * 通配符！", file=sys.stderr)
            sys.exit(1)
    return self
```

---

### Task 1.4：PostgreSQL 支持

**核心原则**：使用 SQLAlchemy 抽象层，代码层面对 PostgreSQL 和 SQLite 都兼容，但推荐生产环境使用 PostgreSQL。

#### 1.4.1 更新 requirements.txt

在 `requirements.txt` 中添加：
```
# PostgreSQL 驱动
asyncpg==0.29.0
psycopg2-binary==2.9.9
```

#### 1.4.2 重构 DatabaseConfig

将 `app/shared/config.py` 中的 `DatabaseConfig` 类替换为：

```python
class DatabaseConfig(BaseModel):
    url: str = f"sqlite+aiosqlite:///{os.path.join(os.getcwd(), 'data', 'nas.db')}"
    # 连接池配置（仅 PostgreSQL 生效）
    pool_size: int = 10
    max_overflow: int = 20
    pool_timeout: int = 30
    pool_recycle: int = 1800
    echo: bool = False

    @field_validator('url')
    @classmethod
    def validate_db_url(cls, v: str) -> str:
        allowed_schemes = ['sqlite', 'sqlite+aiosqlite', 'postgresql', 'postgresql+asyncpg', 'postgresql+psycopg2']
        scheme = v.split('://')[0] if '://' in v else ''
        if not any(v.startswith(s) for s in allowed_schemes):
            raise ValueError(f"不支持的数据库类型，允许: {allowed_schemes}")
        return v

    @property
    def is_postgresql(self) -> bool:
        return 'postgresql' in self.url

    @property
    def is_sqlite(self) -> bool:
        return 'sqlite' in self.url
```

**同时在 config.yaml 示例中添加**：
```yaml
database:
  url: "postgresql+asyncpg://${DB_USER}:${DB_PASSWORD}@localhost:5432/nas"
  pool_size: 10
  max_overflow: 20
```

#### 1.4.3 重构 database.py

将 `app/shared/database.py` 完整替换为：

```python
"""
数据库连接管理

支持 SQLite（开发）和 PostgreSQL（生产）。
使用 SQLAlchemy 2.x 同步模式保持与现有代码兼容。
"""

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool, QueuePool
from contextlib import contextmanager
from pathlib import Path
from typing import Generator
from loguru import logger

from app.shared.models import Base


class DatabaseManager:
    def __init__(self, db_url: str, pool_size: int = 5, max_overflow: int = 10,
                 pool_recycle: int = 1800, echo: bool = False):
        self.db_url = db_url
        self.is_sqlite = db_url.startswith("sqlite")
        self.is_postgresql = "postgresql" in db_url

        # SQLite 专用：去掉 +aiosqlite 前缀（同步驱动）
        sync_url = db_url.replace("sqlite+aiosqlite", "sqlite")
        # PostgreSQL：将 +asyncpg 替换为 +psycopg2（同步驱动）
        sync_url = sync_url.replace("postgresql+asyncpg", "postgresql+psycopg2")

        if self.is_sqlite:
            # SQLite 使用 StaticPool，允许多线程
            sqlite_path = db_url.split("///")[-1]
            Path(sqlite_path).parent.mkdir(parents=True, exist_ok=True)
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
            # PostgreSQL 使用 QueuePool
            self.engine = create_engine(
                sync_url,
                poolclass=QueuePool,
                pool_size=pool_size,
                max_overflow=max_overflow,
                pool_recycle=pool_recycle,
                pool_pre_ping=True,
                echo=echo,
            )

        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )
        logger.info(f"数据库引擎初始化完成: {'SQLite' if self.is_sqlite else 'PostgreSQL'}")

    def init_db(self):
        Base.metadata.create_all(bind=self.engine)

    def get_session(self) -> Session:
        return self.SessionLocal()

    @contextmanager
    def session_scope(self) -> Generator[Session, None, None]:
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()


_db_manager: DatabaseManager | None = None


def get_db_manager() -> DatabaseManager:
    global _db_manager
    if _db_manager is None:
        from app.shared.config import get_config
        config = get_config()
        _db_manager = DatabaseManager(
            db_url=config.database.url,
            pool_size=config.database.pool_size,
            max_overflow=config.database.max_overflow,
            pool_recycle=config.database.pool_recycle,
            echo=config.database.echo,
        )
    return _db_manager


def get_db() -> Generator[Session, None, None]:
    db_manager = get_db_manager()
    with db_manager.session_scope() as session:
        yield session
```

#### 1.4.4 更新 Alembic 迁移配置

将 `migrations/env.py` 中的：
```python
db_path = os.getenv('DATABASE_URL', f"sqlite:///{os.path.join(os.getcwd(), 'data', 'app.db')}")
...
render_as_batch=True,  # Required for SQLite
```

替换为：
```python
# 从环境变量读取，优先使用 DATABASE_URL，其次从配置文件
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from app.shared.config import get_config

_config = get_config()
db_url = os.getenv('DATABASE_URL', _config.database.url)
# Alembic 使用同步驱动
db_url = db_url.replace("postgresql+asyncpg", "postgresql+psycopg2")
db_url = db_url.replace("sqlite+aiosqlite", "sqlite")
config.set_main_option('sqlalchemy.url', db_url)

# 注意：render_as_batch 仅 SQLite 需要，PostgreSQL 不需要
_is_sqlite = 'sqlite' in db_url
```

在 `run_migrations_offline` 和 `run_migrations_online` 的 `context.configure` 中：
```python
context.configure(
    ...,
    render_as_batch=_is_sqlite,  # 根据数据库类型动态决定
)
```

#### 1.4.5 创建 PostgreSQL 初始化 migration

创建新的 Alembic migration 文件（`alembic revision --autogenerate -m "migrate_to_postgresql"`），执行前确保：
- 删除 SQLite 专用迁移脚本中的 `sqlite3` 直接操作
- 所有 `Text` 列中存储 JSON 的，在 PostgreSQL 版本中可升级为 `JSONB`
- 时区问题：确保所有 `DateTime` 列使用 `timezone=True`

#### 1.4.6 更新 docker-compose.yml

将 `docker-compose.yml` 完整替换为以下内容：

```yaml
version: '3.9'

services:
  postgres:
    image: pgvector/pgvector:pg15
    container_name: nas-postgres
    environment:
      POSTGRES_DB: nas
      POSTGRES_USER: ${DB_USER:-nasuser}
      POSTGRES_PASSWORD: ${DB_PASSWORD:?DB_PASSWORD is required}
    volumes:
      - pg_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER:-nasuser} -d nas"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    container_name: nas-redis
    command: redis-server --requirepass ${REDIS_PASSWORD:-changeme_redis}
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "-a", "${REDIS_PASSWORD:-changeme_redis}", "ping"]
      interval: 10s
      timeout: 5s
      retries: 3

  backend:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: nas-backend
    ports:
      - "8000:8000"
    volumes:
      - nas-backups:/app/backups
      - nas-logs:/app/logs
      - nas-assets:/app/assets
    environment:
      DATABASE_URL: "postgresql+psycopg2://${DB_USER:-nasuser}:${DB_PASSWORD}@postgres:5432/nas"
      REDIS_URL: "redis://:${REDIS_PASSWORD:-changeme_redis}@redis:6379/0"
      AUTH_ENABLED: "${AUTH_ENABLED:-true}"
      CORS_ALLOWED_ORIGINS: "${CORS_ALLOWED_ORIGINS:-http://localhost:3000}"
      JWT_SECRET: "${JWT_SECRET:?JWT_SECRET is required in production}"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 15s

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    container_name: nas-frontend
    ports:
      - "3000:80"
    depends_on:
      backend:
        condition: service_healthy
    restart: unless-stopped

volumes:
  pg_data:
  redis_data:
  nas-backups:
  nas-logs:
  nas-assets:
```

#### 1.4.7 创建 .env.example 文件

创建或更新 `.env.example`（根目录），内容如下：

```bash
# === 数据库 ===
DB_USER=nasuser
DB_PASSWORD=change_me_strong_password_here
DATABASE_URL=postgresql+psycopg2://nasuser:change_me_strong_password_here@localhost:5432/nas

# === Redis ===
REDIS_PASSWORD=change_me_redis_password
REDIS_URL=redis://:change_me_redis_password@localhost:6379/0

# === 安全 ===
# 生成强随机密钥: python -c "import secrets; print(secrets.token_hex(32))"
JWT_SECRET=change_me_at_least_32_chars_random_secret_key_here
AUTH_ENABLED=true

# === CORS ===
# 多个域名用逗号分隔
CORS_ALLOWED_ORIGINS=http://localhost:3000,https://your-nas.example.com

# === AI ===
OPENAI_API_KEY=your_api_key_here
OPENAI_BASE_URL=https://api.openai.com/v1
AI_DEFAULT_MODEL=gpt-4o-mini
```

---

### Task 1.5：前端 Token 存储安全修复

**涉及文件**：`frontend/src/views/Login.vue`、`frontend/src/api/request.js`

**短期修复方案**（保持 Vue 3 + localStorage，但增加防护）：

在 `frontend/src/views/Login.vue` 的 `handleLogin` 函数中，保持 localStorage 方式但增加 Token 内容校验：

```javascript
// 在存储前验证 token 格式（基本保护）
const validateAndStoreToken = (token) => {
  if (!token || typeof token !== 'string') {
    throw new Error('Invalid token format')
  }
  // 验证是 JWT 格式 (三段 base64url)
  const parts = token.split('.')
  if (parts.length !== 3) {
    throw new Error('Invalid JWT structure')
  }
  // 不在 localStorage 以外的地方暴露 token
  // 不在 URL 参数中传递 token
  // 不在日志中打印 token
  localStorage.setItem('accessToken', token)
}
```

**中期目标**（Phase 1 完成后、Phase 4 前端迁移时彻底修复）：

后端在登录接口添加 `Set-Cookie: accessToken=...; HttpOnly; Secure; SameSite=Strict`，前端不再手动管理 token。此步骤在 Phase 4（前端迁移到 React+TS 时）一并完成。

---

### Task 1.6：更新测试套件以支持 PostgreSQL

**涉及文件**：`tests/conftest.py`

```python
# tests/conftest.py
import pytest
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.shared.models import Base
from app.shared.database import DatabaseManager


@pytest.fixture(scope="session")
def test_db_manager():
    """测试数据库管理器 — 优先使用环境变量中的 PostgreSQL，回退到内存 SQLite"""
    test_db_url = os.getenv(
        "TEST_DATABASE_URL",
        "sqlite:///:memory:"  # CI 环境或无 PG 时的回退
    )
    manager = DatabaseManager(db_url=test_db_url, echo=False)
    manager.init_db()
    yield manager
    # 清理
    if "sqlite" in test_db_url:
        Base.metadata.drop_all(bind=manager.engine)


@pytest.fixture(scope="function")
def db_session(test_db_manager):
    """每个测试函数独立事务，测试后回滚"""
    session = test_db_manager.get_session()
    try:
        yield session
    finally:
        session.rollback()
        session.close()
```

在 `pytest.ini` 中添加：
```ini
[pytest]
...
env =
    TEST_DATABASE_URL=sqlite:///:memory:
```

对于需要 PostgreSQL 特性的测试（如 JSONB），使用 `pytest.mark.postgresql` 标记，CI 中专门运行。

---

### Phase 1 验收标准

- [ ] 所有 225 个现有测试在修改后仍通过
- [ ] `docker-compose up` 使用 PostgreSQL 正常启动
- [ ] CORS 不再允许 `*` 通配符，仅允许配置的 origin
- [ ] 生产环境（`AUTH_ENABLED=true`）下，使用默认 JWT Secret 启动时进程立即退出并报错
- [ ] `backend/` 目录已明确标记废弃
- [ ] `docker-compose.yml` 不再包含任何明文密码，全部通过环境变量引用

---

## Phase 2：自动化平台化

> **目标**：将所有设备操作从同步 API 调用改为异步 Job 模型，统一厂商驱动，支持 Aruba 和 Fortinet。  
> **前置条件**：Phase 1 完成。

---

### Task 2.1：引入 Celery 任务队列

#### 2.1.1 安装依赖

在 `requirements.txt` 中添加：
```
celery==5.4.0
redis==5.0.3
flower==2.0.1          # Celery 监控 UI（可选）
aiosmtplib==3.0.1      # 已有，保留
```

#### 2.1.2 创建 Celery 应用实例

创建新文件 `app/core/celery_app.py`：

```python
"""
Celery 应用实例

队列划分：
- device_ops: 设备操作（备份/部署/执行命令），高优先级
- ai_tasks: AI 分析任务，中优先级，设有超时
- notifications: 通知发送，低优先级
- scheduled: 定时任务（健康检查/合规扫描）
"""

from celery import Celery
from app.shared.config import get_config

config = get_config()


def create_celery_app() -> Celery:
    redis_url = config.celery.broker_url  # 在 config.py 中新增

    celery_app = Celery(
        "nas",
        broker=redis_url,
        backend=redis_url,
    )

    celery_app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        task_track_started=True,
        task_acks_late=True,          # 任务完成后才 ACK，避免 worker 崩溃丢任务
        worker_prefetch_multiplier=1, # 每次只取 1 个任务，避免长任务阻塞
        task_routes={
            "app.tasks.backup_tasks.*": {"queue": "device_ops"},
            "app.tasks.deploy_tasks.*": {"queue": "device_ops"},
            "app.tasks.discovery_tasks.*": {"queue": "device_ops"},
            "app.tasks.ai_tasks.*": {"queue": "ai_tasks"},
            "app.tasks.notification_tasks.*": {"queue": "notifications"},
            "app.tasks.scheduled_tasks.*": {"queue": "scheduled"},
        },
        task_default_queue="device_ops",
        task_time_limit=300,         # 硬超时 5 分钟
        task_soft_time_limit=240,    # 软超时 4 分钟（触发 SoftTimeLimitExceeded）
    )

    return celery_app


celery_app = create_celery_app()
```

#### 2.1.3 在 config.py 中添加 Celery 配置

在 `app/shared/config.py` 中添加：

```python
class CeleryConfig(BaseModel):
    broker_url: str = "redis://localhost:6379/0"
    result_backend: str = "redis://localhost:6379/0"
    
    @field_validator('broker_url', 'result_backend')
    @classmethod
    def validate_redis_url(cls, v: str) -> str:
        if not v.startswith(('redis://', 'rediss://')):
            raise ValueError("Celery broker/backend 必须使用 Redis URL")
        return v
```

在 `Config` 类中添加：
```python
celery: CeleryConfig = Field(default_factory=CeleryConfig)
```

#### 2.1.4 创建统一 Job 数据模型

创建新文件 `app/shared/models_jobs.py`（或直接在 `app/shared/models.py` 中添加）：

```python
import uuid
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ARRAY
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.dialects.sqlite import JSON  # SQLite 回退
from datetime import datetime
from app.shared.models import Base


def JSONBColumn(*args, **kwargs):
    """跨数据库 JSONB/JSON 列"""
    try:
        from sqlalchemy.dialects.postgresql import JSONB as _JSONB
        return Column(_JSONB, *args, **kwargs)
    except Exception:
        return Column(JSON, *args, **kwargs)


class Job(Base):
    """统一作业记录表——所有设备操作的执行记录"""
    __tablename__ = "jobs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    job_type = Column(String(50), nullable=False, index=True)  # backup/deploy/compliance_scan/discovery/health_check/command_exec
    status = Column(String(20), default="pending", index=True)  # pending/queued/running/success/failed/cancelled/timeout/partial
    
    # 目标设备（单设备或多设备）
    device_id = Column(Integer, nullable=True, index=True)
    device_ids_json = Column(Text, nullable=True)  # JSON 数组字符串，兼容 SQLite
    
    # 关联的变更单
    change_request_id = Column(Integer, nullable=True)
    
    # Celery 任务 ID
    celery_task_id = Column(String(255), nullable=True, index=True)
    
    # 执行参数（JSON）
    parameters_json = Column(Text, nullable=True)
    
    # 执行结果（JSON）
    result_json = Column(Text, nullable=True)
    
    # 操作人
    operator = Column(String(100), nullable=True)
    
    # 进度
    progress_percent = Column(Integer, default=0)
    
    # 日志输出
    log_output = Column(Text, nullable=True)
    
    # 错误信息
    error_message = Column(String(500), nullable=True)
    
    # 时间戳
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        import json
        return {
            "id": self.id,
            "job_type": self.job_type,
            "status": self.status,
            "device_id": self.device_id,
            "progress_percent": self.progress_percent,
            "error_message": self.error_message,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "result": json.loads(self.result_json) if self.result_json else None,
        }
```

#### 2.1.5 创建 Job API 路由

创建新文件 `app/features/jobs/router.py`：

```python
"""
作业监控 API

提供统一的作业查询和取消接口。
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from app.shared.database import get_db
from app.shared.models_jobs import Job

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.get("")
def list_jobs(
    job_type: Optional[str] = None,
    status: Optional[str] = None,
    device_id: Optional[int] = None,
    skip: int = 0,
    limit: int = Query(20, le=100),
    db: Session = Depends(get_db)
):
    query = db.query(Job).order_by(Job.created_at.desc())
    if job_type:
        query = query.filter(Job.job_type == job_type)
    if status:
        query = query.filter(Job.status == status)
    if device_id:
        query = query.filter(Job.device_id == device_id)
    total = query.count()
    items = query.offset(skip).limit(limit).all()
    return {"total": total, "items": [j.to_dict() for j in items]}


@router.get("/{job_id}")
def get_job(job_id: str, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job.to_dict()


@router.post("/{job_id}/cancel")
def cancel_job(job_id: str, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status not in ("pending", "queued", "running"):
        raise HTTPException(status_code=400, detail=f"Job is {job.status}, cannot cancel")
    
    # 撤销 Celery 任务
    if job.celery_task_id:
        from app.core.celery_app import celery_app
        celery_app.control.revoke(job.celery_task_id, terminate=True)
    
    job.status = "cancelled"
    job.completed_at = __import__('datetime').datetime.utcnow()
    db.commit()
    return {"success": True, "message": "Job cancelled"}
```

在 `app/main.py` 中注册该路由（在现有路由注册部分添加）：
```python
from app.features.jobs.router import router as jobs_router
app.include_router(jobs_router)
```

---

### Task 2.2：统一设备驱动层

#### 2.2.1 创建驱动抽象基类

创建 `app/features/devices/drivers/base.py`（参考 ENTERPRISE_ARCHITECTURE.md 第 5.1 节中的代码规范）

#### 2.2.2 重构现有厂商驱动

**操作步骤**：
1. 创建 `app/features/devices/drivers/` 目录。
2. 将 `app/features/devices/vendor_adapter.py` 中的逻辑迁移到 `app/features/devices/drivers/` 下各文件：
   - `cisco_ios.py` — 继承 `BaseDeviceDriver`，实现接口
   - `cisco_nxos.py` — **新增**，Cisco NX-OS 专用驱动（`cisco_nxos` Netmiko）
   - `huawei_vrp.py` — 继承 `BaseDeviceDriver`
   - `h3c_comware.py` — 继承 `BaseDeviceDriver`
   - `aruba_os.py` — **新增**（见下文详细实现）
   - `fortinet_os.py` — **新增**（见下文详细实现）
3. 创建 `app/features/devices/drivers/registry.py` 驱动注册表。
4. 向下兼容：`app/features/devices/vendor_adapter.py` 保留，内部调用新的驱动注册表。

#### 2.2.3 Aruba OS 驱动实现

创建 `app/features/devices/drivers/aruba_os.py`：

```python
"""Aruba ArubaOS-Switch 驱动 (ProCurve / ArubaOS-Switch)"""

from app.features.devices.drivers.base import BaseDeviceDriver
from typing import List, Dict, Optional


class ArubaOSDriver(BaseDeviceDriver):
    VENDOR = "aruba"
    OS_TYPES = ["aruba", "aruba_os", "aruba-os", "aruba_procurve"]
    NETMIKO_DRIVER = "aruba_os"
    NAPALM_DRIVER = None  # NAPALM 不原生支持 ArubaOS-Switch
    SUPPORTS_ENABLE_MODE = True
    SHOW_RUN_COMMAND = "show running-config"
    SAVE_CONFIG_COMMAND = "write memory"
    CONFIG_MODE_COMMAND = "configure terminal"
    EXIT_CONFIG_MODE = "end"

    def get_running_config(self, connection) -> str:
        return connection.send_command(
            self.SHOW_RUN_COMMAND,
            read_timeout=60,
            expect_string=r"#"
        )

    def get_device_facts(self, connection) -> Dict:
        output = connection.send_command("show version")
        # 使用 TextFSM 解析，NTC-Templates 中有 aruba_os_show_version
        return {"raw_version": output}

    def deploy_config_lines(self, connection, commands: List[str], dry_run: bool = False) -> Dict:
        if dry_run:
            return {"success": True, "dry_run": True, "commands": commands}
        try:
            # ArubaOS 进入配置模式
            output = connection.send_config_set(
                commands,
                enter_config_mode=True,
                exit_config_mode=True,
                delay_factor=2,
            )
            return {"success": True, "output": output}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def save_config(self, connection) -> bool:
        output = connection.send_command(self.SAVE_CONFIG_COMMAND, expect_string=r"#")
        return "error" not in output.lower()

    def get_interfaces(self, connection) -> List[Dict]:
        output = connection.send_command("show interfaces brief")
        return [{"raw": output}]  # TextFSM 解析
```

#### 2.2.4 Fortinet OS 驱动实现

创建 `app/features/devices/drivers/fortinet_os.py`：

```python
"""Fortinet FortiOS 驱动"""

from app.features.devices.drivers.base import BaseDeviceDriver
from typing import List, Dict, Optional


class FortinetDriver(BaseDeviceDriver):
    VENDOR = "fortinet"
    OS_TYPES = ["fortinet", "fortigate", "fortios"]
    NETMIKO_DRIVER = "fortinet"
    NAPALM_DRIVER = None
    SUPPORTS_ENABLE_MODE = False   # FortiOS 无 enable 模式
    SHOW_RUN_COMMAND = "show full-configuration"
    SAVE_CONFIG_COMMAND = "execute cfg save"
    # FortiOS 按资源路径进入配置，无通用 configure terminal
    CONFIG_MODE_COMMAND = ""
    EXIT_CONFIG_MODE = "end"

    def get_running_config(self, connection) -> str:
        # FortiOS show full-configuration 可能很长，使用更长超时
        return connection.send_command(
            self.SHOW_RUN_COMMAND,
            read_timeout=120,
            max_loops=1000,
        )

    def get_device_facts(self, connection) -> Dict:
        output = connection.send_command("get system status")
        return {"raw_status": output}

    def deploy_config_lines(self, connection, commands: List[str], dry_run: bool = False) -> Dict:
        """
        FortiOS 配置部署
        
        注意：FortiOS 使用层级式配置结构（config ... set ... end），
        直接发送命令列表可能无法正确进入/退出配置上下文。
        实际部署时建议使用配置脚本方式（generate-command-script）。
        """
        if dry_run:
            return {"success": True, "dry_run": True, "commands": commands, 
                    "warning": "FortiOS 配置部署需要仔细检查层级结构"}
        try:
            outputs = []
            for cmd in commands:
                output = connection.send_command_timing(
                    cmd,
                    delay_factor=2,
                )
                outputs.append(output)
            return {"success": True, "output": "\n".join(outputs)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def save_config(self, connection) -> bool:
        output = connection.send_command_timing(self.SAVE_CONFIG_COMMAND)
        return True  # FortiOS 自动保存，命令执行即保存

    def get_interfaces(self, connection) -> List[Dict]:
        output = connection.send_command("get system interface physical")
        return [{"raw": output}]
```

#### 2.2.5 在 deploy_service.py 和 napalm_service.py 中使用统一驱动注册表

在所有 `vendor_device_type_map` 的地方（目前分散在至少 5 个文件中），改为调用注册表：

```python
# 旧代码（分散在多处，禁止继续新增）
vendor_device_type_map = {
    'cisco': 'cisco_ios',
    'huawei': 'huawei',
    ...
}
netmiko_device_type = vendor_device_type_map.get(vendor, 'cisco_ios')

# 新代码（统一入口）
from app.features.devices.drivers.registry import DriverRegistry
driver_class = DriverRegistry.get(vendor)
netmiko_device_type = driver_class.NETMIKO_DRIVER
```

**需要修改的文件列表**（搜索 `vendor_device_type_map` 关键词定位所有位置）：
- `app/features/deploy/deploy_service.py` 第 63 行区域
- `app/features/deploy/deploy_stream_service.py` 第 103 行区域（两处）
- `app/features/deploy/cli_stream_service.py` 第 29 行区域
- `app/features/deploy/napalm_service.py`（多处映射，全部替换）

---

### Task 2.3：将备份操作改为 Celery 异步任务

**涉及文件**：`app/features/backups/router.py`（主要），`app/tasks/backup_tasks.py`（新建）

#### 2.3.1 创建备份 Celery 任务

创建新文件 `app/tasks/backup_tasks.py`：

```python
"""配置备份 Celery 任务"""

import json
from datetime import datetime
from loguru import logger
from app.core.celery_app import celery_app


@celery_app.task(
    bind=True,
    name="app.tasks.backup_tasks.backup_device",
    max_retries=2,
    default_retry_delay=30,
    acks_late=True,
)
def backup_device(self, job_id: str, device_id: int, operator: str):
    """
    异步备份单个设备。

    Args:
        job_id: Job 表记录 ID，用于更新状态
        device_id: 目标设备 ID
        operator: 操作人
    """
    from app.shared.database import get_db_manager
    from app.shared.models_jobs import Job
    from app.shared.models import Device
    from app.features.backups.netmiko_service import NetmikoService
    from app.features.credentials.credential_service import CredentialService

    db_manager = get_db_manager()

    with db_manager.session_scope() as db:
        # 更新 Job 状态为 running
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            logger.error(f"Job {job_id} not found")
            return

        job.status = "running"
        job.started_at = datetime.utcnow()
        job.celery_task_id = self.request.id
        db.commit()

        # 获取设备
        device = db.query(Device).filter(Device.id == device_id).first()
        if not device:
            job.status = "failed"
            job.error_message = f"Device {device_id} not found"
            job.completed_at = datetime.utcnow()
            db.commit()
            return

        try:
            # 获取凭证并执行备份（复用现有 NetmikoService 逻辑）
            cred_service = CredentialService(db)
            credentials = cred_service.get_credentials_for_device(device)
            
            netmiko_svc = NetmikoService()
            result = netmiko_svc.backup_device(device, credentials, operator)

            job.status = "success" if result.get("success") else "failed"
            job.result_json = json.dumps(result)
            job.completed_at = datetime.utcnow()
            db.commit()

        except Exception as exc:
            logger.error(f"Backup task failed for device {device_id}: {exc}")
            try:
                self.retry(exc=exc)
            except self.MaxRetriesExceededError:
                job.status = "failed"
                job.error_message = str(exc)
                job.completed_at = datetime.utcnow()
                db.commit()


@celery_app.task(
    bind=True,
    name="app.tasks.backup_tasks.backup_devices_batch",
    acks_late=True,
)
def backup_devices_batch(self, job_id: str, device_ids: list, operator: str):
    """批量备份设备（并发控制通过 Celery chord/group 实现）"""
    from celery import group
    
    subtasks = group(
        backup_device.s(f"{job_id}-{i}", device_id, operator)
        for i, device_id in enumerate(device_ids)
    )
    result = subtasks.apply_async()
    return {"group_id": result.id}
```

#### 2.3.2 修改备份 API 路由改为异步提交

在 `app/features/backups/router.py` 中，找到 `POST /api/backups/backup/{device_id}` 的处理函数，在保留原有同步路径基础上，新增异步路径（用 Query 参数 `async_mode=true` 控制）：

```python
# 新增：异步备份（推荐）
@router.post("/backup/{device_id}/async")
async def backup_device_async(
    device_id: int,
    operator: str = "system",
    db: Session = Depends(get_db)
):
    """提交备份任务到队列，返回 job_id 供轮询"""
    import uuid
    from app.shared.models_jobs import Job
    from app.tasks.backup_tasks import backup_device as backup_task

    job = Job(
        id=str(uuid.uuid4()),
        job_type="backup",
        status="pending",
        device_id=device_id,
        operator=operator,
    )
    db.add(job)
    db.commit()

    backup_task.delay(job_id=job.id, device_id=device_id, operator=operator)

    return {"job_id": job.id, "status": "pending", "message": "备份任务已提交"}
```

---

### Task 2.4：命令黑名单安全检查

创建新文件 `app/core/command_guard.py`：

```python
"""
设备命令安全守卫

在所有设备操作执行前调用 validate_commands 检查高危命令。
"""

from typing import List

# 禁止执行的命令（精确匹配或前缀匹配）
DANGEROUS_COMMANDS_EXACT = frozenset({
    "reload", "write erase", "erase startup-config",
    "factory-reset", "execute factoryreset",  # Fortinet
    "reset saved-configuration",              # Huawei/H3C
    "reset factory-configuration",            # Huawei
    "execute cfg reset",                      # Fortinet
    "crypto key zeroize",
})

# 高危命令前缀（匹配开头）
DANGEROUS_COMMAND_PREFIXES = (
    "delete ",
    "format ",
    "no crypto key",
    "no ip ssh",
    "no aaa",
)

# 需要二次确认的命令（不直接阻止，但需审计记录 + 通知）
HIGH_RISK_COMMANDS = frozenset({
    "shutdown",         # 关闭接口
    "no shutdown",      # 不危险，但高频操作记录
    "no service password-encryption",
    "service password-encryption",
})


class CommandGuardError(Exception):
    """命令安全检查失败"""
    def __init__(self, command: str, reason: str):
        self.command = command
        self.reason = reason
        super().__init__(f"命令 '{command}' 被安全守卫拒绝: {reason}")


def validate_commands(commands: List[str], allow_high_risk: bool = False) -> List[str]:
    """
    验证命令列表的安全性。

    Args:
        commands: 要执行的命令列表
        allow_high_risk: 是否允许高风险命令（需经审批流程）

    Returns:
        验证通过的命令列表（可能经过清洗）

    Raises:
        CommandGuardError: 发现危险命令时抛出
    """
    high_risk_found = []
    
    for cmd in commands:
        cmd_lower = cmd.strip().lower()
        
        # 检查精确匹配危险命令
        if cmd_lower in DANGEROUS_COMMANDS_EXACT:
            raise CommandGuardError(cmd, "属于禁止执行命令列表")
        
        # 检查前缀匹配
        for prefix in DANGEROUS_COMMAND_PREFIXES:
            if cmd_lower.startswith(prefix):
                raise CommandGuardError(cmd, f"命令前缀 '{prefix}' 属于危险操作")
        
        # 记录高风险命令
        if cmd_lower in HIGH_RISK_COMMANDS:
            high_risk_found.append(cmd)
    
    if high_risk_found and not allow_high_risk:
        raise CommandGuardError(
            str(high_risk_found),
            "包含高风险命令，请在变更审批通过后执行"
        )
    
    return commands
```

在 `app/features/deploy/deploy_service.py` 的 `deploy_config` 方法中，在发送命令前调用：
```python
from app.core.command_guard import validate_commands, CommandGuardError

# 在 connection.send_config_set(commands) 之前
try:
    validate_commands(commands)
except CommandGuardError as e:
    return {"success": False, "message": str(e), "errors": [str(e)]}
```

---

### Phase 2 验收标准

- [ ] 备份操作有同步和异步两个路径，异步路径通过 Celery 执行
- [ ] Job 表正常写入，`GET /api/jobs` 可查询作业历史
- [ ] 驱动注册表统一，代码中不再有分散的 `vendor_device_type_map` 字典
- [ ] Aruba OS 和 Fortinet 驱动已创建（可 mock 测试，无需真实设备）
- [ ] 命令黑名单在所有部署路径中生效
- [ ] `docker-compose` 中 Worker 和 Beat 容器正常启动

---

## Phase 3：AI 平台化

> **目标**：构建真正的 RAG 知识库，建立 AI 工具治理，完善 AI 工作台。  
> **前置条件**：Phase 1 完成，Phase 2 可并行。

---

### Task 3.1：配置 pgvector 扩展

```sql
-- 连接 PostgreSQL 后执行
CREATE EXTENSION IF NOT EXISTS vector;

-- 验证
SELECT * FROM pg_extension WHERE extname = 'vector';
```

在 `requirements.txt` 中添加：
```
pgvector==0.3.2
langchain==0.2.16
langchain-openai==0.1.23
langchain-community==0.2.16
openai==1.40.0
```

---

### Task 3.2：创建知识文档 DB 模型

在 `app/shared/models.py` 中添加（PostgreSQL 运行时使用 vector 类型）：

```python
class AIKnowledgeDocument(Base):
    """AI 知识库文档表（RAG 向量索引）"""
    __tablename__ = "ai_knowledge_documents"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    doc_type = Column(String(50), nullable=False, index=True)
    # doc_type 枚举值：device_config / fault_record / sop / vendor_doc / compliance_rule / change_record
    
    title = Column(String(300), nullable=False)
    content = Column(Text, nullable=False)
    
    # 关联的目标（可选）
    device_id = Column(Integer, nullable=True, index=True)
    
    # 元数据（JSON），如：设备厂商、备份时间、故障编号等
    metadata_json = Column(Text, nullable=True)
    
    # 向量嵌入维度（PostgreSQL + pgvector 时使用）
    # SQLite 不支持 vector 类型，此列在 SQLite 测试中可忽略
    # 生产部署时通过 Alembic migration 添加: ALTER TABLE ai_knowledge_documents ADD COLUMN embedding vector(1536)
    
    # 索引状态
    indexed_at = Column(DateTime, nullable=True)
    embedding_model = Column(String(100), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

---

### Task 3.3：创建 RAG 引擎

创建新文件 `app/services/rag/rag_engine.py`：

```python
"""
RAG 检索引擎

使用 LangChain + pgvector 构建企业级知识检索能力。
"""

from typing import List, Optional, Dict
from loguru import logger


class RAGEngine:
    """RAG 知识检索引擎"""

    def __init__(self):
        self._vector_store = None
        self._embeddings = None

    def _get_embeddings(self):
        """获取 Embedding 模型（复用 LiteLLM 配置）"""
        if self._embeddings:
            return self._embeddings
        
        from langchain_openai import OpenAIEmbeddings
        from app.shared.config import get_config
        
        config = get_config()
        # 使用 LiteLLM 代理，兼容 OpenAI 接口
        self._embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small",
            base_url=config.ai.base_url if hasattr(config, 'ai') else None,
            api_key=config.ai.api_key if hasattr(config, 'ai') else "not-set",
            dimensions=1536,
        )
        return self._embeddings

    def _get_vector_store(self, db):
        """获取 pgvector 向量存储"""
        if self._vector_store:
            return self._vector_store
        
        try:
            from langchain_community.vectorstores import PGVector
            from app.shared.config import get_config
            
            config = get_config()
            if not config.database.is_postgresql:
                logger.warning("RAG 需要 PostgreSQL + pgvector，当前使用 SQLite，知识检索不可用")
                return None
            
            # PGVector 使用 psycopg2 同步连接
            pg_url = config.database.url.replace("postgresql+asyncpg", "postgresql+psycopg2")
            
            self._vector_store = PGVector(
                connection_string=pg_url,
                embedding_function=self._get_embeddings(),
                collection_name="nas_knowledge",
                pre_delete_collection=False,
            )
            return self._vector_store
        except ImportError:
            logger.error("pgvector 未安装，请运行: pip install pgvector")
            return None

    def index_device_config(self, device_id: int, device_name: str, config_content: str, db) -> bool:
        """将设备配置索引到向量库"""
        vector_store = self._get_vector_store(db)
        if not vector_store:
            return False
        
        try:
            from langchain.text_splitter import RecursiveCharacterTextSplitter
            from langchain.schema import Document
            
            # 按配置段落分块（interface/router/policy 等）
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=100,
                separators=["\n!\n", "\n !\n", "\ninterface ", "\nrouter ", "\n"],
            )
            
            chunks = splitter.split_text(config_content)
            docs = [
                Document(
                    page_content=chunk,
                    metadata={
                        "doc_type": "device_config",
                        "device_id": device_id,
                        "device_name": device_name,
                    }
                )
                for chunk in chunks
            ]
            
            vector_store.add_documents(docs)
            logger.info(f"设备 {device_name} 配置已索引，共 {len(docs)} 个块")
            return True
        except Exception as e:
            logger.error(f"配置索引失败: {e}")
            return False

    def search(
        self,
        query: str,
        doc_types: Optional[List[str]] = None,
        device_id: Optional[int] = None,
        top_k: int = 5,
        db = None,
    ) -> List[Dict]:
        """
        语义检索知识库

        Args:
            query: 检索问题
            doc_types: 限制文档类型（None 表示全部）
            device_id: 限制设备范围
            top_k: 返回最相关的 K 个结果

        Returns:
            相关文档列表，按相似度降序
        """
        vector_store = self._get_vector_store(db)
        if not vector_store:
            return []
        
        try:
            filter_dict = {}
            if doc_types:
                filter_dict["doc_type"] = {"$in": doc_types}
            if device_id:
                filter_dict["device_id"] = device_id
            
            docs_with_scores = vector_store.similarity_search_with_score(
                query=query,
                k=top_k,
                filter=filter_dict or None,
            )
            
            return [
                {
                    "content": doc.page_content,
                    "metadata": doc.metadata,
                    "score": float(score),
                }
                for doc, score in docs_with_scores
            ]
        except Exception as e:
            logger.error(f"向量检索失败: {e}")
            return []


# 单例
rag_engine = RAGEngine()
```

---

### Task 3.4：统一 AI 工具注册表

创建新文件 `app/services/ai_tools/registry.py`：

```python
"""
AI 工具注册表

所有可被 AI Agent 调用的工具必须在此注册。
每个工具声明所需权限、是否只读、超时限制。
"""

from dataclasses import dataclass, field
from typing import Callable, List, Optional, Dict
from loguru import logger


@dataclass
class AITool:
    name: str
    description: str
    parameters_schema: dict
    handler: Callable
    requires_permission: str    # 如 "device:read", "config:write"
    is_readonly: bool = True
    is_destructive: bool = False
    timeout_seconds: int = 30
    rate_limit_per_minute: int = 10


class AIToolRegistry:
    _tools: Dict[str, AITool] = {}

    @classmethod
    def register(cls, tool: AITool):
        if tool.is_destructive and tool.is_readonly:
            raise ValueError(f"工具 {tool.name} 不能同时是只读和破坏性操作")
        cls._tools[tool.name] = tool
        logger.info(f"AI Tool 已注册: {tool.name} (readonly={tool.is_readonly})")

    @classmethod
    def get(cls, name: str) -> Optional[AITool]:
        return cls._tools.get(name)

    @classmethod
    def list_tools(cls) -> List[Dict]:
        return [
            {
                "name": t.name,
                "description": t.description,
                "is_readonly": t.is_readonly,
                "requires_permission": t.requires_permission,
            }
            for t in cls._tools.values()
        ]

    @classmethod
    def get_readonly_tools(cls) -> List[AITool]:
        return [t for t in cls._tools.values() if t.is_readonly]


# 注册内置工具
def _register_builtin_tools():
    from app.services.ai_tools.builtin import (
        get_device_config_tool,
        get_device_facts_tool,
        search_knowledge_base_tool,
        get_fault_history_tool,
        get_compliance_status_tool,
    )
    for tool in [
        get_device_config_tool,
        get_device_facts_tool,
        search_knowledge_base_tool,
        get_fault_history_tool,
        get_compliance_status_tool,
    ]:
        AIToolRegistry.register(tool)


_register_builtin_tools()
```

---

### Task 3.5：在备份完成后自动触发知识库索引

在 `app/tasks/backup_tasks.py` 的备份成功分支中，添加：

```python
# 备份成功后触发 RAG 索引（仅 PostgreSQL 环境）
if result.get("success") and config.database.is_postgresql:
    from app.tasks.ai_tasks import index_device_config_task
    backup_content = result.get("config_content", "")
    if backup_content:
        index_device_config_task.delay(
            device_id=device_id,
            device_name=device.name,
            config_content=backup_content,
        )
```

创建 `app/tasks/ai_tasks.py`：

```python
"""AI 任务：知识库索引、分析等"""

from app.core.celery_app import celery_app


@celery_app.task(
    name="app.tasks.ai_tasks.index_device_config",
    queue="ai_tasks",
    soft_time_limit=60,
    time_limit=120,
)
def index_device_config_task(device_id: int, device_name: str, config_content: str):
    """将设备配置索引到 RAG 知识库"""
    from app.services.rag.rag_engine import rag_engine
    from app.shared.database import get_db_manager
    
    db_manager = get_db_manager()
    with db_manager.session_scope() as db:
        success = rag_engine.index_device_config(device_id, device_name, config_content, db)
    
    return {"success": success, "device_id": device_id}
```

---

### Phase 3 验收标准

- [ ] PostgreSQL + pgvector 扩展正常启用
- [ ] 备份成功后自动触发 RAG 索引（可在 `ai_knowledge_documents` 表中看到记录）
- [ ] `GET /api/ai/search` 接口能返回语义检索结果
- [ ] AI 工具注册表包含至少 5 个内置工具
- [ ] AI 分析请求在 LLM 不可用时返回 `{ "success": false, "error": "...", "degraded": true }` 而非 500 错误

---

## Phase 4：前端迁移（React + TypeScript + Ant Design）

> **目标**：将前端从 Vue 3 + Element Plus + JavaScript 迁移到 React 18 + TypeScript + Ant Design 5。  
> **策略**：新旧前端并行，按业务模块逐步替换。Vue 3 版本继续服务已有功能，新功能优先在 React 端实现。  
> **前置条件**：Phase 1 完成（API 稳定）。

---

### Task 4.1：初始化 React 项目

在仓库根目录创建 `frontend-react/` 目录：

```bash
cd c:\AI_Projects\network-automation-system-master
npm create vite@latest frontend-react -- --template react-ts
cd frontend-react
npm install antd @ant-design/icons @ant-design/charts
npm install @tanstack/react-query axios zustand
npm install react-router-dom
npm install -D @types/react @types/react-dom vitest @testing-library/react
```

**初始 `frontend-react/` 结构**（参考 ENTERPRISE_ARCHITECTURE.md 第 10.1 节）

---

### Task 4.2：配置 API 客户端

创建 `frontend-react/src/api/client.ts`：

```typescript
import axios, { AxiosInstance, InternalAxiosRequestConfig, AxiosResponse } from 'axios'

const apiClient: AxiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? '/api',
  timeout: 30_000,
  withCredentials: true,  // 为 httpOnly Cookie 做准备
})

// 请求拦截：附加 Bearer Token（短期过渡，Phase 4 完成后改 Cookie）
apiClient.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = localStorage.getItem('accessToken')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// 响应拦截：统一错误处理
apiClient.interceptors.response.use(
  (response: AxiosResponse) => response.data,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('accessToken')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export default apiClient
```

---

### Task 4.3：迁移顺序（按模块优先级）

| 优先级 | 模块 | Vue 3 对应页面 | 理由 |
|---|---|---|---|
| 1 | AI 分析中心 | `AIAnalysis.vue`, `DeviceHealth.vue` | 全新能力，无历史包袱 |
| 2 | 设备管理 | `Devices.vue`, `DeviceDetail.vue` | 访问频率最高 |
| 3 | 变更管理（新） | 无对应 | Phase 2 新功能，直接在 React 实现 |
| 4 | 作业监控（新） | 无对应 | Phase 2 新功能 |
| 5 | 故障管理 | `Faults.vue`, `FaultDetail.vue` | 业务核心 |
| 6 | 配置备份 | `Backups.vue` | 业务核心 |
| 7 | 配置部署 | `Deploy.vue` | 高风险，需充分测试 |
| 8 | 合规检查 | `Compliance.vue` | |
| 9 | 其余模块 | ... | |

---

### Task 4.4：Nginx 双前端路由配置

在迁移期间，使用 Nginx 实现路由分流：Vue 3 前端处理已有路由，React 前端处理新路由。

在 `frontend/nginx.conf`（如无则创建）中：

```nginx
server {
    listen 80;
    
    # 新前端（React）— AI 分析、作业监控、变更管理（新模块优先迁移）
    location ~ ^/(ai-analysis|device-health|jobs|changes) {
        proxy_pass http://nas-frontend-react;
    }
    
    # 旧前端（Vue 3）— 其他模块
    location / {
        proxy_pass http://nas-frontend-vue;
    }
    
    # API 代理
    location /api {
        proxy_pass http://nas-backend:8000;
    }
}
```

---

### Phase 4 验收标准

- [ ] React 前端可独立启动，AI 分析模块完整可用
- [ ] TypeScript 严格模式，无 `any` 类型（工具类除外）
- [ ] React Query 管理所有服务端状态，无手动 `useEffect` 数据获取
- [ ] 所有 API 调用有对应的 TypeScript 类型定义
- [ ] 迁移完成后 Vue 3 前端依然可用（并行期不得破坏旧功能）
- [ ] Ant Design 组件使用，无自定义 CSS 样式与 Element Plus 混用

---

## 全局开发规范（所有阶段适用）

### 代码提交规范

```
feat(phase1): migrate database config to support postgresql
fix(security): restrict cors to configured origins only
refactor(drivers): unify vendor driver via DriverRegistry
feat(phase2): add job model and celery backup task
```

### 测试要求

每个 Task 完成后必须：
1. 新增的服务/工具有对应的单元测试（`tests/test_xxx.py`）
2. 测试覆盖率不低于修改前水平
3. 所有测试在 SQLite 内存模式下通过（CI 无需 PostgreSQL）
4. 关键路径（备份、部署、认证）有集成测试

### 禁止操作

- 禁止在 API 路由函数（FastAPI endpoint）中直接执行设备 SSH 命令（Phase 2 后）
- 禁止在代码中硬编码 IP 地址、用户名、密码
- 禁止 `allow_origins=["*"]`（Phase 1 完成后）
- 禁止在日志中输出任何密码、Token、SSH Key
- 禁止使用 `sqlite3` 模块直接操作数据库（统一通过 SQLAlchemy）

---

## 技术债清单（按优先级）

| ID | 类型 | 描述 | 文件/位置 | 修复阶段 |
|---|---|---|---|---|
| TD-001 | 安全 | CORS 允许 `*` 通配符 | `app/main.py:70` | Phase 1 Task 1.2 |
| TD-002 | 安全 | 认证默认关闭 | `app/shared/config.py:116` | Phase 1 Task 1.3 |
| TD-003 | 安全 | JWT 默认弱 Secret | `app/shared/config.py:117` | Phase 1 Task 1.3 |
| TD-004 | 安全 | Token 存 localStorage | `frontend/src/views/Login.vue:110` | Phase 1 Task 1.5 / Phase 4 |
| TD-005 | 架构 | 双后端并存 | `backend/` 目录 | Phase 1 Task 1.1 |
| TD-006 | 数据库 | SQLite 单写锁 | `app/shared/database.py` | Phase 1 Task 1.4 |
| TD-007 | 架构 | API 请求线程直接执行设备命令 | 多处 | Phase 2 Task 2.3+ |
| TD-008 | 架构 | vendor_device_type_map 分散维护 | 5+ 文件 | Phase 2 Task 2.2 |
| TD-009 | 功能 | 缺少 Aruba/Fortinet 驱动 | `vendor_adapter.py` | Phase 2 Task 2.2 |
| TD-010 | 功能 | 缺少命令黑名单防护 | 所有 deploy 路径 | Phase 2 Task 2.4 |
| TD-011 | AI | 无 RAG 知识库 | `app/services/adk/` | Phase 3 |
| TD-012 | AI | AI 工具无统一治理 | `app/services/adk/agents/` | Phase 3 Task 3.4 |
| TD-013 | 前端 | Vue 3 + JavaScript（非目标栈） | `frontend/` | Phase 4 |
| TD-014 | 可观测 | 日志非结构化 JSON | 多处 `loguru` 使用 | Phase 2+ |
| TD-015 | 迁移脚本 | `render_as_batch` 绑定 SQLite | `migrations/env.py:38` | Phase 1 Task 1.4.4 |

---

*本文档由 GitHub Copilot (Claude Sonnet 4.6) 生成于 2026-06-05。*  
*配套文档：ENTERPRISE_ARCHITECTURE.md（企业级目标架构设计文档）*
