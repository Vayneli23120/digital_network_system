"""Regression tests for workflow maintenance creation guarantees."""

import pytest

from app.services.workflow.actions.actions import CreateMaintenanceAction
from app.shared.models import Device, FaultRecord, MaintenanceRecord


@pytest.mark.asyncio
async def test_create_maintenance_action_is_idempotent_for_fault(db_session):
    device = Device(name="SW-Workflow-Test", ip="192.0.2.11")
    db_session.add(device)
    db_session.flush()

    fault = FaultRecord(
        device_id=device.id,
        device_name=device.name,
        fault_no="FAULT-WORKFLOW-001",
        status="open",
        severity="major",
        description="Repeated workflow event",
    )
    db_session.add(fault)
    db_session.commit()

    action = CreateMaintenanceAction()
    context = {"device_id": device.id, "fault_id": fault.id}

    first = await action.execute({}, context, db_session)
    second = await action.execute({}, context, db_session)

    assert first["success"] is True
    assert second["success"] is True
    assert second["reused"] is True
    assert second["maintenance_id"] == first["maintenance_id"]
    assert db_session.query(MaintenanceRecord).filter(
        MaintenanceRecord.fault_id == fault.id
    ).count() == 1

    db_session.refresh(fault)
    assert fault.maintenance_id == first["maintenance_id"]
    assert fault.auto_created_maintenance is True