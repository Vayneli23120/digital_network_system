"""Transactional helpers for creating one maintenance record per fault."""

from typing import Any, Dict, Optional, Sequence, Tuple

from sqlalchemy.orm import Session

from app.shared.models import FaultRecord, MaintenanceRecord


class FaultMaintenanceConflictError(RuntimeError):
    """Raised when a fault can no longer be claimed for maintenance."""


def find_fault_maintenance(
    db: Session,
    fault: FaultRecord,
) -> Optional[MaintenanceRecord]:
    """Return the maintenance record linked from either side of the relation."""
    existing = None
    if fault.maintenance_id:
        existing = db.query(MaintenanceRecord).filter(
            MaintenanceRecord.id == fault.maintenance_id
        ).first()
    if not existing:
        existing = db.query(MaintenanceRecord).filter(
            MaintenanceRecord.fault_id == fault.id
        ).order_by(MaintenanceRecord.id).first()
    return existing


def create_fault_maintenance_once(
    db: Session,
    fault: FaultRecord,
    maintenance: MaintenanceRecord,
    *,
    fault_updates: Optional[Dict[Any, Any]] = None,
    claim_filters: Sequence[Any] = (),
) -> Tuple[MaintenanceRecord, bool]:
    """Create and atomically link a maintenance record, or reuse the winner."""
    existing = find_fault_maintenance(db, fault)
    if existing:
        if fault.maintenance_id != existing.id:
            fault.maintenance_id = existing.id
            db.commit()
            db.refresh(fault)
        return existing, False

    db.add(maintenance)
    db.flush()

    updates = {FaultRecord.maintenance_id: maintenance.id}
    updates.update(fault_updates or {})

    claim = db.query(FaultRecord).filter(
        FaultRecord.id == fault.id,
        FaultRecord.maintenance_id.is_(None),
        *claim_filters,
    ).update(updates, synchronize_session=False)

    if claim != 1:
        db.rollback()
        current_fault = db.query(FaultRecord).filter(
            FaultRecord.id == fault.id
        ).first()
        existing = (
            find_fault_maintenance(db, current_fault)
            if current_fault
            else None
        )
        if existing:
            return existing, False
        raise FaultMaintenanceConflictError(
            "Fault maintenance state changed during creation"
        )

    db.commit()
    db.refresh(maintenance)
    db.refresh(fault)
    return maintenance, True