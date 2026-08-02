"""Security Step 4E-C1: atomic spare-movement transactional flow.

Covers the batch endpoint and the single-transaction integration into
planned-task completion and maintenance-record updates:
- all-or-nothing (a failing movement rolls back the whole request)
- conditional spare_movement:write permission for embedded movements
- the /api/spare-movements/batch endpoint
"""

import app.shared.models_jobs  # noqa: F401  Register jobs table in metadata.


def _create_user(db_session, username: str, *, permissions=(), superuser=False):
    from app.shared.models import Permission, Role, User

    user = User(
        username=username,
        password_hash="unused",
        is_active=True,
        is_superuser=superuser,
    )
    names = list(permissions)
    if names:
        role = Role(name=f"role-{username}", description="test role")
        records = []
        for permission_name in names:
            record = db_session.query(Permission).filter(
                Permission.name == permission_name
            ).first()
            if record is None:
                record = Permission(
                    name=permission_name,
                    resource=permission_name.split(":", 1)[0],
                    action=permission_name.split(":", 1)[1],
                )
                records.append(record)
            role.permissions.append(record)
        user.roles.append(role)
        db_session.add_all([role, *records])
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


def _enable_auth(monkeypatch):
    from app.shared.config import get_config

    config = get_config()
    monkeypatch.setattr(config.security, "auth_enabled", True)
    monkeypatch.setattr(config.app, "debug", False)


def _client(current_user, db, router_module):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from fastapi.exceptions import RequestValidationError

    from app.features.auth.identity import get_current_principal
    from app.shared.database import get_db
    from app.shared.exceptions import validation_exception_handler

    app = FastAPI()
    # 与真实服务器一致：校验失败返回 400 而非默认 422
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.include_router(router_module.router)
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_principal] = lambda: _principal(current_user)
    return TestClient(app)


def _part(db_session, part_number: str, stock: int = 0):
    from app.shared.models import SparePart

    part = SparePart(
        name=f"atomic-{part_number}",
        part_number=part_number,
        quantity_in_stock=stock,
        min_quantity=0,
        status="active" if stock > 0 else "depleted",
    )
    db_session.add(part)
    db_session.commit()
    db_session.refresh(part)
    return part


def _task(db_session, task_no: str):
    from datetime import datetime

    from app.shared.models import MaintenanceTask

    task = MaintenanceTask(
        task_no=task_no,
        device_id=None,
        device_name="TEST-DEV",
        scheduled_date=datetime.utcnow(),
        status="in_progress",
        schedule_source="test",
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)
    return task


def _maintenance_record(db_session, maint_no: str, description: str = "before"):
    from app.shared.models import MaintenanceRecord

    record = MaintenanceRecord(
        maint_no=maint_no,
        device_id=None,
        device_name="TEST-DEV",
        maint_type="corrective",
        title="atomic",
        description=description,
        status="created",
    )
    db_session.add(record)
    db_session.commit()
    db_session.refresh(record)
    return record


def _stock(db_session, part_id: int) -> int:
    from app.shared.models import SparePart

    db_session.expire_all()
    return db_session.query(SparePart).filter(SparePart.id == part_id).one().quantity_in_stock


# ==================== Batch endpoint ====================


def test_batch_movements_valid_all_or_nothing(db_session, monkeypatch):
    from app.shared.models import SparePartMovement
    from app.features.spare_movements import router as movements_router

    _enable_auth(monkeypatch)
    admin = _create_user(db_session, "atomic-batch-admin", superuser=True)
    part = _part(db_session, "ATOM-BATCH", stock=0)

    with _client(admin, db_session, movements_router) as client:
        resp = client.post("/api/spare-movements/batch", json={
            "movements": [
                {"part_id": part.id, "movement_type": "in", "quantity": 5},
                {"part_id": part.id, "movement_type": "out", "quantity": 2},
            ]
        })
        assert resp.status_code == 200, resp.text
        assert len(resp.json()) == 2
        assert [m["movement_type"] for m in resp.json()] == ["in", "out"]

    assert _stock(db_session, part.id) == 3
    assert db_session.query(SparePartMovement).count() == 2


def test_batch_movements_failure_rolls_back_everything(db_session, monkeypatch):
    from app.shared.models import SparePartMovement
    from app.features.spare_movements import router as movements_router

    _enable_auth(monkeypatch)
    admin = _create_user(db_session, "atomic-batch-admin2", superuser=True)
    part = _part(db_session, "ATOM-BATCHFAIL", stock=0)

    with _client(admin, db_session, movements_router) as client:
        resp = client.post("/api/spare-movements/batch", json={
            "movements": [
                {"part_id": part.id, "movement_type": "in", "quantity": 1},
                {"part_id": part.id, "movement_type": "out", "quantity": 99},
            ]
        })
        assert resp.status_code == 400, resp.text

    # 整批回滚：第 2 条"库存不足"失败，第 1 条入库也不落库
    assert _stock(db_session, part.id) == 0
    assert db_session.query(SparePartMovement).count() == 0


def test_batch_movements_empty_rejected(db_session, monkeypatch):
    from app.features.spare_movements import router as movements_router

    _enable_auth(monkeypatch)
    admin = _create_user(db_session, "atomic-batch-admin3", superuser=True)

    with _client(admin, db_session, movements_router) as client:
        resp = client.post("/api/spare-movements/batch", json={"movements": []})
        assert resp.status_code == 400, resp.text


def test_batch_requires_movement_write(db_session, monkeypatch):
    from app.shared.models import SparePartMovement
    from app.features.spare_movements import router as movements_router

    _enable_auth(monkeypatch)
    reader = _create_user(db_session, "atomic-batch-reader", permissions=["spare_movement:read"])
    part = _part(db_session, "ATOM-BATCHPERM")

    with _client(reader, db_session, movements_router) as client:
        resp = client.post("/api/spare-movements/batch", json={
            "movements": [{"part_id": part.id, "movement_type": "in", "quantity": 1}]
        })
        assert resp.status_code == 403, resp.text
    assert db_session.query(SparePartMovement).count() == 0


# ==================== Planned-task completion ====================


def test_complete_task_atomic_success(db_session, monkeypatch):
    from app.shared.models import MaintenanceTask, SparePartMovement
    from app.features.planned_maintenance import router as pm_router

    _enable_auth(monkeypatch)
    executor = _create_user(
        db_session, "atomic-exec-ok",
        permissions=["planned_task:execute", "spare_movement:write"],
    )
    part = _part(db_session, "ATOM-TASKOK")
    task = _task(db_session, "ATOM-TASK-OK")

    with _client(executor, db_session, pm_router) as client:
        resp = client.post(f"/api/planned-maintenance/tasks/{task.id}/complete", json={
            "description": "atomic complete",
            "spare_movements": [
                {"part_id": part.id, "movement_type": "in", "quantity": 3},
                {"part_id": part.id, "movement_type": "out", "quantity": 1},
            ]
        })
        assert resp.status_code == 200, resp.text

    db_session.expire_all()
    assert db_session.query(MaintenanceTask).filter(
        MaintenanceTask.id == task.id).one().status == "completed"
    assert _stock(db_session, part.id) == 2
    assert db_session.query(SparePartMovement).count() == 2


def test_complete_task_movement_failure_keeps_task_in_progress(db_session, monkeypatch):
    from app.shared.models import MaintenanceRecord, MaintenanceTask, SparePartMovement
    from app.features.planned_maintenance import router as pm_router

    _enable_auth(monkeypatch)
    executor = _create_user(
        db_session, "atomic-exec-fail",
        permissions=["planned_task:execute", "spare_movement:write"],
    )
    part = _part(db_session, "ATOM-TASKFAIL")
    task = _task(db_session, "ATOM-TASK-FAIL")

    with _client(executor, db_session, pm_router) as client:
        resp = client.post(f"/api/planned-maintenance/tasks/{task.id}/complete", json={
            "description": "atomic complete",
            "spare_movements": [
                {"part_id": part.id, "movement_type": "in", "quantity": 1},
                {"part_id": part.id, "movement_type": "out", "quantity": 99},
            ]
        })
        assert resp.status_code == 400, resp.text

    db_session.expire_all()
    # 整批回滚：任务保持 in_progress、维修单未创建、无任何 movement 落库
    assert db_session.query(MaintenanceTask).filter(
        MaintenanceTask.id == task.id).one().status == "in_progress"
    assert db_session.query(MaintenanceRecord).filter(
        MaintenanceRecord.maint_no.like("MAINT-%")).count() == 0
    assert _stock(db_session, part.id) == 0
    assert db_session.query(SparePartMovement).count() == 0


def test_complete_task_embedded_movement_requires_movement_write(db_session, monkeypatch):
    from app.shared.models import MaintenanceTask, SparePartMovement
    from app.features.planned_maintenance import router as pm_router

    _enable_auth(monkeypatch)
    # 持有 planned_task:execute 但无 spare_movement:write
    executor = _create_user(
        db_session, "atomic-exec-nomv", permissions=["planned_task:execute"],
    )
    part = _part(db_session, "ATOM-TASKPERM")
    task = _task(db_session, "ATOM-TASK-PERM")

    with _client(executor, db_session, pm_router) as client:
        resp = client.post(f"/api/planned-maintenance/tasks/{task.id}/complete", json={
            "description": "atomic complete",
            "spare_movements": [
                {"part_id": part.id, "movement_type": "in", "quantity": 1},
            ]
        })
        assert resp.status_code == 403, resp.text

    db_session.expire_all()
    assert db_session.query(MaintenanceTask).filter(
        MaintenanceTask.id == task.id).one().status == "in_progress"
    assert _stock(db_session, part.id) == 0
    assert db_session.query(SparePartMovement).count() == 0


def test_complete_task_without_movements_still_works(db_session, monkeypatch):
    from app.shared.models import MaintenanceTask
    from app.features.planned_maintenance import router as pm_router

    _enable_auth(monkeypatch)
    executor = _create_user(db_session, "atomic-exec-plain", permissions=["planned_task:execute"])
    task = _task(db_session, "ATOM-TASK-PLAIN")

    with _client(executor, db_session, pm_router) as client:
        resp = client.post(f"/api/planned-maintenance/tasks/{task.id}/complete", json={
            "description": "plain complete",
        })
        assert resp.status_code == 200, resp.text

    db_session.expire_all()
    assert db_session.query(MaintenanceTask).filter(
        MaintenanceTask.id == task.id).one().status == "completed"


# ==================== Maintenance-record update ====================


def test_update_maintenance_atomic_success(db_session, monkeypatch):
    from app.shared.models import MaintenanceRecord, SparePartMovement
    from app.features.maintenance import router as maint_router

    _enable_auth(monkeypatch)
    writer = _create_user(
        db_session, "atomic-maint-ok",
        permissions=["maintenance:write", "spare_movement:write"],
    )
    part = _part(db_session, "ATOM-MAINTOK")
    record = _maintenance_record(db_session, "ATOM-MAINT-OK")

    with _client(writer, db_session, maint_router) as client:
        resp = client.put(f"/api/maintenance/{record.id}", json={
            "description": "after",
            "spare_movements": [
                {"part_id": part.id, "movement_type": "in", "quantity": 4},
                {"part_id": part.id, "movement_type": "out", "quantity": 1},
            ]
        })
        assert resp.status_code == 200, resp.text

    db_session.expire_all()
    assert db_session.query(MaintenanceRecord).filter(
        MaintenanceRecord.id == record.id).one().description == "after"
    assert _stock(db_session, part.id) == 3
    assert db_session.query(SparePartMovement).count() == 2


def test_update_maintenance_movement_failure_rolls_back(db_session, monkeypatch):
    from app.shared.models import MaintenanceRecord, SparePartMovement
    from app.features.maintenance import router as maint_router

    _enable_auth(monkeypatch)
    writer = _create_user(
        db_session, "atomic-maint-fail",
        permissions=["maintenance:write", "spare_movement:write"],
    )
    part = _part(db_session, "ATOM-MAINTFAIL")
    record = _maintenance_record(db_session, "ATOM-MAINT-FAIL", description="before")

    with _client(writer, db_session, maint_router) as client:
        resp = client.put(f"/api/maintenance/{record.id}", json={
            "description": "after",
            "spare_movements": [
                {"part_id": part.id, "movement_type": "in", "quantity": 1},
                {"part_id": part.id, "movement_type": "out", "quantity": 99},
            ]
        })
        assert resp.status_code == 400, resp.text

    db_session.expire_all()
    # 记录字段与库存均回滚
    assert db_session.query(MaintenanceRecord).filter(
        MaintenanceRecord.id == record.id).one().description == "before"
    assert _stock(db_session, part.id) == 0
    assert db_session.query(SparePartMovement).count() == 0


def test_update_maintenance_embedded_movement_requires_movement_write(db_session, monkeypatch):
    from app.shared.models import MaintenanceRecord, SparePartMovement
    from app.features.maintenance import router as maint_router

    _enable_auth(monkeypatch)
    writer = _create_user(db_session, "atomic-maint-nomv", permissions=["maintenance:write"])
    part = _part(db_session, "ATOM-MAINTPERM")
    record = _maintenance_record(db_session, "ATOM-MAINT-PERM", description="before")

    with _client(writer, db_session, maint_router) as client:
        resp = client.put(f"/api/maintenance/{record.id}", json={
            "description": "after",
            "spare_movements": [
                {"part_id": part.id, "movement_type": "in", "quantity": 1},
            ]
        })
        assert resp.status_code == 403, resp.text

    db_session.expire_all()
    assert db_session.query(MaintenanceRecord).filter(
        MaintenanceRecord.id == record.id).one().description == "before"
    assert _stock(db_session, part.id) == 0
    assert db_session.query(SparePartMovement).count() == 0
