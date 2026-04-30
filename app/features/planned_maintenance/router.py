"""Planned maintenance router - 计划性运维管理"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
from datetime import datetime, timedelta
import uuid

from pydantic import BaseModel

from app.shared.database import get_db
from app.shared.models import MaintenancePlan, MaintenanceTask, MaintenanceRecord, Device

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
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    skip: int = 0,
    limit: int = 100
):
    """获取运维任务列表"""
    db: Session = next(get_db())

    try:
        query = db.query(MaintenanceTask)

        if plan_id:
            query = query.filter(MaintenanceTask.plan_id == plan_id)

        if device_id:
            query = query.filter(MaintenanceTask.device_id == device_id)

        if status:
            query = query.filter(MaintenanceTask.status == status)

        if start_date:
            query = query.filter(MaintenanceTask.scheduled_date >= start_date)

        if end_date:
            query = query.filter(MaintenanceTask.scheduled_date <= end_date)

        total = query.count()
        tasks = query.order_by(MaintenanceTask.scheduled_date).offset(skip).limit(limit).all()
        now = datetime.utcnow()

        return {
            "total": total,
            "items": [
                {
                    "id": t.id,
                    "plan_id": t.plan_id,
                    "device_id": t.device_id,
                    "device_name": t.device_name,
                    "task_no": t.task_no,
                    "scheduled_date": t.scheduled_date.isoformat() if t.scheduled_date else None,
                    "actual_date": t.actual_date.isoformat() if t.actual_date else None,
                    # 动态判断超期状态：pending且scheduled_date已过
                    "status": "overdue" if t.status == "pending" and t.scheduled_date < now else t.status,
                    "maintenance_id": t.maintenance_id,
                    "notes": t.notes,
                    "created_at": t.created_at.isoformat() if t.created_at else None
                }
                for t in tasks
            ]
        }
    finally:
        db.close()


@router.post("/tasks")
async def create_task(task_data: TaskCreate):
    """手动创建运维任务"""
    db: Session = next(get_db())

    try:
        # 自动生成任务编号
        task_no = f"TASK-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:4].upper()}"

        # 检查是否超期
        now = datetime.utcnow()
        status = "pending"
        if task_data.scheduled_date < now:
            status = "overdue"

        task = MaintenanceTask(
            plan_id=task_data.plan_id,
            device_id=task_data.device_id,
            device_name=task_data.device_name,
            task_no=task_no,
            scheduled_date=task_data.scheduled_date,
            status=status,
            notes=task_data.notes
        )
        db.add(task)
        db.commit()
        db.refresh(task)

        return {"id": task.id, "task_no": task_no, "message": "任务创建成功"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()


@router.get("/tasks/{task_id}")
async def get_task(task_id: int):
    """获取运维任务详情"""
    db: Session = next(get_db())

    try:
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

        return {
            "id": task.id,
            "plan_id": task.plan_id,
            "plan": plan_info,
            "device_id": task.device_id,
            "device_name": task.device_name,
            "task_no": task.task_no,
            "scheduled_date": task.scheduled_date.isoformat() if task.scheduled_date else None,
            "actual_date": task.actual_date.isoformat() if task.actual_date else None,
            "status": task.status,
            "maintenance_id": task.maintenance_id,
            "maintenance": maintenance_info,
            "notes": task.notes,
            "created_at": task.created_at.isoformat() if task.created_at else None
        }
    finally:
        db.close()


@router.post("/tasks/{task_id}/start")
async def start_task(task_id: int):
    """开始执行任务"""
    db: Session = next(get_db())

    try:
        task = db.query(MaintenanceTask).filter(MaintenanceTask.id == task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")

        if task.status not in ["pending", "overdue"]:
            raise HTTPException(status_code=400, detail="任务状态不允许开始")

        task.status = "in_progress"
        db.commit()

        return {"message": "任务已开始"}
    finally:
        db.close()


@router.post("/tasks/{task_id}/complete")
async def complete_task(task_id: int, maintenance_data: Optional[dict] = None):
    """完成任务并可选创建维修单"""
    db: Session = next(get_db())

    try:
        task = db.query(MaintenanceTask).filter(MaintenanceTask.id == task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")

        if task.status != "in_progress":
            raise HTTPException(status_code=400, detail="任务未处于进行中状态")

        # 如果提供了维修数据，创建维修单
        if maintenance_data:
            maint_no = f"MAINT-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:4].upper()}"

            # 处理成本字段，确保是数值
            parts_cost = maintenance_data.get("parts_cost", 0)
            if parts_cost is None:
                parts_cost = 0
            parts_cost = float(parts_cost)

            labor_hours = maintenance_data.get("labor_hours", 0)
            if labor_hours is None:
                labor_hours = 0
            labor_hours = float(labor_hours)

            labor_cost = maintenance_data.get("labor_cost", 0)
            if labor_cost is None:
                labor_cost = 0
            labor_cost = float(labor_cost)

            maintenance = MaintenanceRecord(
                maint_no=maint_no,
                device_id=task.device_id,
                device_name=task.device_name,
                maint_type="preventive",  # 计划性维修
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

        from app.shared.cache import cache
        cache.invalidate_prefix("dashboard:")

        return {
            "message": "任务完成",
            "maintenance_id": task.maintenance_id
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.post("/tasks/{task_id}/skip")
async def skip_task(task_id: int, reason: Optional[str] = None):
    """跳过任务"""
    db: Session = next(get_db())

    try:
        task = db.query(MaintenanceTask).filter(MaintenanceTask.id == task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")

        if task.status not in ["pending", "overdue"]:
            raise HTTPException(status_code=400, detail="任务状态不允许跳过")

        task.status = "skipped"
        task.notes = (task.notes or "") + f"\n跳过原因: {reason or '未说明'}"
        db.commit()

        return {"message": "任务已跳过"}
    finally:
        db.close()


@router.delete("/tasks/{task_id}")
async def delete_task(task_id: int):
    """删除任务"""
    db: Session = next(get_db())

    try:
        task = db.query(MaintenanceTask).filter(MaintenanceTask.id == task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")

        if task.status in ["in_progress", "completed"]:
            raise HTTPException(status_code=400, detail="进行中或已完成的任务不能删除")

        db.delete(task)
        db.commit()

        return {"message": "删除成功"}
    finally:
        db.close()


# ============ 统计 API ============

@router.get("/stats")
async def get_stats(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    device_id: Optional[int] = None,
    plan_type: Optional[str] = None
):
    """获取计划性运维统计"""
    db: Session = next(get_db())

    try:
        # 任务统计 - 默认统计所有任务，不限制时间范围
        task_query = db.query(MaintenanceTask)

        # 只有明确传入时间范围时才筛选
        if start_date:
            task_query = task_query.filter(MaintenanceTask.scheduled_date >= start_date)
        if end_date:
            task_query = task_query.filter(MaintenanceTask.scheduled_date <= end_date)

        if device_id:
            task_query = task_query.filter(MaintenanceTask.device_id == device_id)

        tasks = task_query.all()
        now = datetime.utcnow()

        # 统计各状态任务数（动态判断超期）
        status_counts = {}
        for task in tasks:
            # 动态判断超期状态
            actual_status = "overdue" if task.status == "pending" and task.scheduled_date < now else task.status
            status_counts[actual_status] = status_counts.get(actual_status, 0) + 1

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

        # 按计划类型分组统计
        plan_type_stats = {}
        for task in tasks:
            if task.plan_id:
                plan = db.query(MaintenancePlan).filter(MaintenancePlan.id == task.plan_id).first()
                if plan:
                    pt = plan.plan_type
                    if pt not in plan_type_stats:
                        plan_type_stats[pt] = {"total": 0, "completed": 0}
                    plan_type_stats[pt]["total"] += 1
                    # 使用动态状态判断是否完成
                    actual_status = "overdue" if task.status == "pending" and task.scheduled_date < now else task.status
                    if actual_status == "completed":
                        plan_type_stats[pt]["completed"] += 1

        return {
            "period": {
                "start": start_date.isoformat() if start_date else None,
                "end": end_date.isoformat() if end_date else None
            },
            "tasks": {
                "total": len(tasks),
                "completed": status_counts.get("completed", 0),
                "in_progress": status_counts.get("in_progress", 0),
                "pending": status_counts.get("pending", 0),
                "overdue": status_counts.get("overdue", 0),
                "skipped": status_counts.get("skipped", 0)
            },
            "costs": {
                "parts_cost": float(cost_result[0] or 0),
                "labor_cost": float(cost_result[1] or 0),
                "total_cost": float((cost_result[0] or 0) + (cost_result[1] or 0)),
                "labor_hours": float(cost_result[2] or 0),
                "maintenance_count": cost_result[3] or 0
            },
            "by_plan_type": plan_type_stats
        }
    finally:
        db.close()


@router.post("/generate-tasks")
async def generate_tasks_for_plans():
    """为活跃计划自动生成任务"""
    db: Session = next(get_db())

    try:
        # 获取所有活跃且开启自动生成的计划
        now = datetime.utcnow()
        plans = db.query(MaintenancePlan).filter(
            MaintenancePlan.status == "active",
            MaintenancePlan.auto_generate == True,
            MaintenancePlan.next_date >= now  # 只生成未过期或今天的任务
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

            # 判断是否超期
            task_status = "pending"
            if plan.next_date < now:
                task_status = "overdue"

            task = MaintenanceTask(
                plan_id=plan.id,
                device_id=plan.device_id,
                device_name=plan.device_name,
                task_no=task_no,
                scheduled_date=plan.next_date,
                status=task_status
            )
            db.add(task)
            generated_count += 1

        db.commit()

        return {"generated": generated_count, "message": f"已生成 {generated_count} 个任务"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()