"""自动化工作流 API 路由

提供工作流管理接口：
- 规则管理（创建、查询、更新、删除）
- 手动触发工作流
- 执行历史查询
- 统计数据
"""

import json
from typing import Any, Dict, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, JsonValue, field_validator, model_validator
from sqlalchemy.orm import Session

from app.features.auth.identity import Principal, get_current_principal
from app.shared.database import get_db
from app.shared.dependencies import get_user_all_permissions, require_permission
from app.shared.models import WorkflowRule
from app.services.workflow import (
    ACTION_REQUIRED_PERMISSIONS,
    RuleEngine,
    WorkflowExecutor,
    WorkflowPermissionError,
)

router = APIRouter(prefix="/api/workflows", tags=["workflow"])
require_workflow_read = require_permission("workflow:read")
require_workflow_write = require_permission("workflow:write")
require_workflow_delete = require_permission("workflow:delete")
require_workflow_trigger = require_permission("workflow:trigger")

TriggerType = Literal[
    "fault_created",
    "device_health_low",
    "maintenance_completed",
    "scheduled_check",
]
ActionType = Literal[
    "create_maintenance",
    "create_pm_task",
    "send_alert",
    "update_health_score",
    "log_event",
]
MAX_WORKFLOW_JSON_BYTES = 100_000
MAX_WORKFLOW_CONDITION_DEPTH = 10
MAX_WORKFLOW_CONDITION_NODES = 1_000
COMPARISON_OPERATORS = {
    "<", "<=", ">", ">=", "=", "!=", "in", "not_in", "contains",
    "not_contains",
}
LOGICAL_OPERATORS = {"and", "or", "not"}


def _validate_json_mapping(value: Dict[str, JsonValue], field_name: str) -> Dict[str, JsonValue]:
    serialized = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    if len(serialized.encode("utf-8")) > MAX_WORKFLOW_JSON_BYTES:
        raise ValueError(f"{field_name} 超过大小限制")
    return value


def _validate_conditions(
    conditions: Dict[str, JsonValue],
    depth: int = 0,
    counter: Optional[list[int]] = None,
) -> None:
    if depth > MAX_WORKFLOW_CONDITION_DEPTH:
        raise ValueError("触发条件嵌套过深")
    if counter is None:
        counter = [0]
    counter[0] += 1
    if counter[0] > MAX_WORKFLOW_CONDITION_NODES:
        raise ValueError("触发条件节点过多")

    for field, comparison in conditions.items():
        if len(field) > 100:
            raise ValueError("触发条件字段名过长")
        if field in ("and", "or"):
            if not isinstance(comparison, list) or not comparison:
                raise ValueError(f"{field} 条件必须是非空数组")
            for operand in comparison:
                if not isinstance(operand, dict):
                    raise ValueError(f"{field} 条件项必须是对象")
                _validate_conditions(operand, depth + 1, counter)
        elif field == "not":
            if not isinstance(comparison, dict):
                raise ValueError("not 条件必须是对象")
            _validate_conditions(comparison, depth + 1, counter)
        elif isinstance(comparison, dict):
            if not comparison or not set(comparison).issubset(COMPARISON_OPERATORS):
                raise ValueError("触发条件包含不支持的比较操作符")


def _validate_action_config(action_type: str, config: Dict[str, JsonValue]) -> None:
    allowed_fields = {
        "create_maintenance": {
            "maint_type", "priority", "title_template", "description",
        },
        "create_pm_task": {
            "task_type", "days_offset", "name_template", "reason",
        },
        "send_alert": {"level", "title", "message_template"},
        "update_health_score": {"adjustment", "reason"},
        "log_event": {"event_type", "message"},
    }
    unexpected = set(config) - allowed_fields[action_type]
    if unexpected:
        raise ValueError(f"动作配置包含不支持字段: {', '.join(sorted(unexpected))}")

    string_fields = {
        "create_maintenance": {
            "maint_type", "priority", "title_template", "description",
        },
        "create_pm_task": {"task_type", "name_template", "reason"},
        "send_alert": {"level", "title", "message_template"},
        "update_health_score": {"reason"},
        "log_event": {"event_type", "message"},
    }
    for field in string_fields[action_type].intersection(config):
        if not isinstance(config[field], str):
            raise ValueError(f"动作配置字段 {field} 必须是字符串")

    if action_type == "create_pm_task":
        days_offset = config.get("days_offset", 7)
        if not isinstance(days_offset, int) or isinstance(days_offset, bool) or not 0 <= days_offset <= 3650:
            raise ValueError("days_offset 必须是 0 到 3650 的整数")
    elif action_type == "create_maintenance":
        maint_type = config.get("maint_type", "corrective")
        if maint_type not in {"preventive", "corrective", "upgrade", "emergency"}:
            raise ValueError("maint_type 无效")
        priority = config.get("priority", "normal")
        if priority not in {
            "P1", "P2", "P3", "P4", "urgent", "high", "normal", "low",
        }:
            raise ValueError("priority 无效")
        title_template = config.get("title_template", "")
        if not isinstance(title_template, str) or len(title_template) > 100:
            raise ValueError("title_template 长度不能超过 100")
    elif action_type == "update_health_score":
        adjustment = config.get("adjustment", 0)
        if not isinstance(adjustment, (int, float)) or isinstance(adjustment, bool):
            raise ValueError("adjustment 必须是数字")
        if not -100 <= adjustment <= 100:
            raise ValueError("adjustment 必须在 -100 到 100 之间")

    for key, value in config.items():
        if isinstance(value, str) and len(value) > 10_000:
            raise ValueError(f"动作配置字段 {key} 超过长度限制")


class WorkflowRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")


def _action_authorizer(principal: Principal, db: Session):
    if principal.user is None:
        return lambda _action_type: True
    permissions = set(get_user_all_permissions(principal.user.id, db))

    def authorize(action_type: str) -> bool:
        required = ACTION_REQUIRED_PERMISSIONS.get(action_type)
        return required is None or "admin:all" in permissions or required in permissions

    return authorize


def _target_permission_error(exc: WorkflowPermissionError) -> HTTPException:
    return HTTPException(
        status_code=403,
        detail=(
            "工作流动作需要目标域权限: "
            + ", ".join(exc.missing_permissions)
        ),
    )


def _require_action_permission(
    principal: Principal,
    db: Session,
    action_type: str,
) -> None:
    required = ACTION_REQUIRED_PERMISSIONS.get(action_type)
    if required and not _action_authorizer(principal, db)(action_type):
        raise _target_permission_error(WorkflowPermissionError([required]))


# ===== Request Models =====

class CreateRuleRequest(WorkflowRequest):
    """创建规则请求"""
    name: str = Field(min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    trigger_type: TriggerType
    trigger_conditions: Dict[str, JsonValue] = Field(default_factory=dict)
    action_type: ActionType
    action_config: Dict[str, JsonValue] = Field(default_factory=dict)
    priority: int = Field(default=100, ge=0, le=10_000)
    is_active: bool = True

    @field_validator("trigger_conditions")
    @classmethod
    def validate_conditions(cls, value: Dict[str, JsonValue]) -> Dict[str, JsonValue]:
        _validate_json_mapping(value, "触发条件")
        _validate_conditions(value)
        return value

    @field_validator("action_config")
    @classmethod
    def validate_config_size(cls, value: Dict[str, JsonValue]) -> Dict[str, JsonValue]:
        return _validate_json_mapping(value, "动作配置")

    @model_validator(mode="after")
    def validate_action(self):
        _validate_action_config(self.action_type, self.action_config)
        return self


class UpdateRuleRequest(WorkflowRequest):
    """更新规则请求"""
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    trigger_type: Optional[TriggerType] = None
    trigger_conditions: Optional[Dict[str, JsonValue]] = None
    action_type: Optional[ActionType] = None
    action_config: Optional[Dict[str, JsonValue]] = None
    priority: Optional[int] = Field(default=None, ge=0, le=10_000)
    is_active: Optional[bool] = None

    @field_validator("trigger_conditions")
    @classmethod
    def validate_conditions(
        cls,
        value: Optional[Dict[str, JsonValue]],
    ) -> Optional[Dict[str, JsonValue]]:
        if value is not None:
            _validate_json_mapping(value, "触发条件")
            _validate_conditions(value)
        return value

    @field_validator("action_config")
    @classmethod
    def validate_config_size(
        cls,
        value: Optional[Dict[str, JsonValue]],
    ) -> Optional[Dict[str, JsonValue]]:
        return _validate_json_mapping(value, "动作配置") if value is not None else value


class TriggerRequest(WorkflowRequest):
    """手动触发请求"""
    trigger_type: TriggerType
    event_data: Dict[str, JsonValue]

    @field_validator("event_data")
    @classmethod
    def validate_event_size(cls, value: Dict[str, JsonValue]) -> Dict[str, JsonValue]:
        return _validate_json_mapping(value, "事件数据")

    @model_validator(mode="after")
    def validate_event_shape(self):
        expected = {
            "fault_created": {"fault_id"},
            "device_health_low": {"device_id"},
            "maintenance_completed": {"maintenance_id"},
            "scheduled_check": {"check_type"},
        }
        if set(self.event_data) != expected[self.trigger_type]:
            raise ValueError("事件数据与触发类型不匹配")
        key = next(iter(expected[self.trigger_type]))
        value = self.event_data[key]
        if key.endswith("_id") and (
            not isinstance(value, int) or isinstance(value, bool) or value <= 0
        ):
            raise ValueError(f"{key} 必须是正整数")
        if key == "check_type" and (
            not isinstance(value, str) or not 1 <= len(value) <= 50
        ):
            raise ValueError("check_type 长度必须为 1 到 50")
        return self


class TriggerFaultRequest(WorkflowRequest):
    """触发故障创建请求"""
    fault_id: int = Field(gt=0)


class TriggerHealthRequest(WorkflowRequest):
    """触发健康检查请求"""
    device_id: int = Field(gt=0)


class TriggerMaintenanceRequest(WorkflowRequest):
    """触发维修完成请求"""
    maintenance_id: int = Field(gt=0)


# ===== Rule Management =====

@router.get("/rules")
async def list_rules(
    trigger_type: Optional[TriggerType] = None,
    is_active: Optional[bool] = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    _: None = Depends(require_workflow_read),
):
    """
    列出工作流规则

    Args:
        trigger_type: 按触发类型筛选
        is_active: 按活跃状态筛选
    """
    engine = RuleEngine(db)
    total = engine.count_rules(trigger_type, is_active)
    rules = engine.list_rules(trigger_type, is_active, skip=skip, limit=limit)

    result = []
    for rule in rules:
        result.append({
            "id": rule.id,
            "name": rule.name,
            "description": rule.description,
            "trigger_type": rule.trigger_type,
            "trigger_conditions": rule.get_trigger_conditions_dict() if hasattr(rule, 'get_trigger_conditions_dict') else {},
            "action_type": rule.action_type,
            "action_config": rule.get_action_config_dict() if hasattr(rule, 'get_action_config_dict') else {},
            "is_active": rule.is_active,
            "priority": rule.priority,
            "execution_count": rule.execution_count,
            "last_triggered_at": rule.last_triggered_at.isoformat() if rule.last_triggered_at else None,
            "created_at": rule.created_at.isoformat() if rule.created_at else None
        })

    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "rules": result
    }


@router.post("/rules")
async def create_rule(
    request: CreateRuleRequest,
    db: Session = Depends(get_db),
    _: None = Depends(require_workflow_write),
    principal: Principal = Depends(get_current_principal),
):
    """
    创建工作流规则

    Args:
        request: 规则创建参数
    """
    _require_action_permission(principal, db, request.action_type)
    engine = RuleEngine(db)

    rule = engine.create_rule(
        name=request.name,
        trigger_type=request.trigger_type,
        trigger_conditions=request.trigger_conditions,
        action_type=request.action_type,
        action_config=request.action_config,
        description=request.description,
        priority=request.priority,
        is_active=request.is_active
    )

    return {
        "success": True,
        "rule_id": rule.id,
        "name": rule.name,
        "trigger_type": rule.trigger_type,
        "action_type": rule.action_type
    }


@router.get("/rules/{rule_id}")
async def get_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_workflow_read),
):
    """获取单个规则详情"""
    rule = db.query(WorkflowRule).filter(WorkflowRule.id == rule_id).first()

    if not rule:
        raise HTTPException(status_code=404, detail="规则不存在")

    return {
        "id": rule.id,
        "name": rule.name,
        "description": rule.description,
        "trigger_type": rule.trigger_type,
        "trigger_conditions": json.loads(rule.trigger_conditions) if rule.trigger_conditions else {},
        "action_type": rule.action_type,
        "action_config": json.loads(rule.action_config) if rule.action_config else {},
        "is_active": rule.is_active,
        "priority": rule.priority,
        "execution_count": rule.execution_count,
        "last_triggered_at": rule.last_triggered_at.isoformat() if rule.last_triggered_at else None,
        "created_at": rule.created_at.isoformat() if rule.created_at else None
    }


@router.put("/rules/{rule_id}")
async def update_rule(
    rule_id: int,
    request: UpdateRuleRequest,
    db: Session = Depends(get_db),
    _: None = Depends(require_workflow_write),
    principal: Principal = Depends(get_current_principal),
):
    """更新规则"""
    engine = RuleEngine(db)

    existing = engine.get_rule(rule_id)
    if not existing:
        raise HTTPException(status_code=404, detail="规则不存在")

    updates = request.model_dump(exclude_none=True)
    action_type = updates.get("action_type", existing.action_type)
    _require_action_permission(principal, db, action_type)
    if "action_type" in updates and "action_config" not in updates:
        raise HTTPException(
            status_code=422,
            detail="修改动作类型时必须同时提供动作配置",
        )
    if "action_config" in updates:
        _validate_action_config(action_type, updates["action_config"])

    rule = engine.update_rule(rule_id, updates)

    if not rule:
        raise HTTPException(status_code=404, detail="规则不存在")

    return {
        "success": True,
        "rule_id": rule.id,
        "name": rule.name
    }


@router.delete("/rules/{rule_id}")
async def delete_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_workflow_delete),
):
    """删除规则"""
    engine = RuleEngine(db)

    success = engine.delete_rule(rule_id)

    if not success:
        raise HTTPException(status_code=404, detail="规则不存在")

    return {"success": True, "deleted_rule_id": rule_id}


@router.patch("/rules/{rule_id}/toggle")
async def toggle_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_workflow_write),
    principal: Principal = Depends(get_current_principal),
):
    """启用/禁用规则"""
    rule = db.query(WorkflowRule).filter(WorkflowRule.id == rule_id).first()

    if not rule:
        raise HTTPException(status_code=404, detail="规则不存在")

    _require_action_permission(principal, db, rule.action_type)

    rule.is_active = not rule.is_active
    db.commit()

    return {
        "success": True,
        "rule_id": rule.id,
        "is_active": rule.is_active
    }


# ===== Trigger Execution =====

@router.post("/trigger")
async def trigger_workflow(
    request: TriggerRequest,
    db: Session = Depends(get_db),
    _: None = Depends(require_workflow_trigger),
    principal: Principal = Depends(get_current_principal),
):
    """
    手动触发工作流

    Args:
        request: 触发请求参数
    """
    executor = WorkflowExecutor(db)

    try:
        result = await executor.execute(
            trigger_type=request.trigger_type,
            event_data=request.event_data,
            actor=principal.username,
            action_authorizer=_action_authorizer(principal, db),
        )
    except WorkflowPermissionError as exc:
        raise _target_permission_error(exc) from exc

    return result.to_dict()


@router.post("/trigger/fault")
async def trigger_fault_workflow(
    request: TriggerFaultRequest,
    db: Session = Depends(get_db),
    _: None = Depends(require_workflow_trigger),
    principal: Principal = Depends(get_current_principal),
):
    """
    触发故障创建工作流

    Args:
        request: 包含 fault_id
    """
    executor = WorkflowExecutor(db)

    try:
        result = await executor.trigger_fault_created(
            request.fault_id,
            actor=principal.username,
            action_authorizer=_action_authorizer(principal, db),
        )
    except WorkflowPermissionError as exc:
        raise _target_permission_error(exc) from exc

    return result.to_dict()


@router.post("/trigger/health")
async def trigger_health_workflow(
    request: TriggerHealthRequest,
    db: Session = Depends(get_db),
    _: None = Depends(require_workflow_trigger),
    principal: Principal = Depends(get_current_principal),
):
    """
    触发健康检查工作流

    Args:
        request: 包含 device_id
    """
    executor = WorkflowExecutor(db)

    try:
        result = await executor.trigger_health_check(
            request.device_id,
            actor=principal.username,
            action_authorizer=_action_authorizer(principal, db),
        )
    except WorkflowPermissionError as exc:
        raise _target_permission_error(exc) from exc

    return result.to_dict()


@router.post("/trigger/maintenance")
async def trigger_maintenance_workflow(
    request: TriggerMaintenanceRequest,
    db: Session = Depends(get_db),
    _: None = Depends(require_workflow_trigger),
    principal: Principal = Depends(get_current_principal),
):
    """
    触发维修完成工作流

    Args:
        request: 包含 maintenance_id
    """
    executor = WorkflowExecutor(db)

    try:
        result = await executor.trigger_maintenance_completed(
            request.maintenance_id,
            actor=principal.username,
            action_authorizer=_action_authorizer(principal, db),
        )
    except WorkflowPermissionError as exc:
        raise _target_permission_error(exc) from exc

    return result.to_dict()


# ===== Defaults & Stats =====

@router.post("/init-defaults")
async def init_default_rules(
    db: Session = Depends(get_db),
    _: None = Depends(require_workflow_write),
    principal: Principal = Depends(get_current_principal),
):
    """
    初始化默认工作流规则

    创建以下默认规则：
    - 健康评分低自动创建巡检
    - 严重故障自动创建维修单
    - 维修完成更新健康评分
    - 高风险设备告警
    """
    for action_type in ACTION_REQUIRED_PERMISSIONS:
        _require_action_permission(principal, db, action_type)
    executor = WorkflowExecutor(db)

    created_rules = executor.create_default_rules()

    return {
        "success": True,
        "created_count": len(created_rules),
        "created_rules": [
            {"id": r.id, "name": r.name, "trigger_type": r.trigger_type}
            for r in created_rules
        ]
    }


@router.get("/stats")
async def get_workflow_stats(
    db: Session = Depends(get_db),
    _: None = Depends(require_workflow_read),
):
    """
    获取工作流统计

    Returns:
        - 规则统计
        - 可用触发类型
        - 可用动作类型
    """
    executor = WorkflowExecutor(db)

    return executor.get_stats()


@router.get("/triggers")
async def list_triggers(_: None = Depends(require_workflow_read)):
    """列出可用的触发类型"""
    from app.services.workflow.triggers import TriggerManager

    return {
        "triggers": list(TriggerManager.TRIGGER_CLASSES.keys()),
        "trigger_info": {
            "fault_created": "故障创建时触发",
            "device_health_low": "设备健康评分低于阈值时触发",
            "maintenance_completed": "维修完成时触发",
            "scheduled_check": "定时检查触发"
        }
    }


@router.get("/actions")
async def list_actions(_: None = Depends(require_workflow_read)):
    """列出可用的动作类型"""
    from app.services.workflow.actions import ActionManager

    actions = list(ActionManager.ACTION_CLASSES.keys())

    return {
        "actions": actions,
        "action_info": {
            "create_maintenance": "创建维修单",
            "create_pm_task": "创建计划性维护任务",
            "send_alert": "发送告警通知",
            "update_health_score": "更新设备健康评分",
            "log_event": "记录事件日志"
        }
    }
