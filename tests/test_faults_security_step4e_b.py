"""Security Step 4E-B1: Faults RBAC, identity, and input safety."""

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


def _fault_client(current_user, db_session):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.features.auth.identity import get_current_principal
    from app.features.auth.router import get_current_user_from_token
    from app.features.faults import router as faults_router
    from app.shared.database import get_db

    app = FastAPI()
    app.include_router(faults_router.router)
    app.dependency_overrides[get_current_user_from_token] = lambda: current_user
    app.dependency_overrides[get_db] = lambda: db_session
    if current_user is not None:
        app.dependency_overrides[get_current_principal] = lambda: _principal(current_user)
    return TestClient(app)


def _enable_auth(monkeypatch):
    from app.shared.config import get_config

    config = get_config()
    monkeypatch.setattr(config.security, "auth_enabled", True)
    monkeypatch.setattr(config.app, "debug", False)


def test_fault_http_permission_matrix_is_declared():
    from app.features.faults import router as faults_router

    expected = {
        "require_fault_read": [
            "list_faults",
            "get_fault",
            "get_root_cause",
            "get_fault_maintenance",
            "get_incidents_dashboard",
            "get_fault_transitions",
        ],
        "require_fault_write": [
            "create_fault",
            "update_fault",
            "update_fault_status",
            "escalate_fault",
            "convert_to_maintenance",
            "assign_fault",
            "accept_fault",
            "review_fault",
            "diagnose_fault",
            "add_fault_work_note",
            "transfer_to_maintenance",
            "resolve_fault",
            "close_fault",
        ],
        "require_fault_delete": ["delete_fault"],
        "require_fault_analyze": [
            "analyze_fault",
            "ai_pre_diagnose",
            "auto_create_maintenance",
        ],
    }
    assert sum(len(functions) for functions in expected.values()) == 23
    for dependency_name, function_names in expected.items():
        dependency = getattr(faults_router, dependency_name)
        for function_name in function_names:
            function = getattr(faults_router, function_name)
            parameter = inspect.signature(function).parameters.get("_")
            assert parameter is not None, f"{function_name} missing permission dependency"
            assert parameter.default.dependency is dependency


def test_fault_permission_tiers_are_separated(db_session, monkeypatch):
    from app.shared.models import Device

    _enable_auth(monkeypatch)
    device = Device(name="fault-permission-device", ip="192.0.2.31")
    db_session.add(device)
    db_session.commit()
    reader = _create_user(db_session, "fault-reader", permission="fault:read")
    writer = _create_user(db_session, "fault-writer", permission="fault:write")
    analyzer = _create_user(db_session, "fault-analyzer", permission="fault:analyze")
    deleter = _create_user(db_session, "fault-deleter", permission="fault:delete")

    with _fault_client(None, db_session) as client:
        assert client.get("/api/faults").status_code == 401

    with _fault_client(reader, db_session) as client:
        assert client.get("/api/faults").status_code == 200
        assert client.get("/api/faults/incidents/dashboard").status_code == 200
        assert client.post(
            "/api/faults",
            json={"device_id": device.id, "description": "denied"},
        ).status_code == 403
    with _fault_client(writer, db_session) as client:
        assert client.get("/api/faults").status_code == 403
        assert client.delete("/api/faults/999999").status_code == 403
        assert client.post("/api/faults/999999/ai-pre-diagnose").status_code == 403
    with _fault_client(analyzer, db_session) as client:
        assert client.post("/api/faults/999999/ai-pre-diagnose").status_code == 404
        assert client.delete("/api/faults/999999").status_code == 403
    with _fault_client(deleter, db_session) as client:
        assert client.delete("/api/faults/999999").status_code == 404
        assert client.get("/api/faults").status_code == 403


def test_fault_actor_fields_come_from_principal(db_session, monkeypatch):
    from app.features.faults import router as faults_router
    from app.shared.models import Device, FaultRecord, MaintenanceRecord

    _enable_auth(monkeypatch)

    async def no_background_work(*_args, **_kwargs):
        return None

    monkeypatch.setattr(faults_router, "trigger_fault_workflow", no_background_work)
    monkeypatch.setattr(
        faults_router,
        "send_maintenance_assigned_notification",
        no_background_work,
    )
    device = Device(name="fault-actor-device", ip="192.0.2.32")
    db_session.add(device)
    db_session.commit()
    writer = _create_user(
        db_session,
        "trusted-fault-operator",
        permission="fault:write",
    )

    with _fault_client(writer, db_session) as client:
        created = client.post(
            "/api/faults",
            json={
                "device_id": device.id,
                "description": "principal identity test",
                "reporter": "forged-reporter",
            },
        )
        assert created.status_code == 200
        fault_id = created.json()["id"]
        reviewed = client.post(
            f"/api/faults/{fault_id}/review",
            json={"reviewed_by": "forged-reviewer", "false_positive": False},
        )
        assert reviewed.status_code == 200

    stored_fault = db_session.query(FaultRecord).filter(FaultRecord.id == fault_id).one()
    assert stored_fault.reporter == writer.username
    assert stored_fault.reviewed_by == writer.username
    assert stored_fault.assigned_to == writer.username

    transfer_fault = FaultRecord(
        device_id=device.id,
        device_name=device.name,
        fault_no="FAULT-PRINCIPAL-TRANSFER",
        status="diagnosing",
        severity="major",
        description="transfer identity test",
    )
    db_session.add(transfer_fault)
    db_session.commit()

    with _fault_client(writer, db_session) as client:
        transferred = client.post(
            f"/api/faults/{transfer_fault.id}/transfer-to-maintenance",
            json={
                "maintenance_owner": "field-engineer",
                "description": "maintenance description",
                "diagnosis_text": "transfer diagnosis",
            },
        )

    assert transferred.status_code == 200
    maintenance = db_session.query(MaintenanceRecord).filter(
        MaintenanceRecord.id == transferred.json()["maintenance_id"]
    ).one()
    assert maintenance.operator == writer.username
    assert maintenance.current_owner == "field-engineer"
    assert maintenance.description == "maintenance description"
    assert maintenance.diagnosis_text == "transfer diagnosis"


def test_fault_work_note_and_pagination_are_bounded(db_session, monkeypatch):
    from app.shared.models import Device, FaultRecord

    _enable_auth(monkeypatch)
    device = Device(name="fault-input-device", ip="192.0.2.33")
    db_session.add(device)
    db_session.flush()
    fault = FaultRecord(
        device_id=device.id,
        device_name=device.name,
        fault_no="FAULT-INPUT-BOUNDS",
        status="open",
        severity="minor",
        description="input bounds test",
    )
    db_session.add(fault)
    db_session.commit()
    writer = _create_user(db_session, "fault-input-writer", permission="fault:write")
    reader = _create_user(db_session, "fault-input-reader", permission="fault:read")

    with _fault_client(writer, db_session) as client:
        assert client.post(
            f"/api/faults/{fault.id}/work-note",
            json={"note": "", "operator": "forged"},
        ).status_code == 422
        assert client.post(
            f"/api/faults/{fault.id}/work-note",
            json={"note": " "},
        ).status_code == 422
        assert client.post(
            f"/api/faults/{fault.id}/work-note",
            json={"note": "x" * 10_001},
        ).status_code == 422
        assert client.post(
            f"/api/faults/{fault.id}/work-note",
            json={"note": " bounded note "},
        ).status_code == 200

    with _fault_client(reader, db_session) as client:
        assert client.get("/api/faults?skip=-1").status_code == 422
        assert client.get("/api/faults?limit=0").status_code == 422
        assert client.get("/api/faults?limit=501").status_code == 422

    db_session.refresh(fault)
    assert fault.diagnosis_text == "bounded note"


def test_fault_list_uses_business_severity_order(db_session, monkeypatch):
    from app.shared.models import Device, FaultRecord

    _enable_auth(monkeypatch)
    device = Device(name="fault-order-device", ip="192.0.2.34")
    db_session.add(device)
    db_session.flush()
    for index, severity in enumerate(("minor", "warning", "major", "critical")):
        db_session.add(FaultRecord(
            device_id=device.id,
            device_name=device.name,
            fault_no=f"FAULT-ORDER-{index}",
            status="open",
            severity=severity,
            description=f"{severity} fault",
        ))
    db_session.commit()
    reader = _create_user(db_session, "fault-order-reader", permission="fault:read")

    with _fault_client(reader, db_session) as client:
        response = client.get("/api/faults")

    assert response.status_code == 200
    assert [item["severity"] for item in response.json()["items"]] == [
        "critical",
        "major",
        "warning",
        "minor",
    ]


def test_fault_dashboard_accounts_for_full_status_machine(db_session, monkeypatch):
    from app.shared.models import Device, FaultRecord

    _enable_auth(monkeypatch)
    device = Device(name="fault-status-device", ip="192.0.2.35")
    db_session.add(device)
    db_session.flush()
    statuses = (
        "open",
        "assigned",
        "accepted",
        "diagnosing",
        "resolving",
        "transferred",
        "resolved",
        "reassigned",
        "investigating",
        "closed",
    )
    for index, status in enumerate(statuses):
        db_session.add(FaultRecord(
            device_id=device.id,
            device_name=device.name,
            fault_no=f"FAULT-STATUS-{index}",
            status=status,
            severity="major",
            description=f"{status} fault",
        ))
    db_session.commit()
    reader = _create_user(db_session, "fault-status-reader", permission="fault:read")

    with _fault_client(reader, db_session) as client:
        response = client.get("/api/faults/incidents/dashboard")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_faults"] == len(statuses)
    assert payload["active_faults"] == len(statuses) - 1
    assert sum(payload["status_distribution"].values()) == len(statuses)
    assert set(payload["status_distribution"]) == set(statuses)
    assert payload["severity_distribution"]["major"] == len(statuses) - 1


def test_fault_frontend_does_not_send_actor_identity_or_raw_fetch():
    root = Path(__file__).resolve().parents[1]
    faults_source = (root / "frontend/src/views/Faults.vue").read_text(encoding="utf-8")
    detail_source = (
        root / "frontend/src/views/DeviceDetail.vue"
    ).read_text(encoding="utf-8")
    fault_detail_source = (
        root / "frontend/src/views/FaultDetail.vue"
    ).read_text(encoding="utf-8")
    monitor_source = (
        root / "frontend/src/views/Monitor3D.vue"
    ).read_text(encoding="utf-8")
    layout_source = (
        root / "frontend/src/views/Layout.vue"
    ).read_text(encoding="utf-8")

    assert "reporter: 'Web'" not in faults_source
    assert "reporter: 'Web'" not in detail_source
    assert "reviewed_by: 'Monitor3D'" not in monitor_source
    assert (
        "note: editForm.value.work_note.trim(),\n"
        "          author: localStorage.getItem('currentUser')"
    ) not in fault_detail_source
    assert "fetch('/api/faults" not in layout_source
    assert "getFaults({ limit: 500 })" in layout_source
    assert "f.status !== 'closed'" in layout_source
    assert "description: transferForm.value.maintenance_description" in fault_detail_source
    fault_menu = next(
        line for line in layout_source.splitlines() if "path: '/faults'" in line
    )
    assert "permission: 'fault:read'" in fault_menu