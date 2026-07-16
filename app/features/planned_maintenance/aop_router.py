"""AOP planning API for annual network maintenance work."""

import json
from datetime import datetime
from decimal import Decimal
from typing import List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.features.planned_maintenance.aop_service import (
    AopSchedulingError,
    generate_aop_tasks,
)
from app.shared.database import get_db
from app.shared.models import (
    AopMaintenanceWindow,
    AopProgram,
    AopProject,
    MaintenanceTask,
)


router = APIRouter(prefix="/aop", tags=["planned-maintenance-aop"])

ProgramStatus = Literal["draft", "submitted", "approved", "active", "closed"]
ProjectType = Literal["replacement", "maintenance", "upgrade"]
ProjectStatus = Literal["proposed", "scheduled", "in_progress", "completed", "cancelled"]
ApprovalStatus = Literal["draft", "submitted", "approved", "rejected"]
WindowType = Literal["shutdown", "holiday", "weekend", "standard"]
WindowStatus = Literal["draft", "approved", "cancelled"]


class ProgramCreate(BaseModel):
    year: int = Field(ge=2000, le=2100)
    name: str = Field(min_length=1, max_length=200)
    version: int = Field(default=1, ge=1)
    status: ProgramStatus = "draft"
    owner: Optional[str] = Field(default=None, max_length=100)
    currency: str = Field(default="CNY", min_length=3, max_length=3)
    budget_amount: Decimal = Field(default=Decimal("0"), ge=0)
    notes: Optional[str] = None

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return value.upper()


class ProgramUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    status: Optional[ProgramStatus] = None
    owner: Optional[str] = Field(default=None, max_length=100)
    currency: Optional[str] = Field(default=None, min_length=3, max_length=3)
    budget_amount: Optional[Decimal] = Field(default=None, ge=0)
    notes: Optional[str] = None

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: Optional[str]) -> Optional[str]:
        return value.upper() if value else value


class WindowCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    window_type: WindowType
    start_at: datetime
    end_at: datetime
    timezone: str = Field(default="Asia/Shanghai", min_length=1, max_length=64)
    max_parallel_tasks: int = Field(default=1, ge=1, le=100)
    status: WindowStatus = "draft"
    owner: Optional[str] = Field(default=None, max_length=100)
    notes: Optional[str] = None

    @model_validator(mode="after")
    def validate_range(self):
        if self.end_at <= self.start_at:
            raise ValueError("维护窗口结束时间必须晚于开始时间")
        return self


class WindowUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    window_type: Optional[WindowType] = None
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None
    timezone: Optional[str] = Field(default=None, min_length=1, max_length=64)
    max_parallel_tasks: Optional[int] = Field(default=None, ge=1, le=100)
    status: Optional[WindowStatus] = None
    owner: Optional[str] = Field(default=None, max_length=100)
    notes: Optional[str] = None


class ProjectCreate(BaseModel):
    project_code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=200)
    project_type: ProjectType
    device_id: Optional[int] = None
    device_name: Optional[str] = Field(default=None, max_length=100)
    asset_scope: Optional[str] = None
    current_version: Optional[str] = Field(default=None, max_length=100)
    target_version: Optional[str] = Field(default=None, max_length=100)
    planned_start: datetime
    planned_end: Optional[datetime] = None
    preferred_window_type: Optional[WindowType] = None
    estimated_hours: Decimal = Field(default=Decimal("1"), gt=0)
    estimated_cost: Decimal = Field(default=Decimal("0"), ge=0)
    owner: Optional[str] = Field(default=None, max_length=100)
    priority: Literal["P1", "P2", "P3", "P4"] = "P3"
    risk_level: Literal["low", "medium", "high", "critical"] = "medium"
    approval_status: ApprovalStatus = "draft"
    status: ProjectStatus = "proposed"
    dependencies: List[str] = Field(default_factory=list)
    business_justification: Optional[str] = None
    rollback_plan: Optional[str] = None
    notes: Optional[str] = None

    @model_validator(mode="after")
    def validate_range(self):
        if self.planned_end and self.planned_end <= self.planned_start:
            raise ValueError("计划结束时间必须晚于计划开始时间")
        if self.project_code in self.dependencies:
            raise ValueError("项目不能依赖自身")
        return self


class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    project_type: Optional[ProjectType] = None
    device_id: Optional[int] = None
    device_name: Optional[str] = Field(default=None, max_length=100)
    asset_scope: Optional[str] = None
    current_version: Optional[str] = Field(default=None, max_length=100)
    target_version: Optional[str] = Field(default=None, max_length=100)
    planned_start: Optional[datetime] = None
    planned_end: Optional[datetime] = None
    preferred_window_type: Optional[WindowType] = None
    estimated_hours: Optional[Decimal] = Field(default=None, gt=0)
    estimated_cost: Optional[Decimal] = Field(default=None, ge=0)
    owner: Optional[str] = Field(default=None, max_length=100)
    priority: Optional[Literal["P1", "P2", "P3", "P4"]] = None
    risk_level: Optional[Literal["low", "medium", "high", "critical"]] = None
    approval_status: Optional[ApprovalStatus] = None
    status: Optional[ProjectStatus] = None
    dependencies: Optional[List[str]] = None
    business_justification: Optional[str] = None
    rollback_plan: Optional[str] = None
    notes: Optional[str] = None


def _program_or_404(db: Session, program_id: int) -> AopProgram:
    program = db.query(AopProgram).filter(AopProgram.id == program_id).first()
    if program is None:
        raise HTTPException(status_code=404, detail="AOP 不存在")
    return program


def _lock_program(db: Session, program_id: int) -> AopProgram:
    program = db.query(AopProgram).filter(
        AopProgram.id == program_id
    ).with_for_update().first()
    if program is None:
        raise HTTPException(status_code=404, detail="AOP 不存在")
    return program


def _project_or_404(db: Session, project_id: int) -> AopProject:
    project = db.query(AopProject).filter(AopProject.id == project_id).first()
    if project is None:
        raise HTTPException(status_code=404, detail="AOP 项目不存在")
    return project


def _window_or_404(db: Session, window_id: int) -> AopMaintenanceWindow:
    window = db.query(AopMaintenanceWindow).filter(
        AopMaintenanceWindow.id == window_id
    ).first()
    if window is None:
        raise HTTPException(status_code=404, detail="维护窗口不存在")
    return window


def _program_dict(program: AopProgram, project_count: int = 0) -> dict:
    return {
        "id": program.id,
        "year": program.year,
        "version": program.version,
        "name": program.name,
        "status": program.status,
        "owner": program.owner,
        "currency": program.currency,
        "budget_amount": float(program.budget_amount or 0),
        "project_count": project_count,
        "notes": program.notes,
        "created_at": program.created_at.isoformat() if program.created_at else None,
        "updated_at": program.updated_at.isoformat() if program.updated_at else None,
    }


def _window_dict(window: AopMaintenanceWindow) -> dict:
    return {
        "id": window.id,
        "program_id": window.program_id,
        "name": window.name,
        "window_type": window.window_type,
        "start_at": window.start_at.isoformat(),
        "end_at": window.end_at.isoformat(),
        "timezone": window.timezone,
        "max_parallel_tasks": window.max_parallel_tasks,
        "status": window.status,
        "owner": window.owner,
        "notes": window.notes,
        "scheduled_task_count": len(window.tasks),
    }


def _project_dict(project: AopProject) -> dict:
    try:
        dependencies = json.loads(project.dependencies or "[]")
    except json.JSONDecodeError:
        dependencies = []
    task = project.task
    return {
        "id": project.id,
        "program_id": project.program_id,
        "project_code": project.project_code,
        "name": project.name,
        "project_type": project.project_type,
        "device_id": project.device_id,
        "device_name": project.device_name,
        "asset_scope": project.asset_scope,
        "current_version": project.current_version,
        "target_version": project.target_version,
        "planned_start": project.planned_start.isoformat(),
        "planned_end": project.planned_end.isoformat() if project.planned_end else None,
        "preferred_window_type": project.preferred_window_type,
        "estimated_hours": float(project.estimated_hours or 0),
        "estimated_cost": float(project.estimated_cost or 0),
        "owner": project.owner,
        "priority": project.priority,
        "risk_level": project.risk_level,
        "approval_status": project.approval_status,
        "status": project.status,
        "dependencies": dependencies,
        "business_justification": project.business_justification,
        "rollback_plan": project.rollback_plan,
        "notes": project.notes,
        "task": {
            "id": task.id,
            "task_no": task.task_no,
            "status": task.status,
            "scheduled_date": task.scheduled_date.isoformat(),
            "scheduled_end": task.scheduled_end.isoformat() if task.scheduled_end else None,
            "maintenance_window_id": task.maintenance_window_id,
        } if task else None,
    }


@router.get("/programs")
def list_programs(
    year: Optional[int] = None,
    status: Optional[ProgramStatus] = None,
    db: Session = Depends(get_db),
):
    query = db.query(AopProgram)
    if year is not None:
        query = query.filter(AopProgram.year == year)
    if status is not None:
        query = query.filter(AopProgram.status == status)
    programs = query.order_by(AopProgram.year.desc(), AopProgram.version.desc()).all()
    counts = dict(
        db.query(AopProject.program_id, func.count(AopProject.id))
        .group_by(AopProject.program_id)
        .all()
    )
    return {"total": len(programs), "items": [_program_dict(item, counts.get(item.id, 0)) for item in programs]}


@router.post("/programs", status_code=201)
def create_program(data: ProgramCreate, db: Session = Depends(get_db)):
    program = AopProgram(**data.model_dump())
    db.add(program)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="同一年度和版本的 AOP 已存在")
    db.refresh(program)
    return _program_dict(program)


@router.get("/programs/{program_id}")
def get_program(program_id: int, db: Session = Depends(get_db)):
    program = _program_or_404(db, program_id)
    return {
        **_program_dict(program, len(program.projects)),
        "projects": [_project_dict(item) for item in program.projects],
        "maintenance_windows": [_window_dict(item) for item in program.maintenance_windows],
    }


@router.put("/programs/{program_id}")
def update_program(program_id: int, data: ProgramUpdate, db: Session = Depends(get_db)):
    program = _lock_program(db, program_id)
    update_data = data.model_dump(exclude_unset=True)
    has_tasks = db.query(MaintenanceTask.id).join(
        AopProject,
        MaintenanceTask.aop_project_id == AopProject.id,
    ).filter(AopProject.program_id == program_id).first() is not None
    if (
        has_tasks
        and "status" in update_data
        and update_data["status"] not in ("approved", "active", "closed")
    ):
        raise HTTPException(status_code=409, detail="已有任务的 AOP 不能取消批准")
    for key, value in update_data.items():
        setattr(program, key, value)
    db.commit()
    db.refresh(program)
    return _program_dict(program, len(program.projects))


@router.get("/programs/{program_id}/windows")
def list_windows(program_id: int, db: Session = Depends(get_db)):
    _program_or_404(db, program_id)
    windows = db.query(AopMaintenanceWindow).filter(
        AopMaintenanceWindow.program_id == program_id
    ).order_by(AopMaintenanceWindow.start_at).all()
    return {"total": len(windows), "items": [_window_dict(item) for item in windows]}


@router.post("/programs/{program_id}/windows", status_code=201)
def create_window(program_id: int, data: WindowCreate, db: Session = Depends(get_db)):
    _lock_program(db, program_id)
    window = AopMaintenanceWindow(program_id=program_id, **data.model_dump())
    db.add(window)
    db.commit()
    db.refresh(window)
    return _window_dict(window)


@router.put("/windows/{window_id}")
def update_window(window_id: int, data: WindowUpdate, db: Session = Depends(get_db)):
    window = _window_or_404(db, window_id)
    _lock_program(db, window.program_id)
    db.refresh(window)
    update_data = data.model_dump(exclude_unset=True)
    start_at = update_data.get("start_at", window.start_at)
    end_at = update_data.get("end_at", window.end_at)
    if end_at <= start_at:
        raise HTTPException(status_code=422, detail="维护窗口结束时间必须晚于开始时间")
    if window.tasks:
        locked_fields = {
            "start_at", "end_at", "timezone", "window_type", "max_parallel_tasks"
        }
        invalid_status = (
            "status" in update_data and update_data["status"] != "approved"
        )
        if locked_fields.intersection(update_data) or invalid_status:
            raise HTTPException(status_code=409, detail="已有任务的维护窗口不能修改排程约束或取消批准")
    for key, value in update_data.items():
        setattr(window, key, value)
    db.commit()
    db.refresh(window)
    return _window_dict(window)


@router.get("/programs/{program_id}/projects")
def list_projects(program_id: int, db: Session = Depends(get_db)):
    _program_or_404(db, program_id)
    projects = db.query(AopProject).filter(
        AopProject.program_id == program_id
    ).order_by(AopProject.planned_start, AopProject.id).all()
    return {"total": len(projects), "items": [_project_dict(item) for item in projects]}


@router.post("/programs/{program_id}/projects", status_code=201)
def create_project(program_id: int, data: ProjectCreate, db: Session = Depends(get_db)):
    _lock_program(db, program_id)
    values = data.model_dump(exclude={"dependencies"})
    project = AopProject(
        program_id=program_id,
        dependencies=json.dumps(data.dependencies, ensure_ascii=False),
        **values,
    )
    db.add(project)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="AOP 内项目编号必须唯一")
    db.refresh(project)
    return _project_dict(project)


@router.put("/projects/{project_id}")
def update_project(project_id: int, data: ProjectUpdate, db: Session = Depends(get_db)):
    project = _project_or_404(db, project_id)
    _lock_program(db, project.program_id)
    db.refresh(project)
    update_data = data.model_dump(exclude_unset=True)
    dependencies_provided = "dependencies" in update_data
    dependencies = update_data.pop("dependencies", None)
    planned_start = update_data.get("planned_start", project.planned_start)
    planned_end = update_data.get("planned_end", project.planned_end)
    if planned_end and planned_end <= planned_start:
        raise HTTPException(status_code=422, detail="计划结束时间必须晚于计划开始时间")
    if project.task:
        locked_fields = {
            "device_id", "device_name", "planned_start", "planned_end",
            "preferred_window_type", "estimated_hours",
        }
        invalid_approval = (
            "approval_status" in update_data
            and update_data["approval_status"] != "approved"
        )
        invalid_status = (
            "status" in update_data and update_data["status"] != project.status
        )
        if (
            locked_fields.intersection(update_data)
            or dependencies_provided
            or invalid_approval
            or invalid_status
        ):
            raise HTTPException(status_code=409, detail="已排程项目不能修改排程约束、执行状态或取消批准")
    if dependencies is not None:
        if project.project_code in dependencies:
            raise HTTPException(status_code=422, detail="项目不能依赖自身")
        project.dependencies = json.dumps(dependencies, ensure_ascii=False)
    for key, value in update_data.items():
        setattr(project, key, value)
    db.commit()
    db.refresh(project)
    return _project_dict(project)


@router.post("/programs/{program_id}/generate-tasks")
def schedule_program(program_id: int, db: Session = Depends(get_db)):
    try:
        result = generate_aop_tasks(db, program_id)
        db.commit()
        return result
    except AopSchedulingError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/calendar")
def get_calendar(
    program_id: int,
    start_at: datetime,
    end_at: datetime,
    db: Session = Depends(get_db),
):
    if end_at <= start_at:
        raise HTTPException(status_code=422, detail="日历结束时间必须晚于开始时间")
    _program_or_404(db, program_id)
    windows = db.query(AopMaintenanceWindow).filter(
        AopMaintenanceWindow.program_id == program_id,
        AopMaintenanceWindow.start_at < end_at,
        AopMaintenanceWindow.end_at > start_at,
    ).order_by(AopMaintenanceWindow.start_at).all()
    tasks = db.query(MaintenanceTask).join(
        AopProject,
        MaintenanceTask.aop_project_id == AopProject.id,
    ).filter(
        AopProject.program_id == program_id,
        MaintenanceTask.scheduled_date < end_at,
        MaintenanceTask.scheduled_end > start_at,
    ).order_by(MaintenanceTask.scheduled_date).all()
    return {
        "program_id": program_id,
        "start_at": start_at.isoformat(),
        "end_at": end_at.isoformat(),
        "windows": [_window_dict(item) for item in windows],
        "tasks": [
            {
                "id": task.id,
                "task_no": task.task_no,
                "project_id": task.aop_project_id,
                "project_code": task.aop_project.project_code,
                "project_name": task.aop_project.name,
                "device_name": task.device_name,
                "status": task.status,
                "scheduled_date": task.scheduled_date.isoformat(),
                "scheduled_end": task.scheduled_end.isoformat(),
                "maintenance_window_id": task.maintenance_window_id,
            }
            for task in tasks
        ],
    }