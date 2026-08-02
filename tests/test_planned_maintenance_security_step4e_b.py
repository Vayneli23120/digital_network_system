"""Security Step 4E-B3: Planned Maintenance and AOP hardening."""

import inspect
from pathlib import Path

import app.shared.models_jobs  # noqa: F401  Register jobs table in metadata.


def _create_user(db_session, username: str, *, permission=None, superuser=False):
    from app.shared.models import Permission, Role, User

    user = User(
        username=username,
        password_hash="unused",
        is_active=True,
        is_superuser=superuser,
    )
    if permission:
        role = Role(name=f"role-{username}", description="test role")
        permission_record = Permission(
            name=permission,
            resource=permission.split(":", 1)[0],
            action=permission.split(":", 1)[1],
        )
        role.permissions.append(permission_record)
        user.roles.append(role)
        db_session.add_all([role, permission_record])
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _principal(user):
    from app.features.auth.identity import Principal

    return Principal(
        username=user.username,
        user_id=user.id,
        user=user,
        auth_source="test",
    )


def _planned_client(current_user, db):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.features.auth.identity import get_current_principal
    from app.features.auth.router import get_current_user_from_token
    from app.features.planned_maintenance import router as planned_router
    from app.shared.database import get_db

    app = FastAPI()
    app.include_router(planned_router.router)
    app.dependency_overrides[get_current_user_from_token] = lambda: current_user
    app.dependency_overrides[get_db] = lambda: db
    if current_user is not None:
        app.dependency_overrides[get_current_principal] = lambda: _principal(current_user)
    return TestClient(app)


def _enable_auth(monkeypatch):
    from app.shared.config import get_config

    config = get_config()
    monkeypatch.setattr(config.security, "auth_enabled", True)
    monkeypatch.setattr(config.app, "debug", False)


def _assert_matrix(module, expected):
    for dependency_name, function_names in expected.items():
        dependency = getattr(module, dependency_name)
        for function_name in function_names:
            function = getattr(module, function_name)
            parameter = inspect.signature(function).parameters.get("_")
            assert parameter is not None, f"{function_name} missing permission dependency"
            assert parameter.default.dependency is dependency


def test_planned_maintenance_permission_matrix_is_declared():
    from app.features.planned_maintenance import aop_router
    from app.features.planned_maintenance import router as legacy_router

    legacy_expected = {
        "require_planned_read": [
            "list_plans",
            "get_plan",
            "list_tasks",
            "get_task",
            "get_device_maintenance_history",
            "get_stats",
        ],
        "require_planned_write": ["create_plan", "update_plan", "create_task"],
        "require_planned_delete": ["delete_plan", "delete_task"],
        "require_planned_execute": [
            "start_task",
            "complete_task",
            "skip_task",
            "generate_ai_recommended_tasks",
            "generate_predictive_task_for_device",
            "generate_tasks_for_plans",
        ],
    }
    aop_expected = {
        "require_planned_read": [
            "list_programs",
            "get_program",
            "list_windows",
            "list_projects",
            "get_calendar",
        ],
        "require_planned_write": [
            "create_program",
            "update_program",
            "create_window",
            "create_windows_batch",
            "update_window",
            "create_project",
            "update_project",
        ],
        "require_planned_execute": ["schedule_program"],
    }
    assert sum(map(len, legacy_expected.values())) == 17
    assert sum(map(len, aop_expected.values())) == 13
    _assert_matrix(legacy_router, legacy_expected)
    _assert_matrix(aop_router, aop_expected)


def test_planned_maintenance_permission_tiers_are_separated(
    db_session,
    monkeypatch,
):
    _enable_auth(monkeypatch)
    reader = _create_user(
        db_session,
        "planned-reader",
        permission="planned_task:read",
    )
    writer = _create_user(
        db_session,
        "planned-writer",
        permission="planned_task:write",
    )
    executor = _create_user(
        db_session,
        "planned-executor",
        permission="planned_task:execute",
    )
    deleter = _create_user(
        db_session,
        "planned-deleter",
        permission="planned_task:delete",
    )

    with _planned_client(None, db_session) as client:
        assert client.get("/api/planned-maintenance/plans").status_code == 401
    with _planned_client(reader, db_session) as client:
        assert client.get("/api/planned-maintenance/plans").status_code == 200
        assert client.get("/api/planned-maintenance/aop/programs").status_code == 200
        assert client.post(
            "/api/planned-maintenance/tasks/999/start"
        ).status_code == 403
    with _planned_client(writer, db_session) as client:
        assert client.get("/api/planned-maintenance/plans").status_code == 403
        assert client.delete("/api/planned-maintenance/tasks/999").status_code == 403
    with _planned_client(executor, db_session) as client:
        assert client.post("/api/planned-maintenance/tasks/999/start").status_code == 404
        assert client.delete("/api/planned-maintenance/tasks/999").status_code == 403
    with _planned_client(deleter, db_session) as client:
        assert client.delete("/api/planned-maintenance/tasks/999").status_code == 404
        assert client.get("/api/planned-maintenance/plans").status_code == 403


def test_planned_device_names_and_completion_operator_are_server_derived(
    db_session,
    monkeypatch,
):
    from app.shared.models import (
        AopProgram,
        AopProject,
        Device,
        MaintenancePlan,
        MaintenanceRecord,
        MaintenanceTask,
    )

    _enable_auth(monkeypatch)
    device = Device(name="trusted-planned-device", ip="192.0.2.51")
    db_session.add(device)
    db_session.commit()
    writer = _create_user(
        db_session,
        "planned-device-writer",
        permission="planned_task:write",
    )
    executor = _create_user(
        db_session,
        "planned-task-executor",
        permission="planned_task:execute",
    )

    with _planned_client(writer, db_session) as client:
        plan_response = client.post("/api/planned-maintenance/plans", json={
            "name": "trusted plan",
            "device_id": device.id,
            "device_name": "forged-plan-device",
            "plan_type": "routine_check",
            "next_date": "2027-01-01",
        })
        assert plan_response.status_code == 200
        plan_id = plan_response.json()["id"]
        task_response = client.post("/api/planned-maintenance/tasks", json={
            "plan_id": plan_id,
            "device_id": device.id,
            "device_name": "forged-task-device",
            "scheduled_date": "2027-01-02T00:00:00",
        })
        assert task_response.status_code == 200
        task_id = task_response.json()["id"]
        program_response = client.post(
            "/api/planned-maintenance/aop/programs",
            json={"year": 2032, "name": "2032 AOP"},
        )
        assert program_response.status_code == 201
        program_id = program_response.json()["id"]
        project_response = client.post(
            f"/api/planned-maintenance/aop/programs/{program_id}/projects",
            json={
                "project_code": "TRUST-001",
                "name": "trusted project",
                "project_type": "maintenance",
                "device_id": device.id,
                "device_name": "forged-project-device",
                "planned_start": "2032-01-01T00:00:00",
            },
        )
        assert project_response.status_code == 201
        project_id = project_response.json()["id"]

    task = db_session.query(MaintenanceTask).filter(MaintenanceTask.id == task_id).one()
    task.status = "in_progress"
    db_session.commit()
    with _planned_client(executor, db_session) as client:
        assert client.post(
            f"/api/planned-maintenance/tasks/{task_id}/complete",
            json={"description": "completed by principal", "operator": "forged"},
        ).status_code == 422
        completed = client.post(
            f"/api/planned-maintenance/tasks/{task_id}/complete",
            json={"description": "completed by principal"},
        )
        assert completed.status_code == 200

    db_session.expire_all()
    plan = db_session.query(MaintenancePlan).filter(MaintenancePlan.id == plan_id).one()
    task = db_session.query(MaintenanceTask).filter(MaintenanceTask.id == task_id).one()
    project = db_session.query(AopProject).filter(AopProject.id == project_id).one()
    maintenance = db_session.query(MaintenanceRecord).filter(
        MaintenanceRecord.id == task.maintenance_id
    ).one()
    assert plan.device_name == device.name
    assert task.device_name == device.name
    assert project.device_name == device.name
    assert maintenance.operator == executor.username
    assert db_session.query(AopProgram).filter(AopProgram.id == program_id).one()


def test_planned_models_and_query_bounds_reject_unsafe_input(
    db_session,
    monkeypatch,
):
    _enable_auth(monkeypatch)
    writer = _create_user(
        db_session,
        "planned-input-writer",
        permission="planned_task:write",
    )
    reader = _create_user(
        db_session,
        "planned-input-reader",
        permission="planned_task:read",
    )
    executor = _create_user(
        db_session,
        "planned-input-executor",
        permission="planned_task:execute",
    )

    with _planned_client(writer, db_session) as client:
        assert client.post("/api/planned-maintenance/plans", json={
            "name": "invalid",
            "plan_type": "invalid",
            "next_date": "not-a-date",
        }).status_code == 422
        assert client.post("/api/planned-maintenance/plans", json={
            "name": "invalid extra",
            "plan_type": "routine_check",
            "next_date": "2027-01-01",
            "status": "completed",
        }).status_code == 422
        assert client.post("/api/planned-maintenance/aop/programs", json={
            "year": 2033,
            "name": "invalid extra",
            "created_by": "forged",
        }).status_code == 422
    with _planned_client(reader, db_session) as client:
        assert client.get("/api/planned-maintenance/plans?skip=-1").status_code == 422
        assert client.get("/api/planned-maintenance/tasks?limit=501").status_code == 422
        assert client.get(
            "/api/planned-maintenance/devices/999/maintenance-history?limit=101"
        ).status_code == 422
    with _planned_client(executor, db_session) as client:
        assert client.post(
            "/api/planned-maintenance/devices/999/predictive-task?days_offset=-1"
        ).status_code == 422
        assert client.post(
            "/api/planned-maintenance/generate-ai-tasks",
            json={"min_health_score": 101},
        ).status_code == 422


def test_planned_errors_are_redacted_and_sessions_are_dependency_managed(
    db_session,
    monkeypatch,
):
    from app.features.planned_maintenance import aop_router
    from app.features.planned_maintenance.aop_service import AopSchedulingError

    _enable_auth(monkeypatch)
    executor = _create_user(
        db_session,
        "planned-error-executor",
        permission="planned_task:execute",
    )
    secret_detail = r"database failed at C:\private\aop.db"

    monkeypatch.setattr(
        aop_router,
        "generate_aop_tasks",
        lambda *_args: (_ for _ in ()).throw(AopSchedulingError(secret_detail)),
    )
    with _planned_client(executor, db_session) as client:
        response = client.post(
            "/api/planned-maintenance/aop/programs/999/generate-tasks"
        )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "AOP 排程失败，请检查批准状态、项目依赖和维护窗口"
    )
    assert secret_detail not in response.text

    root = Path(__file__).resolve().parents[1]
    router_source = (
        root / "app/features/planned_maintenance/router.py"
    ).read_text(encoding="utf-8")
    layout_source = (
        root / "frontend/src/views/Layout.vue"
    ).read_text(encoding="utf-8")
    legacy_source = (
        root / "frontend/src/views/PlannedMaintenance.vue"
    ).read_text(encoding="utf-8")
    aop_source = (
        root / "frontend/src/components/AopPlanningWorkspace.vue"
    ).read_text(encoding="utf-8")
    assert "next(get_db())" not in router_source
    assert "...planForm.value" not in legacy_source
    assert "updateMaintenancePlan(planForm.value.id, planForm.value)" not in legacy_source
    assert "const payload = { ...projectForm.value" not in aop_source
    assert "const payload = { ...windowForm.value" not in aop_source
    planned_menu = next(
        line
        for line in layout_source.splitlines()
        if "path: '/planned-maintenance'" in line
    )
    assert "permission: 'planned_task:read'" in planned_menu