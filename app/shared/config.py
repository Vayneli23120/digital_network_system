"""
应用配置管理

Fail-fast configuration: 启动时验证所有关键配置，缺失必填项立即报错退出。
"""

import os
import re
import sys
import yaml
from pathlib import Path
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator

# DatabaseConfig.url 的占位默认值。它是普通字符串而不是 f-string，
# 出现这个值说明「配置里没有显式指定数据库 URL」
_URL_PLACEHOLDER = "sqlite+aiosqlite:///{os.path.join(os.getcwd(), 'data', 'nas.db')}"


def describe_db_url(url: str) -> str:
    """把数据库 URL 脱敏成可以打印到日志里的形式（隐去密码）"""
    if not url:
        return "(未配置)"
    return re.sub(r"://([^:/@]+):[^@]*@", r"://\1:***@", url)


class AlertEmailConfig(BaseModel):
    enabled: bool = False
    smtp_host: str = "smtp.company.com"
    smtp_port: int = 587
    use_tls: bool = True
    username: str = ""
    password: str = ""
    from_addr: str = ""
    recipients: List[str] = []
    notify_on: List[str] = ["backup_failure", "device_unreachable"]


class AlertWeChatWorkConfig(BaseModel):
    """企业微信 Webhook 告警配置"""
    enabled: bool = False
    webhook_url: str = ""


class AlertDingTalkConfig(BaseModel):
    """钉钉 Webhook 告警配置"""
    enabled: bool = False
    webhook_url: str = ""
    secret: str = ""


class AlertsConfig(BaseModel):
    """告警通知配置 — 支持多渠道"""
    enabled: bool = False
    email: AlertEmailConfig = Field(default_factory=AlertEmailConfig)
    wechat_work: AlertWeChatWorkConfig = Field(default_factory=AlertWeChatWorkConfig)
    dingtalk: AlertDingTalkConfig = Field(default_factory=AlertDingTalkConfig)
    channels: List[str] = []  # ["email", "wechat_work", "dingtalk"]


class RedisCacheConfig(BaseModel):
    """Redis 缓存配置"""
    enabled: bool = False
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: str = ""
    default_ttl: int = 60  # seconds


class CeleryConfig(BaseModel):
    """Celery 任务队列配置"""
    broker_url: str = Field(
        default="redis://localhost:6379/1",
        description="Celery broker URL，支持 redis:// 或 amqp://"
    )
    result_backend: str = Field(
        default="redis://localhost:6379/1",
        description="Celery result backend URL"
    )

    @field_validator('broker_url', 'result_backend')
    @classmethod
    def validate_redis_url(cls, v: str) -> str:
        """验证 Celery broker/backend URL"""
        if not v.startswith(('redis://', 'rediss://', 'amqp://')):
            raise ValueError("Celery broker/backend 必须使用 redis:// 或 amqp:// URL")
        return v


class StorageConfig(BaseModel):
    backup_dir: str = "./backups"
    photo_dir: str = "./assets/devices"
    log_dir: str = "./logs"
    max_backups_per_device: int = 30
    backup_retention_days: int = 365

    @field_validator('backup_dir', 'photo_dir', 'log_dir')
    @classmethod
    def check_dir_writable(cls, v: str) -> str:
        """验证目录路径可访问（如果不存在则尝试创建）"""
        p = Path(v)
        if not p.exists():
            try:
                p.mkdir(parents=True, exist_ok=True)
            except PermissionError:
                print(f"[CONFIG ERROR] 无法创建目录: {v}", file=sys.stderr)
                raise ValueError(f"目录不可写且无法创建: {v}")
        elif not os.access(v, os.W_OK):
            print(f"[CONFIG ERROR] 目录无写权限: {v}", file=sys.stderr)
            raise ValueError(f"目录无写权限: {v}")
        return v


class ConsoleConfig(BaseModel):
    baudrate: int = 9600
    bytesize: int = 8
    parity: str = "N"
    stopbits: int = 1
    timeout: int = 30
    command_delay: float = 0.5


class DatabaseConfig(BaseModel):
    """数据库配置 - 支持 SQLite (开发) 和 PostgreSQL (生产)"""
    # 数据库 URL（优先使用此字段）
    url: str = Field(
        default=_URL_PLACEHOLDER,
        description="数据库连接 URL，支持 sqlite+aiosqlite 和 postgresql+asyncpg"
    )
    # SQLite 专用配置（兼容旧配置）
    type: str = "sqlite"
    sqlite_path: str = "./data/nas.db"
    # PostgreSQL 连接池配置
    pool_size: int = Field(default=10, description="连接池基础连接数")
    max_overflow: int = Field(default=20, description="连接池溢出连接数")
    pool_timeout: int = Field(default=30, description="获取连接超时秒数")
    pool_recycle: int = Field(default=1800, description="连接回收时间秒数")
    echo: bool = Field(default=False, description="是否打印 SQL 语句")

    @field_validator('url')
    @classmethod
    def validate_db_url(cls, v: str) -> str:
        """验证数据库 URL 格式"""
        allowed_schemes = [
            'sqlite', 'sqlite+aiosqlite',
            'postgresql', 'postgresql+asyncpg', 'postgresql+psycopg2'
        ]
        scheme = v.split('://')[0] if '://' in v else ''
        if not any(v.startswith(s) for s in allowed_schemes):
            raise ValueError(f"不支持的数据库类型，允许: {allowed_schemes}")
        return v

    @field_validator('sqlite_path')
    @classmethod
    def check_sqlite_path(cls, v: str) -> str:
        """验证 SQLite 数据库路径"""
        p = Path(v)
        parent = p.parent
        if not parent.exists():
            try:
                parent.mkdir(parents=True, exist_ok=True)
            except PermissionError:
                print(f"[CONFIG ERROR] 无法创建数据库目录: {parent}", file=sys.stderr)
                raise ValueError(f"无法创建数据库目录: {parent}")
        if p.exists() and not os.access(v, os.W_OK):
            print(f"[CONFIG ERROR] 数据库文件无写权限: {v}", file=sys.stderr)
            raise ValueError(f"数据库文件无写权限: {v}")
        return v

    @property
    def is_postgresql(self) -> bool:
        """是否使用 PostgreSQL"""
        return 'postgresql' in self.get_effective_url()

    @property
    def is_sqlite(self) -> bool:
        """是否使用 SQLite"""
        url = self.get_effective_url()
        return 'sqlite' in url and 'postgresql' not in url

    @property
    def url_source(self) -> str:
        """有效 URL 的来源，用于启动日志与排障"""
        if self.url and self.url != _URL_PLACEHOLDER:
            return "config.yaml"
        if os.environ.get("DATABASE_URL"):
            return "DATABASE_URL 环境变量"
        return "内置默认值 (SQLite)"

    def get_effective_url(self) -> str:
        """获取有效的数据库 URL

        优先级：config.yaml 的 database.url > DATABASE_URL 环境变量 > 本地 SQLite 默认值。
        环境变量只在配置文件没给出 URL 时兜底，因此不会覆盖服务器上已有的配置。
        """
        if self.url and self.url != _URL_PLACEHOLDER:
            return self.url

        env_url = os.environ.get("DATABASE_URL")
        if env_url:
            return env_url

        return f"sqlite+aiosqlite:///{self.sqlite_path}"


class SSOConfig(BaseModel):
    """单点登录配置 —— Microsoft Entra ID (OIDC 授权码流)

    默认关闭。等 IT 批下应用注册后，只需在 config.yaml 里填三个值并把
    enabled 置为 true，前端登录页的 SSO 入口即可用，无需改代码：

        sso:
          enabled: true
          tenant_id: "<目录 ID>"
          client_id: "<应用程序 ID>"
          client_secret: "${SSO_CLIENT_SECRET}"     # 从环境变量注入，不要写死
          redirect_uri: "https://<内网主机>/api/auth/sso/callback"

    注意：MFA 由 Entra ID 侧负责，本系统不实现第二因子。
    另需确认服务器能出站访问 login.microsoftonline.com（换取令牌 + 拉取 JWKS 验签）。
    """
    enabled: bool = False
    provider: str = Field(default="entra", description="身份提供方标识，目前仅支持 entra")
    display_name: str = Field(default="企业账号登录", description="登录页 SSO 入口的显示名")
    tenant_id: str = ""
    client_id: str = ""
    client_secret: str = ""
    redirect_uri: str = ""
    scopes: List[str] = Field(default=["openid", "profile", "email"])
    # 首次通过 SSO 登录时自动建号，并赋予下面这个角色
    auto_provision: bool = True
    default_role: str = Field(default="viewer", description="SSO 新用户的默认角色")

    @property
    def authority(self) -> str:
        """Entra ID 的 authority URL"""
        return f"https://login.microsoftonline.com/{self.tenant_id}" if self.tenant_id else ""

    def missing_fields(self) -> List[str]:
        """返回启用 SSO 还缺哪些配置项，供 /api/auth/sso/status 自检"""
        required = {
            "tenant_id": self.tenant_id,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "redirect_uri": self.redirect_uri,
        }
        return [name for name, value in required.items() if not value]


class SecurityConfig(BaseModel):
    auth_enabled: bool = False  # 认证功能开关，默认关闭
    jwt_secret: str = "your-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7
    # CORS 安全配置
    cors_allowed_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:5173"],
        description="生产环境必须配置为实际域名，禁止使用 * 通配符"
    )
    cors_allow_credentials: bool = True

    @field_validator('cors_allowed_origins')
    @classmethod
    def check_cors_origins(cls, v: List[str]) -> List[str]:
        """CORS origins 安全检查"""
        if "*" in v:
            print("[CONFIG WARNING] CORS 使用 * 通配符，生产环境请配置具体域名", file=sys.stderr)
        return v

    @field_validator('jwt_secret')
    @classmethod
    def check_jwt_secret(cls, v: str) -> str:
        """JWT Secret 安全检查"""
        weak_secrets = [
            'your-secret-key-change-in-production',
            'secret',
            'password',
            'changeme',
            '123456',
        ]
        if v.lower() in weak_secrets:
            print("[CONFIG WARNING] JWT secret 使用了默认值！生产环境请设置强密码", file=sys.stderr)
        elif len(v) < 32:
            print(f"[CONFIG WARNING] JWT secret 长度 < 32 位，安全性不足", file=sys.stderr)
        return v

    @field_validator('jwt_access_token_expire_minutes')
    @classmethod
    def check_token_expiry(cls, v: int) -> int:
        """Token 过期时间合理性检查"""
        if v < 5:
            print(f"[CONFIG WARNING] jwt_access_token_expire_minutes={v} 过短，建议 >= 5", file=sys.stderr)
        elif v > 1440:  # 24小时
            print(f"[CONFIG WARNING] jwt_access_token_expire_minutes={v} 过长，建议 <= 1440", file=sys.stderr)
        return v


class AppConfig(BaseModel):
    name: str = "Network Automation System"
    version: str = "1.3.0"
    debug: bool = False


class Config(BaseModel):
    app: AppConfig = Field(default_factory=AppConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    sso: SSOConfig = Field(default_factory=SSOConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    console: ConsoleConfig = Field(default_factory=ConsoleConfig)
    alerts: AlertsConfig = Field(default_factory=AlertsConfig)
    cache: RedisCacheConfig = Field(default_factory=RedisCacheConfig)
    celery: CeleryConfig = Field(default_factory=CeleryConfig)
    logging: dict = Field(default_factory=lambda: {"level": "INFO"})

    @classmethod
    def load(cls, config_path: str = "config.yaml") -> "Config":
        """从 YAML 文件加载配置"""
        path = Path(config_path)

        if not path.exists():
            # 配置文件缺失时会静默回退到本地 SQLite。生产是 PostgreSQL 时，
            # 这种回退会让服务连上一个空的开发库而不报任何错，所以必须显式告警。
            fallback = cls()
            fallback._apply_security_env_overrides()
            fallback.validate()
            effective = fallback.database.get_effective_url()
            print(
                f"[CONFIG WARNING] 未找到配置文件 {path.resolve()}，"
                f"已回退到内置默认配置", file=sys.stderr
            )
            print(
                f"[CONFIG WARNING] 生效的数据库: {describe_db_url(effective)}"
                f"（来源：{fallback.database.url_source}）", file=sys.stderr
            )
            if fallback.database.is_sqlite:
                print(
                    "[CONFIG WARNING] 这是本地开发用的 SQLite。若本机应连 PostgreSQL，"
                    "请在工作目录放置 config.yaml 或设置 DATABASE_URL 环境变量后重试",
                    file=sys.stderr
                )
            if Path("config.example.yaml").exists():
                print("[CONFIG WARNING] 可复制 config.example.yaml 为 config.yaml 后修改", file=sys.stderr)
            return fallback

        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        # 环境变量替换
        data = cls._replace_env_vars(data)

        config = cls(**data)
        config._apply_security_env_overrides()
        # Fail-fast 验证
        config.validate()
        return config

    def _apply_security_env_overrides(self) -> None:
        """应用容器/进程环境中的认证配置。

        这些变量已在 docker-compose.yml 与 .env.example 中公开，必须真实生效。
        """
        if "AUTH_ENABLED" in os.environ:
            self.security.auth_enabled = self._parse_bool_env(
                "AUTH_ENABLED", os.environ["AUTH_ENABLED"]
            )
        if "APP_DEBUG" in os.environ:
            self.app.debug = self._parse_bool_env("APP_DEBUG", os.environ["APP_DEBUG"])
        if "JWT_SECRET" in os.environ:
            self.security.jwt_secret = os.environ["JWT_SECRET"]
        if "CORS_ALLOWED_ORIGINS" in os.environ:
            self.security.cors_allowed_origins = [
                origin.strip()
                for origin in os.environ["CORS_ALLOWED_ORIGINS"].split(",")
                if origin.strip()
            ]

    @staticmethod
    def _parse_bool_env(name: str, value: str) -> bool:
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
        raise ValueError(f"{name} 必须是 true/false、1/0、yes/no 或 on/off")

    @staticmethod
    def _replace_env_vars(obj):
        """递归替换配置中的 ${ENV_VAR} 为环境变量值"""
        if isinstance(obj, dict):
            return {k: Config._replace_env_vars(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [Config._replace_env_vars(item) for item in obj]
        elif isinstance(obj, str) and obj.startswith("${") and obj.endswith("}"):
            env_var = obj[2:-1]
            return os.environ.get(env_var, "")
        return obj

    def validate(self) -> "Config":
        """应用级配置验证 — 跨字段检查

        在 Config.load() 后自动调用，失败时打印错误并退出。
        """
        weak_secrets = [
            'your-secret-key-change-in-production',
            'secret',
            'password',
            'changeme',
            '123456',
        ]

        # 检查认证已启用时的安全配置
        if self.security.auth_enabled:
            # JWT secret 不能是默认值或弱密码
            if self.security.jwt_secret.lower() in weak_secrets:
                print(
                    "[CONFIG ERROR] auth_enabled=true 但 jwt_secret 仍为默认值或弱密码！",
                    file=sys.stderr
                )
                print("请在 config.yaml 或环境变量中设置 security.jwt_secret 为强密码", file=sys.stderr)
                sys.exit(1)

            # JWT secret 长度必须 >= 32
            if len(self.security.jwt_secret) < 32:
                print(
                    f"[CONFIG ERROR] auth_enabled=true 但 jwt_secret 长度不足 32 位（当前 {len(self.security.jwt_secret)} 位）",
                    file=sys.stderr
                )
                print("生产环境要求 JWT secret 长度 >= 32 位", file=sys.stderr)
                sys.exit(1)

            # CORS 不能使用 * 通配符
            if "*" in self.security.cors_allowed_origins:
                print(
                    "[CONFIG ERROR] auth_enabled=true 时 cors_allowed_origins 禁止使用 * 通配符！",
                    file=sys.stderr
                )
                print("请配置具体的域名，如: ['https://your-domain.com']", file=sys.stderr)
                sys.exit(1)

        # 检查备份目录和存储目录不是同一路径
        dirs = [self.storage.backup_dir, self.storage.photo_dir, self.storage.log_dir]
        if len(set(dirs)) != len(dirs):
            print("[CONFIG ERROR] storage 目录下 backup_dir/photo_dir/log_dir 不能相同", file=sys.stderr)
            sys.exit(1)

        return self


# 全局配置实例
_config: Optional[Config] = None


def get_config() -> Config:
    """获取全局配置实例"""
    global _config
    if _config is None:
        _config = Config.load()
    return _config


# 兼容性别名 - 部分代码引用 settings
# 注意：这会在首次 import 时加载配置
settings = get_config()


def reload_config() -> Config:
    """重新加载配置"""
    global _config
    _config = Config.load()
    return _config
