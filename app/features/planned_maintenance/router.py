"""Planned maintenance router - 计划性运维管理（AI增强版）

新增功能：
- AI推荐巡检任务生成
- 健康评分驱动的自动PM任务
- 与工作流引擎集成
- 预测性维护建议
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import uuid
import json

from pydantic import BaseModel

from app.shared.database import get_db
from app.shared.models import MaintenancePlan, MaintenanceTask, MaintenanceRecord, Device
from app.services.ai_manager import predictive_maintenance_analysis

router = APIRouter(prefix="/api/planned-maintenance", tags=["planned-maintenance"])


# ============ Pydantic 模型 ============

class PlanCreate(BaseModel):
    name: str
    device_id: Optional[int] = None
    device_name: Optional[str] = None
    plan_type: str  # routine_check, parts_replace, vendor_service
    cycle_days: int = 30
    next_date: str  # 接收日期字符串，如 "2026-05-01"
    data_basis: Optional[str] = None
    auto_generate: bool = True


class PlanUpdate(BaseModel):
    name: Optional[str] = None
    cycle_days: Optional[int] = None
    next_date: Optional[str] = None  # 接收日期字符串
    data_basis: Optional[str] = None
    auto_generate: Optional[bool] = None
    status: Optional[str] = None


class TaskCreate(BaseModel):
    plan_id: Optional[int] = None
    device_id: Optional[int] = None
    device_name: Optional[str] = None
    scheduled_date: datetime
    notes: Optional[str] = None
    ai_generated: bool = False


class GenerateAIRequest(BaseModel):
    """AI推荐任务生成请求"""
    min_health_score: int = 60  # 健康评分低于此值的设备生成巡检任务
    risk_levels: List[str] = ['high', 'critical']  # 风险等级筛选
    days_offset: int = 3  # 任务安排在几天后


# ============ 维护计划 API ============

@router.get("/plans")
async def list_plans(status: Optional[str] = None, skip: int = 0, limit: int = 100):
    """获取维护计划列表"""
    db: Session = next(get_db())

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
    finally:
        db.close()


@router.post("/plans")
async def create_plan(plan_data: PlanCreate):
    """创建维护计划"""
    db: Session = next(get_db())

    try:
        # 解析日期字符串，转换为 datetime
        next_date_dt = datetime.strptime(plan_data.next_date, "%Y-%m-%d")

        plan = MaintenancePlan(
            name=plan_data.name,
            device_id=plan_data.device_id,
            device_name=plan_data.device_name,
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
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()


@router.get("/plans/{plan_id}")
async def get_plan(plan_id: int):
    """获取维护计划详情"""
    db: Session = next(get_db())

    try:
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
    finally:
        db.close()


@router.put("/plans/{plan_id}")
async def update_plan(plan_id: int, plan_data: PlanUpdate):
    """更新维护计划"""
    db: Session = next(get_db())

    try:
        plan = db.query(MaintenancePlan).filter(MaintenancePlan.id == plan_id).first()
        if not plan:
            raise HTTPException(status_code=404, detail="维护计划不存在")

        update_data = plan_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            if hasattr(plan, key):
                # 处理日期字符串转换
                if key == "next_date" and value:
                    value = datetime.strptime(value, "%Y-%m-%d")
                setattr(plan, key, value)

        db.commit()
        db.refresh(plan)

        return {"id": plan.id, "message": "更新成功"}
    finally:
        db.close()


@router.delete("/plans/{plan_id}")
async def delete_plan(plan_id: int):
    """删除维护计划"""
    db: Session = next(get_db())

    try:
        plan = db.query(MaintenancePlan).filter(MaintenancePlan.id == plan_id).first()
        if not plan:
            raise HTTPException(status_code=404, detail="维护计划不存在")

        db.delete(plan)
        db.commit()

        return {"message": "删除成功"}
    finally:
        db.close()


# ============ 运维任务 API ============

@router.get("/tasks")
async def list_tasks(
    plan_id: Optional[int] = None,
    device_id: Optional[int] = None,
    status: Optional[str] = None,
    ai_generated: Optional[bool] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
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
            "device_id": t.device_id,
            "device_name": t.device_name,
            "task_no": t.task_no,
            "scheduled_date": t.scheduled_date.isoformat() if t.scheduled_date else None,
            "actual_date": t.actual_date.isoformat() if t.actual_date else None,
            "status": "overdue" if t.status == "pending" and t.scheduled_date < now else t.status,
            "maintenance_id": t.maintenance_id,
            "ai_generated": ai_info,
            "notes": t.notes,
            "created_at": t.created_at.isoformat() if t.created_at else None
        })

    return {"total": total, "items": items}


@router.post("/tasks")
async def create_task(task_data: TaskCreate, db: Session = Depends(get_db)):
    """手动创建运维任务"""
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
        device_id=task_data.device_id,
        device_name=task_data.device_name,
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
async def get_task(task_id: int, db: Session = Depends(get_db)):
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
        "device_id": task.device_id,
        "device_name": task.device_name,
        "device": device_info,
        "task_no": task.task_no,
        "scheduled_date": task.scheduled_date.isoformat() if task.scheduled_date else None,
        "actual_date": task.actual_date.isoformat() if task.actual_date else None,
        "status": task.status,
        "maintenance_id": task.maintenance_id,
        "maintenance": maintenance_info,
        "notes": task.notes,
        "created_at": task.created_at.isoformat() if task.created_at else None
    }


@router.post("/tasks/{task_id}/start")
async def start_task(task_id: int, db: Session = Depends(get_db)):
    """开始执行任务"""
    task = db.query(MaintenanceTask).filter(MaintenanceTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    if task.status not in ["pending", "overdue"]:
        raise HTTPException(status_code=400, detail="任务状态不允许开始")

    task.status = "in_progress"
    db.commit()

    return {"message": "任务已开始"}


@router.post("/tasks/{task_id}/complete")
async def complete_task(task_id: int, maintenance_data: Optional[dict] = None, db: Session = Depends(get_db)):
    """完成任务并可选创建维修单"""
    task = db.query(MaintenanceTask).filter(MaintenanceTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    if task.status != "in_progress":
        raise HTTPException(status_code=400, detail="任务未处于进行中状态")

    # 如果提供了维修数据，创建维修单
    if maintenance_data:
        maint_no = f"MAINT-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:4].upper()}"

        # 处理成本字段，确保是数值
        parts_cost = float(maintenance_data.get("parts_cost", 0) or 0)
        labor_hours = float(maintenance_data.get("labor_hours", 0) or 0)
        labor_cost = float(maintenance_data.get("labor_cost", 0) or 0)

        maintenance = MaintenanceRecord(
            maint_no=maint_no,
            device_id=task.device_id,
            device_name=task.device_name,
            maint_type="preventive",
            title=f"计划性运维: {task.task_no}",
            problem_description=f"关联任务: {task.task_no}",
            description=maintenance_data.get("description", f"计划性运维任务 {task.task_no}"),
            parts_replaced=maintenance_data.get("parts_replaced"),
            parts_cost=parts_cost,
            labor_hours=labor_hours,
            labor_cost=labor_cost,
            maint_time=datetime.utcnow()
        )
        db.add(maintenance)
        db.commit()
        db.refresh(maintenance)

        task.maintenance_id = maintenance.id

    task.status = "completed"
    task.actual_date = datetime.utcnow()
    db.commit()

    # 如果有关联计划，更新下次执行日期
    if task.plan_id:
        plan = db.query(MaintenancePlan).filter(MaintenancePlan.id == task.plan_id).first()
        if plan and plan.cycle_days:
            plan.next_date = datetime.utcnow() + timedelta(days=plan.cycle_days)
            db.commit()

    # 触发工作流（维修完成）
    from app.shared.cache import cache
    cache.invalidate_prefix("dashboard:")

    return {
        "message": "任务完成",
        "maintenance_id": task.maintenance_id
    }


@router.post("/tasks/{task_id}/skip")
async def skip_task(task_id: int, reason: Optional[str] = None, db: Session = Depends(get_db)):
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

    db.commit()

    return {"message": "任务已跳过"}


@router.delete("/tasks/{task_id}")
async def delete_task(task_id: int, db: Session = Depends(get_db)):
    """删除任务"""
    task = db.query(MaintenanceTask).filter(MaintenanceTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    if task.status in ["in_progress", "completed"]:
        raise HTTPException(status_code=400, detail="进行中或已完成的任务不能删除")

    db.delete(task)
    db.commit()

    return {"message": "删除成功"}


# ============ AI增强功能 ============

@router.post("/generate-ai-tasks")
async def generate_ai_recommended_tasks(
    request: GenerateAIRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    AI推荐巡检任务生成

    根据设备健康评分和风险等级自动生成巡检任务
    """
    # 查询符合条件的设备
    query = db.query(Device).filter(
        Device.status.in_(['online', 'offline', 'maintenance'])
    )

    devices = query.all()

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
            "days_offset": request.days_offset
        }
    }


@router.post("/devices/{device_id}/predictive-task")
async def generate_predictive_task_for_device(
    device_id: int,
    days_offset: int = 7,
    db: Session = Depends(get_db)
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
    limit: int = 20,
    db: Session = Depends(get_db)
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
    db: Session = Depends(get_db)
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
async def generate_tasks_for_plans(db: Session = Depends(get_db)):
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