"""Tests for annual AOP planning and deterministic maintenance scheduling."""

import json
from datetime import datetime, timezone

import pytest

from app.features.planned_maintenance import router as legacy_router
from app.features.planned_maintenance.aop_router import (
    ProgramCreate,
    ProgramUpdate,
    ProjectCreate,
    ProjectUpdate,
    WindowBatchCreate,
    WindowCreate,
    WindowUpdate,
    create_program,
    create_project,
    create_window,
    create_windows_batch,
    list_projects,
    list_windows,
    schedule_program,
    update_project,
    update_program,
    update_window,
)
from fastapi import HTTPException
from app.features.planned_maintenance.aop_service import (
    generate_aop_tasks,
    schedule_aop_project,
)
from app.shared.models import (
    AopMaintenanceWindow,
    AopProgram,
    AopProject,
    MaintenancePlan,
    MaintenanceTask,
)


def _program(db_session, *, status="approved"):
    program = AopProgram(year=2027, version=1, name="2027 Network AOP", status=status)
    db_session.add(program)
    db_session.flush()
    return program


def _window(
    db_session,
    program,
    *,
    start_hour=0,
    end_hour=8,
    window_type="shutdown",
    status="approved",
    max_parallel_tasks=1,
):
    window = AopMaintenanceWindow(
        program_id=program.id,
        name="Spring Festival Shutdown",
        window_type=window_type,
        start_at=datetime(2027, 2, 8, start_hour),
        end_at=datetime(2027, 2, 8, end_hour),
        status=status,
        max_parallel_tasks=max_parallel_tasks,
    )
    db_session.add(window)
    db_session.flush()
    return window


def _project(
    db_session,
    program,
    code,
    *,
    estimated_hours=2,
    approval_status="approved",
    dependencies=None,
    preferred_window_type="shutdown",
):
    project = AopProject(
        program_id=program.id,
        project_code=code,
        name=f"Project {code}",
        project_type="upgrade",
        planned_start=datetime(2027, 1, 1),
        preferred_window_type=preferred_window_type,
        estimated_hours=estimated_hours,
        approval_status=approval_status,
        dependencies=json.dumps(dependencies or []),
    )
    db_session.add(project)
    db_session.flush()
    return project


def test_aop_models_are_additive_to_legacy_plans(db_session):
    legacy = MaintenancePlan(
        name="Legacy monthly check",
        plan_type="routine_check",
        next_date=datetime(2027, 1, 1),
    )
    program = _program(db_session)
    db_session.add(legacy)
    db_session.flush()

    assert db_session.query(MaintenancePlan).one() is legacy
    assert db_session.query(AopProgram).one() is program


def test_scheduler_requires_approved_program_project_and_window(db_session):
    program = _program(db_session, status="draft")
    _window(db_session, program)
    project = _project(db_session, program, "NET-001")

    result = generate_aop_tasks(db_session, program.id)

    assert result["generated_task_ids"] == []
    assert result["skipped"] == [
        {"project_id": project.id, "reason": "AOP 尚未批准或启用"}
    ]
    assert db_session.query(MaintenanceTask).count() == 0


def test_scheduler_packs_tasks_with_capacity_and_dependency_order(db_session):
    program = _program(db_session)
    window = _window(db_session, program)
    first = _project(db_session, program, "NET-001")
    second = _project(
        db_session,
        program,
        "NET-002",
        dependencies=["NET-001"],
    )

    result = generate_aop_tasks(db_session, program.id)
    tasks = db_session.query(MaintenanceTask).order_by(MaintenanceTask.scheduled_date).all()

    assert result["skipped"] == []
    assert len(tasks) == 2
    assert tasks[0].aop_project_id == first.id
    assert tasks[0].scheduled_date == window.start_at
    assert tasks[0].scheduled_end == datetime(2027, 2, 8, 2)
    assert tasks[1].aop_project_id == second.id
    assert tasks[1].scheduled_date == tasks[0].scheduled_end
    assert tasks[1].scheduled_end == datetime(2027, 2, 8, 4)


def test_scheduler_resolves_dependencies_regardless_of_project_order(db_session):
    program = _program(db_session)
    _window(db_session, program)
    dependent = _project(
        db_session,
        program,
        "NET-002",
        dependencies=["NET-001"],
    )
    prerequisite = _project(db_session, program, "NET-001")

    result = generate_aop_tasks(db_session, program.id)

    assert result["skipped"] == []
    assert len(result["generated_task_ids"]) == 2
    assert prerequisite.task.scheduled_end == dependent.task.scheduled_date


def test_scheduler_uses_peak_concurrency_for_window_capacity(db_session):
    program = _program(db_session)
    window = _window(db_session, program, max_parallel_tasks=2)
    candidate = _project(db_session, program, "NET-003", estimated_hours=2)
    db_session.add_all([
        MaintenanceTask(
            maintenance_window=window,
            task_no="EXISTING-001",
            scheduled_date=window.start_at,
            scheduled_end=datetime(2027, 2, 8, 1),
            status="pending",
        ),
        MaintenanceTask(
            maintenance_window=window,
            task_no="EXISTING-002",
            scheduled_date=datetime(2027, 2, 8, 1),
            scheduled_end=datetime(2027, 2, 8, 2),
            status="pending",
        ),
    ])
    db_session.flush()
    assert db_session.query(MaintenanceTask).filter(
        MaintenanceTask.maintenance_window_id == window.id
    ).count() == 2

    result = generate_aop_tasks(db_session, program.id)

    assert result["skipped"] == []
    assert candidate.task.scheduled_date == window.start_at
    assert candidate.task.scheduled_end == datetime(2027, 2, 8, 2)


def test_scheduler_compares_overdue_status_in_window_timezone(db_session):
    program = _program(db_session)
    _window(db_session, program)
    project = _project(db_session, program, "NET-001")

    task = schedule_aop_project(
        db_session,
        project,
        now=datetime(2027, 2, 7, 17, tzinfo=timezone.utc),
    )

    assert task.status == "overdue"


def test_scheduler_is_idempotent_and_rejects_work_that_does_not_fit(db_session):
    program = _program(db_session)
    _window(db_session, program)
    fitting = _project(db_session, program, "NET-001")
    too_long = _project(db_session, program, "NET-002", estimated_hours=10)

    first = generate_aop_tasks(db_session, program.id)
    second = generate_aop_tasks(db_session, program.id)

    assert len(first["generated_task_ids"]) == 1
    assert first["skipped"][0]["project_id"] == too_long.id
    assert second["generated_task_ids"] == []
    assert second["existing_task_ids"] == [fitting.task.id]
    assert db_session.query(MaintenanceTask).count() == 1


def test_scheduled_work_rejects_updates_that_invalidate_execution(db_session):
    program = _program(db_session)
    window = _window(db_session, program)
    project = _project(db_session, program, "NET-001")
    generate_aop_tasks(db_session, program.id)

    with pytest.raises(HTTPException) as project_error:
        update_project(
            project.id,
            ProjectUpdate(approval_status="rejected"),
            db_session,
        )
    with pytest.raises(HTTPException) as window_error:
        update_window(
            window.id,
            WindowUpdate(status="cancelled"),
            db_session,
        )
    with pytest.raises(HTTPException) as program_error:
        update_program(
            program.id,
            ProgramUpdate(status="draft"),
            db_session,
        )

    assert project_error.value.status_code == 409
    assert window_error.value.status_code == 409
    assert program_error.value.status_code == 409


@pytest.mark.asyncio
async def test_aop_api_generated_task_uses_legacy_execution_flow(db_session):
    program_data = create_program(
        ProgramCreate(year=2028, name="2028 Network AOP", status="approved"),
        db_session,
    )
    program_id = program_data["id"]
    create_window(
        program_id,
        WindowCreate(
            name="National Holiday Window",
            window_type="holiday",
            start_at=datetime(2028, 10, 1, 0),
            end_at=datetime(2028, 10, 1, 8),
            status="approved",
        ),
        db_session,
    )
    create_project(
        program_id,
        ProjectCreate(
            project_code="NET-2028-001",
            name="Core switch software upgrade",
            project_type="upgrade",
            planned_start=datetime(2028, 9, 1),
            preferred_window_type="holiday",
            estimated_hours=2,
            approval_status="approved",
            rollback_plan="Restore previous image and reload standby core",
        ),
        db_session,
    )

    generated = schedule_program(program_id, db_session)
    task_id = generated["generated_task_ids"][0]
    detail = await legacy_router.get_task(task_id, db_session)

    assert detail["schedule_source"] == "aop"
    assert detail["aop_project"]["project_code"] == "NET-2028-001"
    assert detail["maintenance_window"]["window_type"] == "holiday"
    assert detail["scheduled_end"] == "2028-10-01T02:00:00"

    await legacy_router.start_task(task_id, db_session)
    await legacy_router.complete_task(task_id, None, db_session)
    project = list_projects(program_id, db_session)["items"][0]

    assert project["status"] == "completed"
    assert project["task"]["status"] == "completed"


@pytest.mark.asyncio
async def test_aop_completion_rolls_up_execution_results(db_session):
    program_data = create_program(
        ProgramCreate(year=2029, name="2029 Network AOP", status="approved"),
        db_session,
    )
    program_id = program_data["id"]
    create_window(
        program_id,
        WindowCreate(
            name="Spring Shutdown",
            window_type="shutdown",
            start_at=datetime(2029, 2, 1, 0),
            end_at=datetime(2029, 2, 1, 8),
            status="approved",
        ),
        db_session,
    )
    create_project(
        program_id,
        ProjectCreate(
            project_code="NET-2029-001",
            name="Access switch replacement",
            project_type="replacement",
            planned_start=datetime(2029, 1, 1),
            preferred_window_type="shutdown",
            estimated_hours=3,
            approval_status="approved",
        ),
        db_session,
    )

    generated = schedule_program(program_id, db_session)
    task_id = generated["generated_task_ids"][0]
    await legacy_router.start_task(task_id, db_session)
    await legacy_router.complete_task(
        task_id,
        {
            "labor_hours": 2.5,
            "parts_cost": 1200,
            "labor_cost": 800,
            "completion_result": "success",
            "completion_notes": "Replaced access switch, verified uplinks",
        },
        db_session,
    )

    project = list_projects(program_id, db_session)["items"][0]

    assert project["status"] == "completed"
    assert project["actual_hours"] == 2.5
    assert project["actual_cost"] == 2000.0
    assert project["completion_result"] == "success"
    assert project["completion_notes"] == "Replaced access switch, verified uplinks"
    assert project["completed_at"] is not None


def test_batch_window_import_creates_all_windows(db_session):
    program_data = create_program(
        ProgramCreate(year=2030, name="2030 Network AOP", status="approved"),
        db_session,
    )
    program_id = program_data["id"]

    result = create_windows_batch(
        program_id,
        WindowBatchCreate(
            windows=[
                WindowCreate(
                    name="National Day",
                    window_type="holiday",
                    start_at=datetime(2030, 10, 1, 0),
                    end_at=datetime(2030, 10, 2, 0),
                    status="approved",
                ),
                WindowCreate(
                    name="Spring Shutdown",
                    window_type="shutdown",
                    start_at=datetime(2030, 2, 1, 0),
                    end_at=datetime(2030, 2, 8, 0),
                    status="approved",
                ),
            ]
        ),
        db_session,
    )

    assert result["created"] == 2
    windows = list_windows(program_id, db_session)["items"]
    assert len(windows) == 2
    assert windows[0]["start_at"] <= windows[1]["start_at"]
