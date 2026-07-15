"""PostgreSQL-only concurrency tests for Step 0 transaction safeguards."""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, local
from uuid import uuid4

import pytest
from sqlalchemy import event

from app.features.spare_parts.spare_part_service import create_movement
from app.services import fault_maintenance as fault_maintenance_service
from app.services.fault_maintenance import create_fault_maintenance_once
from app.shared.models import (
    Device,
    FaultRecord,
    MaintenanceRecord,
    SparePart,
    SparePartMovement,
)


@pytest.mark.postgresql
def test_concurrent_outbound_movement_never_creates_negative_stock(db_manager):
    test_id = uuid4().hex
    setup_session = db_manager.get_session()
    part = SparePart(
        name=f"STEP0-PG-Part-{test_id}",
        part_number=f"STEP0-PG-PART-{test_id}",
        quantity_in_stock=1,
        min_quantity=0,
    )
    setup_session.add(part)
    setup_session.commit()
    part_id = part.id
    setup_session.close()

    update_barrier = Barrier(2)
    thread_state = local()

    def synchronize_inventory_updates(
        connection,
        cursor,
        statement,
        parameters,
        context,
        executemany,
    ):
        normalized_statement = statement.lower()
        is_atomic_decrement = (
            normalized_statement.lstrip().startswith("update spare_parts")
            and "quantity_in_stock" in normalized_statement
        )
        if is_atomic_decrement and not getattr(thread_state, "update_waited", False):
            thread_state.update_waited = True
            update_barrier.wait(timeout=15)

    def remove_one(operator: str):
        session = db_manager.get_session()
        try:
            try:
                movement = create_movement(
                    session,
                    part_id,
                    "out",
                    1,
                    operator=operator,
                )
                return "success", movement["id"]
            except ValueError as exc:
                session.rollback()
                return "insufficient", str(exc)
        finally:
            session.close()

    verification_session = db_manager.get_session()
    try:
        event.listen(
            db_manager.engine,
            "before_cursor_execute",
            synchronize_inventory_updates,
        )
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [
                executor.submit(remove_one, "STEP0-PG-worker-1"),
                executor.submit(remove_one, "STEP0-PG-worker-2"),
            ]
            results = [future.result(timeout=30) for future in futures]

        outcomes = sorted(result[0] for result in results)
        assert outcomes == ["insufficient", "success"]

        persisted_part = verification_session.query(SparePart).filter(
            SparePart.id == part_id
        ).one()
        movement_count = verification_session.query(SparePartMovement).filter(
            SparePartMovement.part_id == part_id,
            SparePartMovement.movement_type == "out",
        ).count()

        assert persisted_part.quantity_in_stock == 0
        assert movement_count == 1
    finally:
        event.remove(
            db_manager.engine,
            "before_cursor_execute",
            synchronize_inventory_updates,
        )
        verification_session.rollback()
        verification_session.query(SparePartMovement).filter(
            SparePartMovement.part_id == part_id
        ).delete(synchronize_session=False)
        verification_session.query(SparePart).filter(
            SparePart.id == part_id
        ).delete(synchronize_session=False)
        verification_session.commit()
        verification_session.close()


@pytest.mark.postgresql
def test_concurrent_fault_maintenance_creation_reuses_one_record(
    db_manager,
    monkeypatch,
):
    test_id = uuid4().hex
    setup_session = db_manager.get_session()
    device = Device(
        name=f"STEP0-PG-Device-{test_id}",
        ip="192.0.2.20",
    )
    setup_session.add(device)
    setup_session.flush()
    fault = FaultRecord(
        device_id=device.id,
        device_name=device.name,
        fault_no=f"STEP0-PG-FAULT-{test_id}",
        status="diagnosing",
        severity="major",
        description="Concurrent maintenance creation test",
    )
    setup_session.add(fault)
    setup_session.commit()
    device_id = device.id
    fault_id = fault.id
    setup_session.close()

    start_barrier = Barrier(2)
    claim_barrier = Barrier(2)
    thread_state = local()
    original_find = fault_maintenance_service.find_fault_maintenance

    def synchronize_initial_maintenance_check(session, worker_fault):
        existing = original_find(session, worker_fault)
        if existing is None and not getattr(thread_state, "claim_waited", False):
            thread_state.claim_waited = True
            claim_barrier.wait(timeout=15)
        return existing

    monkeypatch.setattr(
        fault_maintenance_service,
        "find_fault_maintenance",
        synchronize_initial_maintenance_check,
    )

    def create_maintenance(worker_number: int):
        session = db_manager.get_session()
        try:
            worker_fault = session.query(FaultRecord).filter(
                FaultRecord.id == fault_id
            ).one()
            start_barrier.wait(timeout=15)
            candidate = MaintenanceRecord(
                maint_no=f"STEP0-PG-MAINT-{worker_number}-{test_id}",
                device_id=device_id,
                device_name=worker_fault.device_name,
                fault_id=fault_id,
                maint_type="corrective",
                status="pending",
                title="Concurrent maintenance creation test",
            )
            maintenance, created = create_fault_maintenance_once(
                session,
                worker_fault,
                candidate,
                fault_updates={
                    FaultRecord.auto_created_maintenance: True,
                },
            )
            return maintenance.id, created
        finally:
            session.close()

    verification_session = db_manager.get_session()
    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [
                executor.submit(create_maintenance, 1),
                executor.submit(create_maintenance, 2),
            ]
            results = [future.result(timeout=30) for future in futures]

        maintenance_ids = {result[0] for result in results}
        created_flags = sorted(result[1] for result in results)
        persisted_fault = verification_session.query(FaultRecord).filter(
            FaultRecord.id == fault_id
        ).one()
        maintenance_count = verification_session.query(MaintenanceRecord).filter(
            MaintenanceRecord.fault_id == fault_id
        ).count()

        assert len(maintenance_ids) == 1
        assert created_flags == [False, True]
        assert maintenance_count == 1
        assert persisted_fault.maintenance_id == next(iter(maintenance_ids))
        assert persisted_fault.auto_created_maintenance is True
    finally:
        verification_session.rollback()
        verification_session.query(FaultRecord).filter(
            FaultRecord.id == fault_id
        ).update(
            {FaultRecord.maintenance_id: None},
            synchronize_session=False,
        )
        verification_session.flush()
        verification_session.query(MaintenanceRecord).filter(
            MaintenanceRecord.fault_id == fault_id
        ).delete(synchronize_session=False)
        verification_session.query(FaultRecord).filter(
            FaultRecord.id == fault_id
        ).delete(synchronize_session=False)
        verification_session.query(Device).filter(
            Device.id == device_id
        ).delete(synchronize_session=False)
        verification_session.commit()
        verification_session.close()