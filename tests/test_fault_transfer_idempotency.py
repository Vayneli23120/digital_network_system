"""Regression tests for fault-to-maintenance transfer guarantees."""

import pytest
from fastapi import BackgroundTasks

from app.features.faults import router as faults_router
from app.features.faults.router import (
    AnalyzeFaultRequest,
    TransferToMaintenanceRequest,
    analyze_fault,
    auto_create_maintenance,
    convert_to_maintenance,
    transfer_to_maintenance,
)
from app.shared.models import Device, FaultRecord, MaintenanceRecord


@pytest.mark.asyncio
async def test_transfer_to_maintenance_is_idempotent(db_session):
    device = Device(name="SW-Transfer-Test", ip="192.0.2.10")
    db_session.add(device)
    db_session.flush()

    fault = FaultRecord(
        device_id=device.id,
        device_name=device.name,
        fault_no="FAULT-TRANSFER-001",
        status="diagnosing",
        severity="major",
        description="Uplink module failure",
    )
    db_session.add(fault)
    db_session.commit()

    request = TransferToMaintenanceRequest(
        maintenance_type="corrective",
        priority="P2",
    )
    first = await transfer_to_maintenance(
        fault.id,
        request,
        BackgroundTasks(),
        db_session,
    )
    second = await transfer_to_maintenance(
        fault.id,
        request,
        BackgroundTasks(),
        db_session,
    )

    assert second["maintenance_id"] == first["maintenance_id"]
    assert db_session.query(MaintenanceRecord).filter(
        MaintenanceRecord.fault_id == fault.id
    ).count() == 1

    db_session.refresh(fault)
    assert fault.status == "transferred"
    assert fault.maintenance_id == first["maintenance_id"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "create_maintenance",
    [auto_create_maintenance, convert_to_maintenance],
)
async def test_legacy_fault_maintenance_routes_are_idempotent(
    db_session,
    create_maintenance,
):
    device = Device(name="SW-Legacy-Route-Test", ip="192.0.2.12")
    db_session.add(device)
    db_session.flush()

    fault = FaultRecord(
        device_id=device.id,
        device_name=device.name,
        fault_no=f"FAULT-{create_maintenance.__name__}",
        status="open",
        severity="major",
        description="Repeated maintenance request",
    )
    db_session.add(fault)
    db_session.commit()

    first = await create_maintenance(fault.id, db=db_session)
    second = await create_maintenance(fault.id, db=db_session)

    assert second["maintenance_id"] == first["maintenance_id"]
    assert db_session.query(MaintenanceRecord).filter(
        MaintenanceRecord.fault_id == fault.id
    ).count() == 1

    db_session.refresh(fault)
    assert fault.maintenance_id == first["maintenance_id"]


@pytest.mark.asyncio
async def test_repeated_ai_analysis_reuses_fault_maintenance(
    db_session,
    monkeypatch,
):
    class FakeADKRunner:
        async def run_agent(self, **kwargs):
            return {"success": True, "response": "repair"}

        def parse_json_response(self, response):
            return {"need_repair": "repair"}

    monkeypatch.setattr(faults_router, "ADK_AVAILABLE", True)
    monkeypatch.setattr(faults_router, "adk_runner", FakeADKRunner())
    monkeypatch.setattr(faults_router, "fault_analysis_agent", object())

    device = Device(name="SW-AI-Route-Test", ip="192.0.2.13")
    db_session.add(device)
    db_session.flush()

    fault = FaultRecord(
        device_id=device.id,
        device_name=device.name,
        fault_no="FAULT-AI-ROUTE-001",
        status="open",
        severity="major",
        description="AI recommends repair",
    )
    db_session.add(fault)
    db_session.commit()

    request = AnalyzeFaultRequest(auto_create_maintenance=True)
    first = await analyze_fault(fault.id, request, db_session)
    second = await analyze_fault(fault.id, request, db_session)

    assert second["maintenance_reused"] is True
    assert second["created_maintenance_id"] == first["created_maintenance_id"]
    assert db_session.query(MaintenanceRecord).filter(
        MaintenanceRecord.fault_id == fault.id
    ).count() == 1