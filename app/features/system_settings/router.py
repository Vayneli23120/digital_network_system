"""
系统设置 API

使用 SystemConfig 表存储全局配置项（key-value），用于系统级别设置如时区。
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Dict, List, Optional

from app.shared.database import get_db
from app.shared.models import SystemConfig

router = APIRouter(prefix="/api/system", tags=["system-settings"])

# ═══════════════════════════════════════════════
# Pydantic 模型
# ═══════════════════════════════════════════════

class ConfigItem(BaseModel):
    """单个配置项"""
    key: str
    value: str
    description: Optional[str] = None


class ConfigUpdateRequest(BaseModel):
    """更新配置请求"""
    key: str
    value: str


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
    rows = db.query(SystemConfig).all()
    stored = {r.key: r.value for r in rows}

    result = {}
    for key, meta in DEFAULT_CONFIGS.items():
        result[key] = stored.get(key, meta["default"])
    # 也返回未预定义但已存储的配置
    for key, val in stored.items():
        if key not in result:
            result[key] = val
    return result


# ═══════════════════════════════════════════════
# API 端点
# ═══════════════════════════════════════════════

@router.get("/config", response_model=ConfigListResponse)
def list_config(db: Session = Depends(get_db)):
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


@router.put("/config", response_model=ConfigItem)
def update_config(body: ConfigUpdateRequest, db: Session = Depends(get_db)):
    """更新系统配置项。"""
    row = db.query(SystemConfig).filter(SystemConfig.key == body.key).first()
    if row:
        row.value = body.value
    else:
        row = SystemConfig(key=body.key, value=body.value)
        db.add(row)
    db.commit()
    db.refresh(row)
    meta = DEFAULT_CONFIGS.get(body.key, {})
    return ConfigItem(
        key=row.key,
        value=row.value,
        description=meta.get("description"),
    )
