"""自动化工作流 API 路由

提供工作流管理接口：
- 规则管理（创建、查询、更新、删除）
- 手动触发工作流
- 执行历史查询
- 统计数据
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime

from app.shared.database import get_db
from app.shared.models import WorkflowRule
from app.services.workflow import WorkflowExecutor, RuleEngine

router = APIRouter(prefix="/api/workflows", tags=["workflow"])


# ===== Request Models =====

class CreateRuleRequest(BaseModel):
    """创建规则请求"""
    name: str
    description: Optional[str] = None
    trigger_type: str
    trigger_conditions: Dict[str, Any]
    action_type: str
    action_config: Dict[str, Any]
    priority: int = 100
    is_active: bool = True


class UpdateRuleRequest(BaseModel):
    """更新规则请求"""
    name: Optional[str] = None
    description: Optional[str] = None
    trigger_type: Optional[str] = None
    trigger_conditions: Optional[Dict[str, Any]] = None
    action_type: Optional[str] = None
    action_config: Optional[Dict[str, Any]] = None
    priority: Optional[int] = None
    is_active: Optional[bool] = None


class TriggerRequest(BaseModel):
    """手动触发请求"""
    trigger_type: str
    event_data: Dict[str, Any]


class TriggerFaultRequest(BaseModel):
    """触发故障创建请求"""
    fault_id: int


class TriggerHealthRequest(BaseModel):
    """触发健康检查请求"""
    device_id: int


class TriggerMaintenanceRequest(BaseModel):
    """触发维修完成请求"""
    maintenance_id: int


# ===== Rule Management =====

@router.get("/rules")
async def list_rules(
    trigger_type: Optional[str] = None,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    """
    列出工作流规则

    Args:
        trigger_type: 按触发类型筛选
        is_active: 按活跃状态筛选
    """
    engine = RuleEngine(db)
    rules = engine.list_rules(trigger_type, is_active)

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
        "total": len(result),
        "rules": result
    }


@router.post("/rules")
async def create_rule(request: CreateRuleRequest, db: Session = Depends(get_db)):
    """
    创建工作流规则

    Args:
        request: 规则创建参数
    """
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
async def get_rule(rule_id: int, db: Session = Depends(get_db)):
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
    db: Session = Depends(get_db)
):
    """更新规则"""
    engine = RuleEngine(db)

    updates = {}
    for key, value in request.dict(exclude_none=True).items():
        updates[key] = value

    rule = engine.update_rule(rule_id, updates)

    if not rule:
        raise HTTPException(status_code=404, detail="规则不存在")

    return {
        "success": True,
        "rule_id": rule.id,
        "name": rule.name
    }


@router.delete("/rules/{rule_id}")
async def delete_rule(rule_id: int, db: Session = Depends(get_db)):
    """删除规则"""
    engine = RuleEngine(db)

    success = engine.delete_rule(rule_id)

    if not success:
        raise HTTPException(status_code=404, detail="规则不存在")

    return {"success": True, "deleted_rule_id": rule_id}


@router.patch("/rules/{rule_id}/toggle")
async def toggle_rule(rule_id: int, db: Session = Depends(get_db)):
    """启用/禁用规则"""
    rule = db.query(WorkflowRule).filter(WorkflowRule.id == rule_id).first()

    if not rule:
        raise HTTPException(status_code=404, detail="规则不存在")

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
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    手动触发工作流

    Args:
        request: 触发请求参数
    """
    executor = WorkflowExecutor(db)

    result = await executor.execute(
        trigger_type=request.trigger_type,
        event_data=request.event_data
    )

    return result.to_dict()


@router.post("/trigger/fault")
async def trigger_fault_workflow(
    request: TriggerFaultRequest,
    db: Session = Depends(get_db)
):
    """
    触发故障创建工作流

    Args:
        request: 包含 fault_id
    """
    executor = WorkflowExecutor(db)

    result = await executor.trigger_fault_created(request.fault_id)

    return result.to_dict()


@router.post("/trigger/health")
async def trigger_health_workflow(
    request: TriggerHealthRequest,
    db: Session = Depends(get_db)
):
    """
    触发健康检查工作流

    Args:
        request: 包含 device_id
    """
    executor = WorkflowExecutor(db)

    result = await executor.trigger_health_check(request.device_id)

    return result.to_dict()


@router.post("/trigger/maintenance")
async def trigger_maintenance_workflow(
    request: TriggerMaintenanceRequest,
    db: Session = Depends(get_db)
):
    """
    触发维修完成工作流

    Args:
        request: 包含 maintenance_id
    """
    executor = WorkflowExecutor(db)

    result = await executor.trigger_maintenance_completed(request.maintenance_id)

    return result.to_dict()


# ===== Defaults & Stats =====

@router.post("/init-defaults")
async def init_default_rules(db: Session = Depends(get_db)):
    """
    初始化默认工作流规则

    创建以下默认规则：
    - 健康评分低自动创建巡检
    - 严重故障自动创建维修单
    - 维修完成更新健康评分
    - 高风险设备告警
    """
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
async def get_workflow_stats(db: Session = Depends(get_db)):
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
async def list_triggers():
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
async def list_actions():
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


# Need json import
import json