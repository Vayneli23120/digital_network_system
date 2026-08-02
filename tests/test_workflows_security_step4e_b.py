"""Security Step 4E-B4: Workflow RBAC, inputs, actors, and execution results."""

import inspect
import importlib
import asyncio
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
    permissions = (
        [permission]
        if isinstance(permission, str)
        else list(permission or [])
    )
    if permissions:
        role = Role(name=f"role-{username}", description="test role")
        new_permission_records = []
        for permission_name in permissions:
            permission_record = db_session.query(Permission).filter(
                Permission.name == permission_name
            ).first()
            if permission_record is None:
                permission_record = Permission(
                    name=permission_name,
                    resource=permission_name.split(":", 1)[0],
                    action=permission_name.split(":", 1)[1],
                )
                new_permission_records.append(permission_record)
            role.permissions.append(permission_record)
        user.roles.append(role)
        db_session.add_all([role, *new_permission_records])
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


def _workflow_client(current_user, db):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.features.auth.identity import get_current_principal
    from app.features.auth.router import get_current_user_from_token
    from app.shared.database import get_db

    workflow_router = importlib.import_module("app.features.workflows.router")
    app = FastAPI()
    app.include_router(workflow_router.router)
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


def _rule_payload(name="test workflow"):
    return {
        "name": name,
        "description": "bounded workflow rule",
        "trigger_type": "fault_created",
        "trigger_conditions": {"fault_severity": "critical"},
        "action_type": "log_event",
        "action_config": {"event_type": "test", "message": "matched"},
        "priority": 100,
        "is_active": True,
    }


def test_workflow_permission_matrix_is_declared():
    workflow_router = importlib.import_module("app.features.workflows.router")
    from app.services.workflow.executor import ACTION_REQUIRED_PERMISSIONS

    expected = {
        "require_workflow_read": [
            "list_rules",
            "get_rule",
            "get_workflow_stats",
            "list_triggers",
            "list_actions",
        ],
        "require_workflow_write": [
            "create_rule",
            "update_rule",
            "toggle_rule",
            "init_default_rules",
        ],
        "require_workflow_delete": ["delete_rule"],
        "require_workflow_trigger": [
            "trigger_workflow",
            "trigger_fault_workflow",
            "trigger_health_workflow",
            "trigger_maintenance_workflow",
        ],
    }
    assert sum(map(len, expected.values())) == 14
    assert ACTION_REQUIRED_PERMISSIONS == {
        "create_maintenance": "maintenance:write",
        "create_pm_task": "planned_task:write",
        "update_health_score": "device:write",
    }
    for dependency_name, function_names in expected.items():
        dependency = getattr(workflow_router, dependency_name)
        for function_name in function_names:
            function = getattr(workflow_router, function_name)
            parameter = inspect.signature(function).parameters.get("_")
            assert parameter is not None, f"{function_name} missing permission dependency"
            assert parameter.default.dependency is dependency


def test_workflow_permission_tiers_are_separated(db_session, monkeypatch):
    _enable_auth(monkeypatch)
    reader = _create_user(db_session, "workflow-reader", permission="workflow:read")
    writer = _create_user(db_session, "workflow-writer", permission="workflow:write")
    triggerer = _create_user(
        db_session,
        "workflow-triggerer",
        permission="workflow:trigger",
    )
    deleter = _create_user(
        db_session,
        "workflow-deleter",
        permission="workflow:delete",
    )

    with _workflow_client(None, db_session) as client:
        assert client.get("/api/workflows/rules").status_code == 401
    with _workflow_client(reader, db_session) as client:
        assert client.get("/api/workflows/rules").status_code == 200
        assert client.get("/api/workflows/actions").status_code == 200
        assert client.post("/api/workflows/rules", json=_rule_payload()).status_code == 403
    with _workflow_client(writer, db_session) as client:
        created = client.post("/api/workflows/rules", json=_rule_payload())
        assert created.status_code == 200
        rule_id = created.json()["rule_id"]
        assert client.get("/api/workflows/rules").status_code == 403
        assert client.delete(f"/api/workflows/rules/{rule_id}").status_code == 403
    with _workflow_client(triggerer, db_session) as client:
        assert client.post(
            "/api/workflows/trigger/fault",
            json={"fault_id": 999999},
        ).status_code == 200
        assert client.patch(f"/api/workflows/rules/{rule_id}/toggle").status_code == 403
    with _workflow_client(deleter, db_session) as client:
        assert client.delete(f"/api/workflows/rules/{rule_id}").status_code == 200
        assert client.get("/api/workflows/rules").status_code == 403


def test_workflow_trigger_actor_is_persisted_on_created_maintenance(
    db_session,
    monkeypatch,
):
    from app.shared.models import Device, FaultRecord, MaintenanceRecord

    _enable_auth(monkeypatch)
    device = Device(name="workflow-actor-device", ip="192.0.2.61")
    db_session.add(device)
    db_session.flush()
    fault = FaultRecord(
        device_id=device.id,
        device_name=device.name,
        fault_no="FAULT-WORKFLOW-ACTOR",
        status="open",
        severity="critical",
        description="workflow actor test",
    )
    db_session.add(fault)
    db_session.commit()
    writer = _create_user(
        db_session,
        "workflow-actor-writer",
        permission=["workflow:write", "maintenance:write"],
    )
    restricted_triggerer = _create_user(
        db_session,
        "restricted-workflow-triggerer",
        permission="workflow:trigger",
    )
    triggerer = _create_user(
        db_session,
        "trusted-workflow-triggerer",
        permission=["workflow:trigger", "maintenance:write"],
    )
    payload = _rule_payload("actor workflow")
    payload["action_type"] = "create_maintenance"
    payload["action_config"] = {
        "maint_type": "emergency",
        "priority": "P1",
        "title_template": "Workflow: {device_name}",
        "description": "created by workflow",
    }

    with _workflow_client(writer, db_session) as client:
        assert client.post("/api/workflows/rules", json=payload).status_code == 200
    with _workflow_client(restricted_triggerer, db_session) as client:
        denied = client.post(
            "/api/workflows/trigger/fault",
            json={"fault_id": fault.id},
        )
    assert denied.status_code == 403
    assert denied.json()["detail"] == (
        "工作流动作需要目标域权限: maintenance:write"
    )
    assert db_session.query(MaintenanceRecord).count() == 0

    with _workflow_client(triggerer, db_session) as client:
        response = client.post(
            "/api/workflows/trigger/fault",
            json={"fault_id": fault.id},
        )

    assert response.status_code == 200
    assert response.json()["success"] is True
    maintenance = db_session.query(MaintenanceRecord).filter(
        MaintenanceRecord.fault_id == fault.id
    ).one()
    assert maintenance.operator == triggerer.username


def test_workflow_health_mutation_requires_device_write_and_is_audited(
    db_session,
    monkeypatch,
):
    from app.shared.models import AuditLog, Device

    _enable_auth(monkeypatch)
    device = Device(
        name="workflow-health-device",
        ip="192.0.2.62",
        health_score=40,
    )
    db_session.add(device)
    db_session.commit()
    writer = _create_user(
        db_session,
        "workflow-health-writer",
        permission=["workflow:write", "device:write"],
    )
    restricted = _create_user(
        db_session,
        "workflow-health-restricted",
        permission="workflow:trigger",
    )
    authorized = _create_user(
        db_session,
        "workflow-health-authorized",
        permission=["workflow:trigger", "device:write"],
    )
    payload = _rule_payload("health audit workflow")
    payload.update({
        "trigger_type": "device_health_low",
        "trigger_conditions": {"health_score": {"<": 60}},
        "action_type": "update_health_score",
        "action_config": {"adjustment": 10, "reason": "workflow test"},
    })

    with _workflow_client(writer, db_session) as client:
        assert client.post("/api/workflows/rules", json=payload).status_code == 200
    with _workflow_client(restricted, db_session) as client:
        assert client.post(
            "/api/workflows/trigger/health",
            json={"device_id": device.id},
        ).status_code == 403
    db_session.refresh(device)
    assert device.health_score == 40

    with _workflow_client(authorized, db_session) as client:
        response = client.post(
            "/api/workflows/trigger/health",
            json={"device_id": device.id},
        )
    assert response.status_code == 200
    assert response.json()["success"] is True
    db_session.refresh(device)
    assert device.health_score == 50
    audit = db_session.query(AuditLog).filter(
        AuditLog.target_type == "device",
        AuditLog.target_id == device.id,
    ).one()
    assert audit.operator == authorized.username
    assert audit.action == "workflow.update_health_score"


def test_workflow_rule_definitions_require_target_domain_permissions(
    db_session,
    monkeypatch,
):
    _enable_auth(monkeypatch)
    restricted = _create_user(
        db_session,
        "workflow-definition-restricted",
        permission="workflow:write",
    )
    authorized = _create_user(
        db_session,
        "workflow-definition-authorized",
        permission=["workflow:write", "maintenance:write"],
    )
    payload = _rule_payload("privileged definition")
    payload.update({
        "action_type": "create_maintenance",
        "action_config": {"maint_type": "corrective", "priority": "P3"},
    })

    with _workflow_client(restricted, db_session) as client:
        denied_create = client.post("/api/workflows/rules", json=payload)
    assert denied_create.status_code == 403
    assert denied_create.json()["detail"] == (
        "工作流动作需要目标域权限: maintenance:write"
    )

    with _workflow_client(authorized, db_session) as client:
        created = client.post("/api/workflows/rules", json=payload)
        assert created.status_code == 200
        rule_id = created.json()["rule_id"]

    with _workflow_client(restricted, db_session) as client:
        assert client.put(
            f"/api/workflows/rules/{rule_id}",
            json={"description": "unauthorized edit"},
        ).status_code == 403
        assert client.patch(f"/api/workflows/rules/{rule_id}/toggle").status_code == 403
        assert client.post("/api/workflows/init-defaults").status_code == 403


def test_user_originated_fault_workflow_respects_target_permissions(db_session):
    from app.features.faults import router as faults_router
    from app.services.workflow.rule_engine import RuleEngine
    from app.shared.models import Device, FaultRecord, MaintenanceRecord

    device = Device(name="fault-workflow-auth-device", ip="192.0.2.63")
    db_session.add(device)
    db_session.flush()
    denied_fault = FaultRecord(
        device_id=device.id,
        device_name=device.name,
        fault_no="FAULT-WORKFLOW-DENIED",
        status="open",
        severity="critical",
        description="denied automatic action",
    )
    allowed_fault = FaultRecord(
        device_id=device.id,
        device_name=device.name,
        fault_no="FAULT-WORKFLOW-ALLOWED",
        status="open",
        severity="critical",
        description="allowed automatic action",
    )
    db_session.add_all([denied_fault, allowed_fault])
    db_session.commit()
    RuleEngine(db_session).create_rule(
        name="fault target permission rule",
        trigger_type="fault_created",
        trigger_conditions={"fault_severity": "critical"},
        action_type="create_maintenance",
        action_config={"maint_type": "emergency", "priority": "P1"},
    )
    restricted = _create_user(
        db_session,
        "fault-workflow-restricted",
        permission="fault:write",
    )
    authorized = _create_user(
        db_session,
        "fault-workflow-authorized",
        permission=["fault:write", "maintenance:write"],
    )

    denied = asyncio.run(faults_router._run_fault_workflow(
        db_session,
        denied_fault.id,
        restricted.username,
        restricted.id,
    ))
    allowed = asyncio.run(faults_router._run_fault_workflow(
        db_session,
        allowed_fault.id,
        authorized.username,
        authorized.id,
    ))

    assert denied is None
    assert allowed.success is True
    assert db_session.query(MaintenanceRecord).filter(
        MaintenanceRecord.fault_id == denied_fault.id
    ).count() == 0
    maintenance = db_session.query(MaintenanceRecord).filter(
        MaintenanceRecord.fault_id == allowed_fault.id
    ).one()
    assert maintenance.operator == authorized.username


def test_workflow_inputs_are_strict_bounded_and_paginated(db_session, monkeypatch):
    from app.services.workflow.rule_engine import RuleEngine

    _enable_auth(monkeypatch)
    writer = _create_user(db_session, "workflow-input-writer", permission="workflow:write")
    reader = _create_user(db_session, "workflow-input-reader", permission="workflow:read")
    triggerer = _create_user(
        db_session,
        "workflow-input-triggerer",
        permission="workflow:trigger",
    )
    with _workflow_client(writer, db_session) as client:
        unknown_trigger = _rule_payload("unknown trigger")
        unknown_trigger["trigger_type"] = "arbitrary"
        assert client.post("/api/workflows/rules", json=unknown_trigger).status_code == 422

        unknown_action = _rule_payload("unknown action")
        unknown_action["action_type"] = "shell"
        assert client.post("/api/workflows/rules", json=unknown_action).status_code == 422

        unknown_operator = _rule_payload("unknown operator")
        unknown_operator["trigger_conditions"] = {"health_score": {"execute": 1}}
        assert client.post("/api/workflows/rules", json=unknown_operator).status_code == 422

        unsafe_config = _rule_payload("unsafe config")
        unsafe_config["action_type"] = "create_pm_task"
        unsafe_config["action_config"] = {"days_offset": 100_000}
        assert client.post("/api/workflows/rules", json=unsafe_config).status_code == 422

        oversized = _rule_payload("oversized")
        oversized["trigger_conditions"] = {"message": "x" * 100_001}
        assert client.post("/api/workflows/rules", json=oversized).status_code == 422

        extra = _rule_payload("extra")
        extra["created_by"] = "forged"
        assert client.post("/api/workflows/rules", json=extra).status_code == 422

        valid = client.post("/api/workflows/rules", json=_rule_payload("valid update"))
        assert valid.status_code == 200
        assert client.put(
            f"/api/workflows/rules/{valid.json()['rule_id']}",
            json={"action_type": "send_alert"},
        ).status_code == 422

    with _workflow_client(triggerer, db_session) as client:
        assert client.post("/api/workflows/trigger", json={
            "trigger_type": "fault_created",
            "event_data": {"device_id": 1},
        }).status_code == 422
        assert client.post("/api/workflows/trigger", json={
            "trigger_type": "scheduled_check",
            "event_data": {"check_type": "x" * 51},
        }).status_code == 422

    engine = RuleEngine(db_session)
    for index in range(2):
        engine.create_rule(
            name=f"pagination-{index}",
            trigger_type="scheduled_check",
            trigger_conditions={},
            action_type="log_event",
            action_config={},
        )
    with _workflow_client(reader, db_session) as client:
        response = client.get("/api/workflows/rules?limit=1")
        assert response.status_code == 200
        assert response.json()["total"] == 3
        assert len(response.json()["rules"]) == 1
        assert client.get("/api/workflows/rules?skip=-1").status_code == 422
        assert client.get("/api/workflows/rules?limit=501").status_code == 422


def test_workflow_action_failures_set_overall_failure(db_session, monkeypatch):
    from app.shared.models import WorkflowRule

    _enable_auth(monkeypatch)
    triggerer = _create_user(
        db_session,
        "workflow-failure-triggerer",
        permission=["workflow:trigger", "maintenance:write"],
    )
    rule = WorkflowRule(
        name="expected action failure",
        trigger_type="scheduled_check",
        trigger_conditions="{}",
        action_type="create_maintenance",
        action_config="{}",
        is_active=True,
        priority=1,
    )
    db_session.add(rule)
    db_session.commit()

    with _workflow_client(triggerer, db_session) as client:
        response = client.post("/api/workflows/trigger", json={
            "trigger_type": "scheduled_check",
            "event_data": {"check_type": "health"},
        })

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is False
    assert payload["actions_executed"][0]["success"] is False
    assert payload["error"] == "一个或多个工作流动作执行失败"


def test_workflow_internal_errors_are_redacted(db_session, monkeypatch):
    from app.services.workflow.actions import ActionManager
    from app.shared.models import WorkflowRule

    _enable_auth(monkeypatch)
    triggerer = _create_user(
        db_session,
        "workflow-error-triggerer",
        permission="workflow:trigger",
    )
    db_session.add(WorkflowRule(
        name="internal error rule",
        trigger_type="scheduled_check",
        trigger_conditions="{}",
        action_type="log_event",
        action_config="{}",
        is_active=True,
        priority=1,
    ))
    db_session.commit()
    secret_detail = r"database failed at C:\private\workflow.db"

    async def explode(*_args, **_kwargs):
        raise RuntimeError(secret_detail)

    monkeypatch.setattr(ActionManager, "execute_action", explode)
    with _workflow_client(triggerer, db_session) as client:
        response = client.post("/api/workflows/trigger", json={
            "trigger_type": "scheduled_check",
            "event_data": {"check_type": "health"},
        })

    assert response.status_code == 200
    assert response.json()["success"] is False
    assert response.json()["error"] == "工作流执行失败，请查看服务端日志"
    assert secret_detail not in response.text


def test_workflow_frontend_menu_uses_read_permission():
    root = Path(__file__).resolve().parents[1]
    layout_source = (
        root / "frontend/src/views/Layout.vue"
    ).read_text(encoding="utf-8")
    workflows_source = (
        root / "frontend/src/views/Workflows.vue"
    ).read_text(encoding="utf-8")
    faults_source = (
        root / "app/features/faults/router.py"
    ).read_text(encoding="utf-8")
    workflow_menu = next(
        line for line in layout_source.splitlines() if "path: '/workflows'" in line
    )
    assert "permission: 'workflow:read'" in workflow_menu
    assert "eventData = { check_type: 'health' }" in workflows_source
    assert "principal.username" in faults_source