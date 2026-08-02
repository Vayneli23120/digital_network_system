"""
系统设置 API

使用 SystemConfig 表存储全局配置项（key-value），用于系统级别设置如时区。
"""

from urllib.parse import urlsplit
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy.orm import Session
from typing import Dict, List, Optional

from app.features.auth.identity import Principal, get_current_principal
from app.shared.database import get_db
from app.shared.dependencies import require_permission
from app.shared.models import SystemConfig

router = APIRouter(prefix="/api/system", tags=["system-settings"])
require_system_config_read = require_permission("system_config:read")
require_system_config_write = require_permission("system_config:write")

# ═══════════════════════════════════════════════
# Pydantic 模型
# ═══════════════════════════════════════════════

class ConfigItem(BaseModel):
    """单个配置项"""
    key: str
    value: str
    description: Optional[str] = None


class ConfigUpdateRequest(BaseModel):
    """原子更新允许公开维护的系统配置。"""
    model_config = ConfigDict(extra="forbid")

    timezone: Optional[str] = Field(default=None, min_length=1, max_length=64)
    grafana_url: Optional[str] = Field(default=None, max_length=500)

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as exc:
            raise ValueError("无效的时区") from exc
        return value

    @field_validator("grafana_url")
    @classmethod
    def validate_grafana_url(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        normalized = value.strip().rstrip("/")
        if not normalized:
            return ""
        parsed = urlsplit(normalized)
        if (
            parsed.scheme not in ("http", "https")
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.fragment
        ):
            raise ValueError("Grafana 地址必须是无凭据的 HTTP(S) URL")
        return normalized

    @model_validator(mode="after")
    def require_update(self):
        if not self.model_fields_set:
            raise ValueError("至少提供一个配置项")
        if any(getattr(self, field) is None for field in self.model_fields_set):
            raise ValueError("配置值不能为 null")
        return self


class ConfigListResponse(BaseModel):
    """配置列表响应"""
    items: List[ConfigItem]


# 系统预定义的配置项（描述/默认值）
DEFAULT_CONFIGS: Dict[str, dict] = {
    "timezone": {
        "default": "Asia/Shanghai",
        "description": "系统时区，如 Asia/Shanghai, UTC, America/New_York",
    },
    "grafana_url": {
        "default": "",
        "description": "Grafana 基础地址（如 http://192.168.4.37:3001），用于设备详情页嵌入指标图表；为空则不显示",
    },
}


def _get_config_dict(db: Session) -> Dict[str, str]:
    """读取全部系统配置为字典（DB 中的值优先，缺失则返回默认值）。"""
    rows = db.query(SystemConfig).filter(
        SystemConfig.key.in_(DEFAULT_CONFIGS)
    ).all()
    stored = {r.key: r.value for r in rows}

    result = {}
    for key, meta in DEFAULT_CONFIGS.items():
        result[key] = stored.get(key, meta["default"])
    return result


# ═══════════════════════════════════════════════
# API 端点
# ═══════════════════════════════════════════════

@router.get("/config", response_model=ConfigListResponse)
def list_config(
    db: Session = Depends(get_db),
    _: None = Depends(require_system_config_read),
):
    """获取全部系统配置。"""
    configs = _get_config_dict(db)
    items = []
    for key, val in configs.items():
        meta = DEFAULT_CONFIGS.get(key, {})
        items.append(ConfigItem(
            key=key,
            value=val,
            description=meta.get("description"),
        ))
    return ConfigListResponse(items=items)


@router.put("/config", response_model=ConfigListResponse)
def update_config(
    body: ConfigUpdateRequest,
    db: Session = Depends(get_db),
    _: None = Depends(require_system_config_write),
    principal: Principal = Depends(get_current_principal),
):
    """在一个事务中更新允许公开维护的配置项。"""
    updates = body.model_dump(exclude_unset=True)
    rows = {
        row.key: row
        for row in db.query(SystemConfig).filter(
            SystemConfig.key.in_(updates)
        ).all()
    }
    for key, value in updates.items():
        row = rows.get(key)
        if row is None:
            row = SystemConfig(key=key, value=value)
            db.add(row)
            rows[key] = row
        else:
            row.value = value
        row.updated_by = principal.username
    db.commit()
    return list_config(db=db, _=None)
