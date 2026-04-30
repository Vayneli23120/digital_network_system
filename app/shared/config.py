"""
应用配置管理

Fail-fast configuration: 启动时验证所有关键配置，缺失必填项立即报错退出。
"""

import os
import sys
import yaml
from pathlib import Path
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator


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
    type: str = "sqlite"
    sqlite_path: str = "./data/nas.db"

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
        # 如果文件已存在，检查是否可写
        if p.exists() and not os.access(v, os.W_OK):
            print(f"[CONFIG ERROR] 数据库文件无写权限: {v}", file=sys.stderr)
            raise ValueError(f"数据库文件无写权限: {v}")
        return v


class SecurityConfig(BaseModel):
    auth_enabled: bool = False  # 认证功能开关，默认关闭
    jwt_secret: str = "your-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7

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
    storage: StorageConfig = Field(default_factory=StorageConfig)
    console: ConsoleConfig = Field(default_factory=ConsoleConfig)
    alerts: AlertsConfig = Field(default_factory=AlertsConfig)
    cache: RedisCacheConfig = Field(default_factory=RedisCacheConfig)
    logging: dict = Field(default_factory=lambda: {"level": "INFO"})

    @classmethod
    def load(cls, config_path: str = "config.yaml") -> "Config":
        """从 YAML 文件加载配置"""
        path = Path(config_path)

        if not path.exists():
            # 尝试加载示例配置
            example_path = Path("config.example.yaml")
            if example_path.exists():
                print(f"警告：{config_path} 不存在，请复制 config.example.yaml 并修改配置")
            return cls()

        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        # 环境变量替换
        data = cls._replace_env_vars(data)

        config = cls(**data)
        # Fail-fast 验证
        config.validate()
        return config

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
        # 检查认证已启用时 JWT secret 是否为默认值
        if self.security.auth_enabled:
            if self.security.jwt_secret == "your-secret-key-change-in-production":
                print(
                    "[CONFIG ERROR] auth_enabled=true 但 jwt_secret 仍为默认值！",
                    file=sys.stderr
                )
                print("请在 config.yaml 中设置 security.jwt_secret 为强密码", file=sys.stderr)
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
