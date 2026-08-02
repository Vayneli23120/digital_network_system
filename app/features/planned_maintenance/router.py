"""Planned maintenance router - 计划性运维管理（AI增强版）

新增功能：
- AI推荐巡检任务生成（使用 ADK Agent）
- 健康评分驱动的自动PM任务
- 与工作流引擎集成
- 预测性维护建议
"""

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from loguru import logger
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Any, List, Literal, Optional
from datetime import datetime, timedelta
from decimal import Decimal
import uuid
import json

from pydantic import BaseModel, ConfigDict, Field, condecimal, field_validator

from app.features.auth.identity import Principal, get_current_principal
from app.shared.database import get_db
from app.shared.dependencies import require_permission
from app.shared.models import (
    AopMaintenanceWindow,
    AopProject,
    MaintenancePlan,
    MaintenanceTask,
    MaintenanceRecord,
    Device,
)
from app.features.spare_movements.schemas import SpareMovementInput
from app.features.spare_movements.router import require_movement_write_for_side_effect
from app.features.spare_parts.spare_part_service import (
    create_movements as svc_create_movements,
)

# ADK 导入（预测性维护功能）
from app.services.adk.runner import adk_runner
from app.services.adk.agents import predictive_agent
from app.features.planned_maintenance.aop_router import router as aop_router

router = APIRouter(prefix="/api/planned-maintenance", tags=["planned-maintenance"])
router.include_router(aop_router)
require_planned_read = require_permission("planned_task:read")
require_planned_write = require_permission("planned_task:write")
require_planned_delete = require_permission("planned_task:delete")
require_planned_execute = require_permission("planned_task:execute")
PLANNED_INTERNAL_ERROR = "计划性运维操作失败，请查看服务端日志"
PlanType = Literal["routine_check", "parts_replace", "vendor_service"]
PlanStatus = Literal["active", "paused", "completed"]
CompletionResult = Literal["success", "partial", "rolled_back"]
Money = condecimal(ge=0, max_digits=10, decimal_places=2)
LaborHours = condecimal(ge=0, max_digits=5, decimal_places=2)


def _actor_username(principal: Any) -> str:
    return principal.username if isinstance(principal, Principal) else "system"


def _internal_error(operation: str) -> HTTPException:
    logger.exception("Planned maintenance operation failed: {}", operation)
    return HTTPException(status_code=500, detail=PLANNED_INTERNAL_ERROR)


# ============ Pydantic 模型 ============

class PlanCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=100)
    device_id: Optional[int] = Field(default=None, gt=0)
    device_name: Optional[str] = Field(default=None, max_length=100)
    plan_type: PlanType
    cycle_days: int = Field(default=30, ge=1, le=3650)
    next_date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    data_basis: Optional[str] = Field(default=None, max_length=100_000)
    auto_generate: bool = True

    @field_validator("next_date")
    @classmethod
    def validate_next_date(cls, value: str) -> str:
        datetime.strptime(value, "%Y-%m-%d")
        return value


class PlanUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    cycle_days: Optional[int] = Field(default=None, ge=1, le=3650)
    next_date: Optional[str] = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    data_basis: Optional[str] = Field(default=None, max_length=100_000)
    auto_generate: Optional[bool] = None
    status: Optional[PlanStatus] = None

    @field_validator("next_date")
    @classmethod
    def validate_next_date(cls, value: Optional[str]) -> Optional[str]:
        if value is not None:
            datetime.strptime(value, "%Y-%m-%d")
        return value


class TaskCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plan_id: Optional[int] = Field(default=None, gt=0)
    device_id: Optional[int] = Field(default=None, gt=0)
    device_name: Optional[str] = Field(default=None, max_length=100)
    scheduled_date: datetime
    notes: Optional[str] = Field(default=None, max_length=100_000)
    ai_generated: bool = False


class GenerateAIRequest(BaseModel):
    """AI推荐任务生成请求"""
    model_config = ConfigDict(extra="forbid")

    min_health_score: int = Field(default=60, ge=0, le=100)
    risk_levels: List[Literal["low", "medium", "high", "critical"]] = Field(
        default_factory=lambda: ["high", "critical"],
        min_length=1,
        max_length=4,
    )
    days_offset: int = Field(default=3, ge=0, le=3650)
    max_devices: int = Field(default=500, ge=1, le=1000)


class TaskCompleteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    description: Optional[str] = Field(default=None, max_length=100_000)
    parts_replaced: Optional[str] = Field(default=None, max_length=1_000_000)
    parts_cost: Money = Decimal("0")
    labor_hours: LaborHours = Decimal("0")
    labor_cost: Money = Decimal("0")
    completion_result: CompletionResult = "success"
    completion_notes: Optional[str] = Field(default=None, max_length=100_000)
    spare_movements: Optional[List[SpareMovementInput]] = None


# ============ 维护计划 API ============

@router.get("/plans")
async def list_plans(
    status: Optional[str] = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    _: None = Depends(require_planned_read),
):
    """获取维护计划列表"""
    try:
        query = db.query(MaintenancePlan)

        if status:
            query = query.filter(MaintenancePlan.status == status)

        total = query.count()
        plans = query.order_by(MaintenancePlan.next_date).offset(skip).limit(limit).all()

        return {
            "total": total,
            "items": [
                {
                    "id": p.id,
                    "name": p.name,
                    "device_id": p.device_id,
                    "device_name": p.device_name,
                    "plan_type": p.plan_type,
                    "cycle_days": p.cycle_days,
                    "next_date": p.next_date.isoformat() if p.next_date else None,
                    "data_basis": p.data_basis,
                    "auto_generate": p.auto_generate,
                    "status": p.status,
                    "created_at": p.created_at.isoformat() if p.created_at else None
                }
                for p in plans
            ]
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise _internal_error("list plans") from exc


@router.post("/plans")
async def create_plan(
    plan_data: PlanCreate,
    db: Session = Depends(get_db),
    _: None = Depends(require_planned_write),
):
    """创建维护计划"""
    try:
        # 解析日期字符串，转换为 datetime
        next_date_dt = datetime.strptime(plan_data.next_date, "%Y-%m-%d")

        device_name = plan_data.device_name
        if plan_data.device_id:
            device = db.query(Device).filter(Device.id == plan_data.device_id).first()
            if not device:
                raise HTTPException(status_code=404, detail="设备不存在")
            device_name = device.name

        plan = MaintenancePlan(
            name=plan_data.name,
            device_id=plan_data.device_id,
            device_name=device_name,
            plan_type=plan_data.plan_type,
            cycle_days=plan_data.cycle_days,
            next_date=next_date_dt,
            data_basis=plan_data.data_basis,
            auto_generate=plan_data.auto_generate,
            status="active"
        )
        db.add(plan)
        db.commit()
        db.refresh(plan)

        return {"id": plan.id, "message": "维护计划创建成功"}
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise _internal_error("create plan") from exc


@router.get("/plans/{plan_id}")
async def get_plan(
    plan_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_planned_read),
):
    """获取维护计划详情"""
    plan = db.query(MaintenancePlan).filter(MaintenancePlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="维护计划不存在")

    # 获取关联的任务统计
    task_stats = db.query(
        MaintenanceTask.status,
        func.count(MaintenanceTask.id)
    ).filter(MaintenanceTask.plan_id == plan_id).group_by(MaintenanceTask.status).all()

    stats = {s: c for s, c in task_stats}

    return {
        "id": plan.id,
        "name": plan.name,
        "device_id": plan.device_id,
        "device_name": plan.device_name,
        "plan_type": plan.plan_type,
        "cycle_days": plan.cycle_days,
        "next_date": plan.next_date.isoformat() if plan.next_date else None,
        "data_basis": plan.data_basis,
        "auto_generate": plan.auto_generate,
        "status": plan.status,
        "task_stats": {
            "pending": stats.get("pending", 0),
            "in_progress": stats.get("in_progress", 0),
            "completed": stats.get("completed", 0),
            "skipped": stats.get("skipped", 0),
            "overdue": stats.get("overdue", 0)
        },
        "created_at": plan.created_at.isoformat() if plan.created_at else None,
        "updated_at": plan.updated_at.isoformat() if plan.updated_at else None
    }


@router.put("/plans/{plan_id}")
async def update_plan(
    plan_id: int,
    plan_data: PlanUpdate,
    db: Session = Depends(get_db),
    _: None = Depends(require_planned_write),
):
    """更新维护计划"""
    plan = db.query(MaintenancePlan).filter(MaintenancePlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="维护计划不存在")

    update_data = plan_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if hasattr(plan, key):
            if key == "next_date" and value:
                value = datetime.strptime(value, "%Y-%m-%d")
            setattr(plan, key, value)

    db.commit()
    db.refresh(plan)

    return {"id": plan.id, "message": "更新成功"}


@router.delete("/plans/{plan_id}")
async def delete_plan(
    plan_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_planned_delete),
):
    """删除维护计划"""
    plan = db.query(MaintenancePlan).filter(MaintenancePlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="维护计划不存在")

    db.delete(plan)
    db.commit()

    return {"message": "删除成功"}


# ============ 运维任务 API ============

@router.get("/tasks")
async def list_tasks(
    plan_id: Optional[int] = None,
    device_id: Optional[int] = None,
    status: Optional[str] = None,
    ai_generated: Optional[bool] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    _: None = Depends(require_planned_read),
):
    """获取运维任务列表"""
    query = db.query(MaintenanceTask)

    if plan_id:
        query = query.filter(MaintenanceTask.plan_id == plan_id)

    if device_id:
        query = query.filter(MaintenanceTask.device_id == device_id)

    if status:
        query = query.filter(MaintenanceTask.status == status)

    if ai_generated is not None:
        # 检查notes中是否包含ai_generated标记
        if ai_generated:
            query = query.filter(MaintenanceTask.notes.contains('ai_generated'))
        else:
            query = query.filter(~MaintenanceTask.notes.contains('ai_generated'))

    if start_date:
        query = query.filter(MaintenanceTask.scheduled_date >= start_date)

    if end_date:
        query = query.filter(MaintenanceTask.scheduled_date <= end_date)

    total = query.count()
    tasks = query.order_by(MaintenanceTask.scheduled_date).offset(skip).limit(limit).all()
    now = datetime.utcnow()

    items = []
    for t in tasks:
        # 解析notes获取AI生成信息
        ai_info = None
        if t.notes:
            try:
                notes_data = json.loads(t.notes)
                ai_info = notes_data.get('ai_generated', False)
            except:
                pass

        items.append({
            "id": t.id,
            "plan_id": t.plan_id,
            "aop_project_id": t.aop_project_id,
            "maintenance_window_id": t.maintenance_window_id,
            "device_id": t.device_id,
            "device_name": t.device_name,
            "task_no": t.task_no,
            "scheduled_date": t.scheduled_date.isoformat() if t.scheduled_date else None,
            "scheduled_end": t.scheduled_end.isoformat() if t.scheduled_end else None,
            "estimated_hours": float(t.estimated_hours) if t.estimated_hours is not None else None,
            "schedule_source": t.schedule_source,
            "actual_date": t.actual_date.isoformat() if t.actual_date else None,
            "status": "overdue" if t.status == "pending" and t.scheduled_date < now else t.status,
            "maintenance_id": t.maintenance_id,
            "ai_generated": ai_info,
            "notes": t.notes,
            "created_at": t.created_at.isoformat() if t.created_at else None
        })

    return {"total": total, "items": items}


@router.post("/tasks")
async def create_task(
    task_data: TaskCreate,
    db: Session = Depends(get_db),
    _: None = Depends(require_planned_write),
):
    """手动创建运维任务"""
    plan = None
    if task_data.plan_id:
        plan = db.query(MaintenancePlan).filter(
            MaintenancePlan.id == task_data.plan_id
        ).first()
        if not plan:
            raise HTTPException(status_code=404, detail="维护计划不存在")

    device_name = plan.device_name if plan else task_data.device_name
    device_id = plan.device_id if plan else task_data.device_id
    if task_data.device_id:
        device = db.query(Device).filter(Device.id == task_data.device_id).first()
        if not device:
            raise HTTPException(status_code=404, detail="设备不存在")
        device_id = device.id
        device_name = device.name

    # 自动生成任务编号
    task_no = f"TASK-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:4].upper()}"

    # 检查是否超期
    now = datetime.utcnow()
    status = "pending"
    if task_data.scheduled_date < now:
        status = "overdue"

    # 构建notes，包含AI生成标记
    notes_data = {"ai_generated": task_data.ai_generated}
    if task_data.notes:
        notes_data["user_notes"] = task_data.notes

    task = MaintenanceTask(
        plan_id=task_data.plan_id,
        device_id=device_id,
        device_name=device_name,
        task_no=task_no,
        scheduled_date=task_data.scheduled_date,
        status=status,
        notes=json.dumps(notes_data)
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    return {"id": task.id, "task_no": task_no, "message": "任务创建成功"}


@router.get("/tasks/{task_id}")
async def get_task(
    task_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_planned_read),
):
    """获取运维任务详情"""
    task = db.query(MaintenanceTask).filter(MaintenanceTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    # 获取关联的维修单信息
    maintenance_info = None
    if task.maintenance_id:
        maintenance = db.query(MaintenanceRecord).filter(
            MaintenanceRecord.id == task.maintenance_id
        ).first()
        if maintenance:
            maintenance_info = {
                "id": maintenance.id,
                "maint_no": maintenance.maint_no,
                "parts_cost": float(maintenance.parts_cost) if maintenance.parts_cost else 0,
                "labor_cost": float(maintenance.labor_cost) if maintenance.labor_cost else 0,
                "description": maintenance.description
            }

    # 获取关联的计划信息
    plan_info = None
    if task.plan_id:
        plan = db.query(MaintenancePlan).filter(MaintenancePlan.id == task.plan_id).first()
        if plan:
            plan_info = {
                "id": plan.id,
                "name": plan.name,
                "plan_type": plan.plan_type
            }

    aop_project_info = None
    if task.aop_project_id:
        project = db.query(AopProject).filter(AopProject.id == task.aop_project_id).first()
        if project:
            aop_project_info = {
                "id": project.id,
                "program_id": project.program_id,
                "project_code": project.project_code,
                "name": project.name,
                "project_type": project.project_type,
                "priority": project.priority,
                "risk_level": project.risk_level,
                "rollback_plan": project.rollback_plan,
            }

    maintenance_window_info = None
    if task.maintenance_window_id:
        window = db.query(AopMaintenanceWindow).filter(
            AopMaintenanceWindow.id == task.maintenance_window_id
        ).first()
        if window:
            maintenance_window_info = {
                "id": window.id,
                "name": window.name,
                "window_type": window.window_type,
                "start_at": window.start_at.isoformat(),
                "end_at": window.end_at.isoformat(),
                "timezone": window.timezone,
            }

    # 获取设备健康信息
    device_info = None
    if task.device_id:
        device = db.query(Device).filter(Device.id == task.device_id).first()
        if device:
            device_info = {
                "health_score": device.health_score,
                "risk_level": device.risk_level,
                "status": device.status
            }

    return {
        "id": task.id,
        "plan_id": task.plan_id,
        "plan": plan_info,
        "aop_project_id": task.aop_project_id,
        "aop_project": aop_project_info,
        "maintenance_window_id": task.maintenance_window_id,
        "maintenance_window": maintenance_window_info,
        "device_id": task.device_id,
        "device_name": task.device_name,
        "device": device_info,
        "task_no": task.task_no,
        "scheduled_date": task.scheduled_date.isoformat() if task.scheduled_date else None,
        "scheduled_end": task.scheduled_end.isoformat() if task.scheduled_end else None,
        "estimated_hours": float(task.estimated_hours) if task.estimated_hours is not None else None,
        "schedule_source": task.schedule_source,
        "actual_date": task.actual_date.isoformat() if task.actual_date else None,
        "status": task.status,
        "maintenance_id": task.maintenance_id,
        "maintenance": maintenance_info,
        "notes": task.notes,
        "created_at": task.created_at.isoformat() if task.created_at else None
    }


@router.post("/tasks/{task_id}/start")
async def start_task(
    task_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_planned_execute),
):
    """开始执行任务"""
    task = db.query(MaintenanceTask).filter(MaintenanceTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    if task.status not in ["pending", "overdue"]:
        raise HTTPException(status_code=400, detail="任务状态不允许开始")

    task.status = "in_progress"
    if task.aop_project:
        task.aop_project.status = "in_progress"
    db.commit()

    return {"message": "任务已开始"}


@router.post("/tasks/{task_id}/complete")
async def complete_task(
    task_id: int,
    maintenance_data: Optional[TaskCompleteRequest] = None,
    db: Session = Depends(get_db),
    _: None = Depends(require_planned_execute),
    principal: Principal = Depends(get_current_principal),
):
    """完成任务并可选创建维修单"""
    task = db.query(MaintenanceTask).filter(MaintenanceTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    if task.status != "in_progress":
        raise HTTPException(status_code=400, detail="任务未处于进行中状态")

    completion_data = None
    if maintenance_data is not None:
        completion_data = (
            maintenance_data
            if isinstance(maintenance_data, TaskCompleteRequest)
            else TaskCompleteRequest.model_validate(maintenance_data)
        )
    completion_values = (
        completion_data.model_dump(exclude_defaults=True, exclude_none=True)
        if completion_data
        else {}
    )
    # 备件动作单独处理：不参与"是否创建维修单"的判定，仅在单事务内一并落库
    spare_movements = completion_values.pop("spare_movements", None)
    # 权限前置检查：带备件动作时须持有 spare_movement:write，
    # 在任何状态变更（任务完成/维修单创建）之前失败，保证 403 零副作用
    if spare_movements:
        require_movement_write_for_side_effect(principal, db)

    parts_cost = float(completion_data.parts_cost) if completion_data else 0
    labor_hours = float(completion_data.labor_hours) if completion_data else 0
    labor_cost = float(completion_data.labor_cost) if completion_data else 0

    # 如果提供了维修数据，创建维修单
    if completion_values:
        maint_no = f"MAINT-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:4].upper()}"

        maintenance = MaintenanceRecord(
            maint_no=maint_no,
            device_id=task.device_id,
            device_name=task.device_name,
            maint_type="preventive",
            title=f"计划性运维: {task.task_no}",
            problem_description=f"关联任务: {task.task_no}",
            description=completion_data.description or f"计划性运维任务 {task.task_no}",
            parts_replaced=completion_data.parts_replaced,
            parts_cost=parts_cost,
            labor_hours=labor_hours,
            labor_cost=labor_cost,
            maint_time=datetime.utcnow(),
            operator=_actor_username(principal),
        )
        db.add(maintenance)
        db.flush()
        task.maintenance_id = maintenance.id

    task.status = "completed"
    task.actual_date = datetime.utcnow()

    # 如果有关联计划，更新下次执行日期
    if task.plan_id:
        plan = db.query(MaintenancePlan).filter(MaintenancePlan.id == task.plan_id).first()
        if plan and plan.cycle_days:
            plan.next_date = datetime.utcnow() + timedelta(days=plan.cycle_days)
    if task.aop_project:
        task.aop_project.status = "completed"
        task.aop_project.completed_at = task.actual_date
        result = completion_data.completion_result if completion_data else "success"
        task.aop_project.completion_result = result
        completion_notes = (
            completion_data.completion_notes or completion_data.description
            if completion_data
            else None
        )
        if completion_notes:
            task.aop_project.completion_notes = completion_notes
        if completion_values:
            task.aop_project.actual_hours = labor_hours
            task.aop_project.actual_cost = parts_cost + labor_cost

    # 备件动作与任务完成在同一事务内原子落库：
    # 任一条失败整批回滚（任务保持 in_progress、无任何 movement 落库）
    if spare_movements:
        try:
            svc_create_movements(
                db,
                spare_movements,
                _actor_username(principal),
            )
        except ValueError as exc:
            db.rollback()
            message = exc.args[0] if exc.args else "备件出入库失败，请检查序列号与库存"
            raise HTTPException(status_code=400, detail=message)

    db.commit()

    # 触发工作流（维修完成）
    from app.shared.cache import cache
    cache.invalidate_prefix("dashboard:")

    return {
        "message": "任务完成",
        "maintenance_id": task.maintenance_id
    }


@router.post("/tasks/{task_id}/skip")
async def skip_task(
    task_id: int,
    reason: Optional[str] = Query(default=None, max_length=500),
    db: Session = Depends(get_db),
    _: None = Depends(require_planned_execute),
):
    """跳过任务"""
    task = db.query(MaintenanceTask).filter(MaintenanceTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    if task.status not in ["pending", "overdue"]:
        raise HTTPException(status_code=400, detail="任务状态不允许跳过")

    task.status = "skipped"

    # 更新notes
    try:
        notes_data = json.loads(task.notes or '{}')
    except:
        notes_data = {}

    notes_data['skip_reason'] = reason or '未说明'
    task.notes = json.dumps(notes_data)
    if task.aop_project:
        task.aop_project.status = "cancelled"

    db.commit()

    return {"message": "任务已跳过"}


@router.delete("/tasks/{task_id}")
async def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(require_planned_delete),
):
    """删除任务"""
    task = db.query(MaintenanceTask).filter(MaintenanceTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    if task.status in ["in_progress", "completed"]:
        raise HTTPException(status_code=400, detail="进行中或已完成的任务不能删除")

    if task.aop_project:
        task.aop_project.status = "proposed"
    db.delete(task)
    db.commit()

    return {"message": "删除成功"}


# ============ AI增强功能 ============

@router.post("/generate-ai-tasks")
async def generate_ai_recommended_tasks(
    request: GenerateAIRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    _: None = Depends(require_planned_execute),
):
    """
    AI推荐巡检任务生成

    根据设备健康评分和风险等级自动生成巡检任务
    """
    # 查询符合条件的设备
    query = db.query(Device).filter(
        Device.status.in_(['online', 'offline', 'maintenance'])
    )

    devices = query.limit(request.max_devices).all()

    generated_tasks = []

    for device in devices:
        health_score = device.health_score or 100
        risk_level = device.risk_level or 'low'

        # 判断是否符合生成条件
        should_generate = False
        reason = ""

        if health_score < request.min_health_score:
            should_generate = True
            reason = f"健康评分低于{request.min_health_score}"

        if risk_level in request.risk_levels:
            should_generate = True
            reason = f"风险等级为{risk_level}"

        if should_generate:
            # 检查是否已有待处理的巡检任务
            existing = db.query(MaintenanceTask).filter(
                MaintenanceTask.device_id == device.id,
                MaintenanceTask.status.in_(['pending', 'overdue', 'in_progress'])
            ).first()

            if existing:
                continue

            # 创建巡检任务
            scheduled_date = datetime.utcnow() + timedelta(days=request.days_offset)
            task_no = f"AI-TASK-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:4].upper()}"

            task = MaintenanceTask(
                device_id=device.id,
                device_name=device.name,
                task_no=task_no,
                scheduled_date=scheduled_date,
                status='pending',
                notes=json.dumps({
                    "ai_generated": True,
                    "reason": reason,
                    "health_score": health_score,
                    "risk_level": risk_level,
                    "generated_by": "health_check_system"
                })
            )

            db.add(task)
            generated_tasks.append({
                "device_id": device.id,
                "device_name": device.name,
                "health_score": health_score,
                "risk_level": risk_level,
                "scheduled_date": scheduled_date.isoformat(),
                "reason": reason
            })

    db.commit()

    return {
        "success": True,
        "generated_count": len(generated_tasks),
        "tasks": generated_tasks,
        "criteria": {
            "min_health_score": request.min_health_score,
            "risk_levels": request.risk_levels,
            "days_offset": request.days_offset,
            "max_devices": request.max_devices,
        }
    }


@router.post("/devices/{device_id}/predictive-task")
async def generate_predictive_task_for_device(
    device_id: int,
    days_offset: int = Query(default=7, ge=0, le=3650),
    db: Session = Depends(get_db),
    _: None = Depends(require_planned_execute),
):
    """
    为单个设备生成预测性维护任务

    基于AI分析和设备历史数据
    """
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="设备不存在")

    # 检查是否已有待处理任务
    existing = db.query(MaintenanceTask).filter(
        MaintenanceTask.device_id == device_id,
        MaintenanceTask.status.in_(['pending', 'overdue', 'in_progress'])
    ).first()

    if existing:
        return {
            "success": False,
            "message": "设备已有待处理任务",
            "existing_task_id": existing.id
        }

    # 创建预测性维护任务
    scheduled_date = datetime.utcnow() + timedelta(days=days_offset)
    task_no = f"PM-TASK-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:4].upper()}"

    task = MaintenanceTask(
        device_id=device.id,
        device_name=device.name,
        task_no=task_no,
        scheduled_date=scheduled_date,
        status='pending',
        notes=json.dumps({
            "ai_generated": True,
            "task_type": "predictive_maintenance",
            "health_score": device.health_score or 100,
            "risk_level": device.risk_level or 'low',
            "uptime_days": device.uptime_days or 0,
            "generated_by": "predictive_system"
        })
    )

    db.add(task)
    db.commit()
    db.refresh(task)

    return {
        "success": True,
        "task_id": task.id,
        "task_no": task_no,
        "device_name": device.name,
        "scheduled_date": scheduled_date.isoformat(),
        "health_score": device.health_score,
        "risk_level": device.risk_level
    }


@router.get("/devices/{device_id}/maintenance-history")
async def get_device_maintenance_history(
    device_id: int,
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: None = Depends(require_planned_read),
):
    """获取设备维护历史摘要"""
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="设备不存在")

    # 获取历史维修记录
    maintenance_records = db.query(MaintenanceRecord).filter(
        MaintenanceRecord.device_id == device_id
    ).order_by(MaintenanceRecord.created_at.desc()).limit(limit).all()

    # 获取历史巡检任务
    pm_tasks = db.query(MaintenanceTask).filter(
        MaintenanceTask.device_id == device_id,
        MaintenanceTask.status == 'completed'
    ).order_by(MaintenanceTask.actual_date.desc()).limit(limit).all()

    # 统计
    total_maintenance = db.query(MaintenanceRecord).filter(
        MaintenanceRecord.device_id == device_id
    ).count()

    total_pm_tasks = db.query(MaintenanceTask).filter(
        MaintenanceTask.device_id == device_id,
        MaintenanceTask.status == 'completed'
    ).count()

    return {
        "device_id": device_id,
        "device_name": device.name,
        "health_score": device.health_score,
        "risk_level": device.risk_level,
        "total_maintenance_count": total_maintenance,
        "total_pm_tasks_count": total_pm_tasks,
        "maintenance_records": [
            {
                "id": m.id,
                "maint_no": m.maint_no,
                "maint_type": m.maint_type,
                "created_at": m.created_at.isoformat()
            }
            for m in maintenance_records
        ],
        "pm_tasks": [
            {
                "id": t.id,
                "task_no": t.task_no,
                "scheduled_date": t.scheduled_date.isoformat(),
                "actual_date": t.actual_date.isoformat() if t.actual_date else None
            }
            for t in pm_tasks
        ]
    }


# ============ 统计 API ============

@router.get("/stats")
async def get_stats(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    device_id: Optional[int] = None,
    db: Session = Depends(get_db),
    _: None = Depends(require_planned_read),
):
    """获取计划性运维统计"""
    # 任务统计
    task_query = db.query(MaintenanceTask)

    if start_date:
        task_query = task_query.filter(MaintenanceTask.scheduled_date >= start_date)
    if end_date:
        task_query = task_query.filter(MaintenanceTask.scheduled_date <= end_date)

    if device_id:
        task_query = task_query.filter(MaintenanceTask.device_id == device_id)

    tasks = task_query.all()
    now = datetime.utcnow()

    # 统计各状态任务数
    status_counts = {}
    ai_generated_count = 0
    for task in tasks:
        actual_status = "overdue" if task.status == "pending" and task.scheduled_date < now else task.status
        status_counts[actual_status] = status_counts.get(actual_status, 0) + 1

        # 统计AI生成任务
        if task.notes:
            try:
                notes_data = json.loads(task.notes)
                if notes_data.get('ai_generated'):
                    ai_generated_count += 1
            except:
                pass

    # 获取已完成任务的维修单，汇总成本
    completed_task_ids = [t.id for t in tasks if t.status == "completed" and t.maintenance_id]

    cost_query = db.query(
        func.sum(MaintenanceRecord.parts_cost),
        func.sum(MaintenanceRecord.labor_cost),
        func.sum(MaintenanceRecord.labor_hours),
        func.count(MaintenanceRecord.id)
    ).filter(MaintenanceRecord.id.in_(
        [t.maintenance_id for t in tasks if t.maintenance_id]
    ))

    cost_result = cost_query.first()

    return {
        "tasks": {
            "total": len(tasks),
            "completed": status_counts.get("completed", 0),
            "in_progress": status_counts.get("in_progress", 0),
            "pending": status_counts.get("pending", 0),
            "overdue": status_counts.get("overdue", 0),
            "skipped": status_counts.get("skipped", 0),
            "ai_generated": ai_generated_count
        },
        "costs": {
            "parts_cost": float(cost_result[0] or 0),
            "labor_cost": float(cost_result[1] or 0),
            "total_cost": float((cost_result[0] or 0) + (cost_result[1] or 0)),
            "labor_hours": float(cost_result[2] or 0),
            "maintenance_count": cost_result[3] or 0
        }
    }


@router.post("/generate-tasks")
async def generate_tasks_for_plans(
    db: Session = Depends(get_db),
    _: None = Depends(require_planned_execute),
):
    """为活跃计划自动生成任务"""
    now = datetime.utcnow()
    plans = db.query(MaintenancePlan).filter(
        MaintenancePlan.status == "active",
        MaintenancePlan.auto_generate == True,
        MaintenancePlan.next_date >= now - timedelta(days=1)
    ).all()

    generated_count = 0

    for plan in plans:
        # 检查是否已有相同日期的任务
        existing = db.query(MaintenanceTask).filter(
            MaintenanceTask.plan_id == plan.id,
            MaintenanceTask.scheduled_date >= plan.next_date - timedelta(days=1),
            MaintenanceTask.scheduled_date <= plan.next_date + timedelta(days=1)
        ).first()

        if existing:
            continue

        task_no = f"TASK-{now.strftime('%Y%m%d')}-{uuid.uuid4().hex[:4].upper()}"

        task_status = "pending"
        if plan.next_date < now:
            task_status = "overdue"

        task = MaintenanceTask(
            plan_id=plan.id,
            device_id=plan.device_id,
            device_name=plan.device_name,
            task_no=task_no,
            scheduled_date=plan.next_date,
            status=task_status,
            notes=json.dumps({"plan_generated": True})
        )
        db.add(task)
        generated_count += 1

    db.commit()

    return {"generated": generated_count, "message": f"已生成 {generated_count} 个任务"}