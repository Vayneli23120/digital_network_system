"""
应用配置管理
"""

import os
import yaml
from pathlib import Path
from typing import Optional, List
from pydantic import BaseModel, Field


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


class AlertsConfig(BaseModel):
    enabled: bool = False
    email: AlertEmailConfig = Field(default_factory=AlertEmailConfig)


class StorageConfig(BaseModel):
    backup_dir: str = "./backups"
    photo_dir: str = "./assets/devices"
    log_dir: str = "./logs"
    max_backups_per_device: int = 30
    backup_retention_days: int = 365


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


class SecurityConfig(BaseModel):
    auth_enabled: bool = False  # 认证功能开关，默认关闭
    jwt_secret: str = "your-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7


class AppConfig(BaseModel):
    name: str = "Network Automation System"
    version: str = "1.0.0"
    debug: bool = False


class Config(BaseModel):
    app: AppConfig = Field(default_factory=AppConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    console: ConsoleConfig = Field(default_factory=ConsoleConfig)
    alerts: AlertsConfig = Field(default_factory=AlertsConfig)
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

        return cls(**data)

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


# 全局配置实例
_config: Optional[Config] = None


def get_config() -> Config:
    """获取全局配置实例"""
    global _config
    if _config is None:
        _config = Config.load()
    return _config


def reload_config() -> Config:
    """重新加载配置"""
    global _config
    _config = Config.load()
    return _config
