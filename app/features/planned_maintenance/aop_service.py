"""Deterministic scheduling for annual operating plan maintenance work."""

import json
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy.orm import Session

from app.shared.models import (
    AopMaintenanceWindow,
    AopProgram,
    AopProject,
    MaintenanceTask,
)


class AopSchedulingError(ValueError):
    """Raised when an AOP project cannot be placed in an approved window."""


class AopDependencyNotScheduledError(AopSchedulingError):
    """Raised when a project must wait for another project in the same run."""


def _window_local_now(window: AopMaintenanceWindow, now: Optional[datetime]) -> datetime:
    try:
        window_zone = ZoneInfo(window.timezone)
    except ZoneInfoNotFoundError as exc:
        raise AopSchedulingError(f"维护窗口时区无效: {window.timezone}") from exc
    if now is None:
        return datetime.now(window_zone).replace(tzinfo=None)
    if now.tzinfo is None:
        return now
    return now.astimezone(window_zone).replace(tzinfo=None)


def _dependency_codes(project: AopProject) -> List[str]:
    if not project.dependencies:
        return []
    try:
        value = json.loads(project.dependencies)
    except (TypeError, json.JSONDecodeError) as exc:
        raise AopSchedulingError("项目依赖必须是 JSON 数组") from exc

    if isinstance(value, dict):
        value = value.get("project_codes", [])
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise AopSchedulingError("项目依赖必须是项目编号数组")
    return list(dict.fromkeys(code.strip() for code in value if code.strip()))


def _dependency_end(db: Session, project: AopProject) -> Optional[datetime]:
    latest_end = None
    for project_code in _dependency_codes(project):
        dependency = db.query(AopProject).filter(
            AopProject.program_id == project.program_id,
            AopProject.project_code == project_code,
        ).first()
        if dependency is None:
            raise AopSchedulingError(f"依赖项目不存在: {project_code}")
        if dependency.id == project.id:
            raise AopSchedulingError("项目不能依赖自身")
        if dependency.task is None or dependency.task.scheduled_end is None:
            raise AopDependencyNotScheduledError(f"依赖项目尚未排程: {project_code}")
        if latest_end is None or dependency.task.scheduled_end > latest_end:
            latest_end = dependency.task.scheduled_end
    return latest_end


def _find_slot(
    db: Session,
    project: AopProject,
    window: AopMaintenanceWindow,
    dependency_end: Optional[datetime],
) -> Optional[Tuple[datetime, datetime]]:
    hours = float(project.estimated_hours or Decimal("1"))
    if hours <= 0:
        raise AopSchedulingError("预计工时必须大于 0")

    duration = timedelta(hours=hours)
    candidate_start = max(
        value
        for value in (project.planned_start, window.start_at, dependency_end)
        if value is not None
    )

    while candidate_start + duration <= window.end_at:
        candidate_end = candidate_start + duration
        if project.planned_end and candidate_end > project.planned_end:
            return None

        overlaps = db.query(MaintenanceTask).filter(
            MaintenanceTask.maintenance_window_id == window.id,
            MaintenanceTask.status != "skipped",
            MaintenanceTask.scheduled_date < candidate_end,
            MaintenanceTask.scheduled_end > candidate_start,
        ).order_by(MaintenanceTask.scheduled_end).all()
        blocked_until = None
        boundaries = sorted(
            {candidate_start}
            | {
                task.scheduled_date
                for task in overlaps
                if candidate_start < task.scheduled_date < candidate_end
            }
        )
        for boundary in boundaries:
            active = [
                task
                for task in overlaps
                if task.scheduled_date <= boundary < task.scheduled_end
            ]
            if len(active) >= window.max_parallel_tasks:
                blocked_until = min(task.scheduled_end for task in active)
                break

        if blocked_until is None:
            return candidate_start, candidate_end

        if blocked_until <= candidate_start:
            return None
        candidate_start = blocked_until

    return None


def schedule_aop_project(
    db: Session,
    project: AopProject,
    *,
    now: Optional[datetime] = None,
) -> MaintenanceTask:
    """Schedule one approved project into its earliest eligible approved window."""
    if project.task is not None:
        return project.task
    if project.approval_status != "approved":
        raise AopSchedulingError("项目尚未批准")

    program = db.query(AopProgram).filter(AopProgram.id == project.program_id).first()
    if program is None or program.status not in ("approved", "active"):
        raise AopSchedulingError("AOP 尚未批准或启用")

    dependency_end = _dependency_end(db, project)
    query = db.query(AopMaintenanceWindow).filter(
        AopMaintenanceWindow.program_id == project.program_id,
        AopMaintenanceWindow.status == "approved",
        AopMaintenanceWindow.end_at > project.planned_start,
    )
    if project.preferred_window_type:
        query = query.filter(
            AopMaintenanceWindow.window_type == project.preferred_window_type
        )

    for window in query.order_by(AopMaintenanceWindow.start_at, AopMaintenanceWindow.id):
        slot = _find_slot(db, project, window, dependency_end)
        if slot is None:
            continue
        scheduled_start, scheduled_end = slot
        current_time = _window_local_now(window, now)
        task = MaintenanceTask(
            aop_project=project,
            maintenance_window=window,
            device_id=project.device_id,
            device_name=project.device_name,
            task_no=f"AOP-{program.year}-{project.id:05d}",
            scheduled_date=scheduled_start,
            scheduled_end=scheduled_end,
            estimated_hours=project.estimated_hours,
            schedule_source="aop",
            status="overdue" if scheduled_start < current_time else "pending",
            notes=json.dumps(
                {
                    "aop_generated": True,
                    "project_code": project.project_code,
                    "window_type": window.window_type,
                },
                ensure_ascii=False,
            ),
        )
        db.add(task)
        db.flush()
        project.status = "scheduled"
        return task

    raise AopSchedulingError("没有满足日期、类型、工时和容量约束的已批准维护窗口")


def generate_aop_tasks(db: Session, program_id: int) -> Dict[str, object]:
    """Generate at most one task for each approved project in an AOP."""
    program = db.query(AopProgram).filter(
        AopProgram.id == program_id
    ).with_for_update().first()
    if program is None:
        raise AopSchedulingError("AOP 不存在")

    projects = db.query(AopProject).filter(
        AopProject.program_id == program_id,
        AopProject.approval_status == "approved",
    ).order_by(AopProject.planned_start, AopProject.id).all()

    generated = []
    existing = []
    skipped = []
    pending = list(projects)
    while pending:
        deferred = []
        generated_this_pass = 0
        for project in pending:
            if project.task is not None:
                existing.append(project.task.id)
                continue
            try:
                task = schedule_aop_project(db, project)
                generated.append(task.id)
                generated_this_pass += 1
            except AopDependencyNotScheduledError as exc:
                deferred.append((project, str(exc)))
            except AopSchedulingError as exc:
                skipped.append({"project_id": project.id, "reason": str(exc)})

        if not deferred:
            break
        if generated_this_pass == 0:
            skipped.extend(
                {"project_id": project.id, "reason": reason}
                for project, reason in deferred
            )
            break
        pending = [project for project, _ in deferred]

    return {
        "program_id": program_id,
        "generated_task_ids": generated,
        "existing_task_ids": existing,
        "skipped": skipped,
    }