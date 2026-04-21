"""
Tests for spare_part_service.py
"""

import pytest
from sqlalchemy.orm import Session

from app.shared.models import SparePart, SparePartMovement
from app.features.spare_parts.spare_part_service import (
    list_parts, get_part, create_part, update_part, delete_part,
    get_stats, create_movement, list_movements, get_movement,
)
from app.shared.exceptions import ResourceNotFoundException, ConflictException


class TestListParts:
    def test_list_parts_empty(self, db_session):
        result = list_parts(db_session)
        assert result["total"] == 0
        assert result["items"] == []

    def test_list_parts_with_data(self, db_session):
        create_part(db_session, {"name": "SFP-1G", "part_number": "SFP-001", "quantity_in_stock": 10})
        result = list_parts(db_session)
        assert result["total"] == 1
        assert result["items"][0]["name"] == "SFP-1G"

    def test_list_parts_filter_by_category(self, db_session):
        create_part(db_session, {"name": "SFP-1G", "part_number": "SFP-001", "category": "module"})
        create_part(db_session, {"name": "Cable-RJ45", "part_number": "CBL-001", "category": "cable"})

        result = list_parts(db_session, category="module")
        assert result["total"] == 1

    def test_list_parts_filter_by_status(self, db_session):
        create_part(db_session, {"name": "Active-Part", "part_number": "AP-001", "status": "active"})
        create_part(db_session, {"name": "Inactive-Part", "part_number": "IP-001", "status": "inactive"})

        result = list_parts(db_session, status="inactive")
        assert result["total"] == 1

    def test_list_parts_low_stock(self, db_session):
        create_part(db_session, {"name": "Enough", "part_number": "P-001", "quantity_in_stock": 10, "min_quantity": 5})
        create_part(db_session, {"name": "Low", "part_number": "P-002", "quantity_in_stock": 2, "min_quantity": 5})

        result = list_parts(db_session, low_stock=True)
        assert result["total"] == 1
        assert result["items"][0]["name"] == "Low"

    def test_list_parts_search(self, db_session):
        create_part(db_session, {"name": "SFP-1G", "part_number": "SFP-001"})
        create_part(db_session, {"name": "SFP-10G", "part_number": "SFP-002"})
        create_part(db_session, {"name": "Cable-RJ45", "part_number": "CBL-001"})

        result = list_parts(db_session, search="SFP")
        assert result["total"] == 2

    def test_list_parts_pagination(self, db_session):
        for i in range(10):
            create_part(db_session, {"name": f"Part-{i}", "part_number": f"P-{i:03d}"})

        result = list_parts(db_session, skip=0, limit=3)
        assert result["total"] == 10  # total is full count
        assert len(result["items"]) == 3  # but items are limited to 3


class TestGetPart:
    def test_get_part_success(self, db_session):
        create_part(db_session, {"name": "SFP-1G", "part_number": "SFP-001", "category": "module"})
        result = get_part(db_session, 1)
        assert result["name"] == "SFP-1G"
        assert result["category"] == "module"

    def test_get_part_not_found(self, db_session):
        with pytest.raises(ResourceNotFoundException):
            get_part(db_session, 999)


class TestCreatePart:
    def test_create_part(self, db_session):
        result = create_part(db_session, {
            "name": "Power-Supply", "part_number": "PSU-001",
            "category": "power", "quantity_in_stock": 5,
            "min_quantity": 2, "unit_price": 500.0,
        })
        assert "id" in result
        assert result["name"] == "Power-Supply"

    def test_create_part_duplicate_part_number(self, db_session):
        create_part(db_session, {"name": "SFP-A", "part_number": "SFP-001"})
        with pytest.raises(ConflictException):
            create_part(db_session, {"name": "SFP-B", "part_number": "SFP-001"})


class TestUpdatePart:
    def test_update_part(self, db_session):
        create_part(db_session, {"name": "Old", "part_number": "P-001"})
        result = update_part(db_session, 1, {"name": "New", "min_quantity": 10})
        assert result["message"] == "更新成功"

        updated = get_part(db_session, 1)
        assert updated["name"] == "New"
        assert updated["min_quantity"] == 10

    def test_update_part_not_found(self, db_session):
        with pytest.raises(ResourceNotFoundException):
            update_part(db_session, 999, {"name": "nope"})


class TestDeletePart:
    def test_delete_part(self, db_session):
        create_part(db_session, {"name": "Delete-Me", "part_number": "DEL-001"})
        result = delete_part(db_session, 1)
        assert result["success"] is True

        with pytest.raises(ResourceNotFoundException):
            get_part(db_session, 1)

    def test_delete_part_not_found(self, db_session):
        with pytest.raises(ResourceNotFoundException):
            delete_part(db_session, 999)


class TestGetStats:
    def test_stats_empty(self, db_session):
        result = get_stats(db_session)
        assert result["total_parts"] == 0
        assert result["total_quantity"] == 0

    def test_stats_basic(self, db_session):
        create_part(db_session, {"name": "A", "part_number": "A-001", "quantity_in_stock": 10, "unit_price": 100.0})
        create_part(db_session, {"name": "B", "part_number": "B-001", "quantity_in_stock": 5, "unit_price": 200.0})

        result = get_stats(db_session)
        assert result["total_parts"] == 2
        assert result["total_quantity"] == 15
        assert result["total_value"] == 2000.0  # 10*100 + 5*200

    def test_stats_low_stock_count(self, db_session):
        create_part(db_session, {"name": "Enough", "part_number": "P-001", "quantity_in_stock": 10, "min_quantity": 5})
        create_part(db_session, {"name": "Low1", "part_number": "P-002", "quantity_in_stock": 2, "min_quantity": 5})
        create_part(db_session, {"name": "Low2", "part_number": "P-003", "quantity_in_stock": 1, "min_quantity": 3})

        result = get_stats(db_session)
        assert result["low_stock_count"] == 2

    def test_stats_by_category(self, db_session):
        create_part(db_session, {"name": "SFP", "part_number": "SFP-001", "category": "module", "quantity_in_stock": 5})
        create_part(db_session, {"name": "Cable", "part_number": "CBL-001", "category": "cable", "quantity_in_stock": 20})
        create_part(db_session, {"name": "Another-SFP", "part_number": "SFP-002", "category": "module", "quantity_in_stock": 3})

        result = get_stats(db_session)
        assert result["by_category"]["module"] == 8
        assert result["by_category"]["cable"] == 20


class TestCreateMovement:
    def test_movement_in(self, db_session):
        create_part(db_session, {"name": "SFP", "part_number": "SFP-001", "quantity_in_stock": 5})
        result = create_movement(db_session, 1, "in", 10, reason="采购入库", operator="admin")
        assert result["movement_type"] == "in"
        assert result["quantity"] == 10

        # Verify stock updated
        updated = get_part(db_session, 1)
        assert updated["quantity_in_stock"] == 15

    def test_movement_out(self, db_session):
        create_part(db_session, {"name": "SFP", "part_number": "SFP-001", "quantity_in_stock": 10})
        result = create_movement(db_session, 1, "out", 3, reason="维修领用", operator="tech")
        assert result["movement_type"] == "out"
        assert result["quantity"] == 3

        updated = get_part(db_session, 1)
        assert updated["quantity_in_stock"] == 7

    def test_movement_out_insufficient_stock(self, db_session):
        create_part(db_session, {"name": "SFP", "part_number": "SFP-001", "quantity_in_stock": 2})
        with pytest.raises(ValueError) as exc_info:
            create_movement(db_session, 1, "out", 5)
        assert "库存不足" in str(exc_info.value)

    def test_movement_invalid_quantity(self, db_session):
        create_part(db_session, {"name": "SFP", "part_number": "SFP-001"})
        with pytest.raises(ValueError):
            create_movement(db_session, 1, "in", 0)

    def test_movement_invalid_type(self, db_session):
        create_part(db_session, {"name": "SFP", "part_number": "SFP-001"})
        with pytest.raises(ValueError):
            create_movement(db_session, 1, "transfer", 5)

    def test_movement_part_not_found(self, db_session):
        with pytest.raises(ResourceNotFoundException):
            create_movement(db_session, 999, "in", 5)

    def test_movement_depleted_status(self, db_session):
        create_part(db_session, {"name": "SFP", "part_number": "SFP-001", "quantity_in_stock": 3})
        create_movement(db_session, 1, "out", 3)

        updated = get_part(db_session, 1)
        assert updated["status"] == "depleted"

    def test_movement_with_reference(self, db_session):
        create_part(db_session, {"name": "SFP", "part_number": "SFP-001", "quantity_in_stock": 10})
        result = create_movement(
            db_session, 1, "out", 2,
            reason="工单维修", operator="tech", reference="WO-2026-001",
        )
        assert result["reference"] == "WO-2026-001"
        assert result["operator"] == "tech"


class TestListMovements:
    def test_list_movements_empty(self, db_session):
        result = list_movements(db_session)
        assert result["total"] == 0

    def test_list_movements_with_data(self, db_session):
        create_part(db_session, {"name": "SFP", "part_number": "SFP-001", "quantity_in_stock": 10})
        create_movement(db_session, 1, "in", 5, operator="admin")
        create_movement(db_session, 1, "out", 2, operator="tech")

        result = list_movements(db_session)
        assert result["total"] == 2

    def test_list_movements_filter_by_type(self, db_session):
        create_part(db_session, {"name": "SFP", "part_number": "SFP-001", "quantity_in_stock": 10})
        create_movement(db_session, 1, "in", 5, operator="admin")
        create_movement(db_session, 1, "out", 2, operator="tech")

        result = list_movements(db_session, movement_type="out")
        assert result["total"] == 1

    def test_list_movements_filter_by_operator(self, db_session):
        create_part(db_session, {"name": "SFP", "part_number": "SFP-001", "quantity_in_stock": 10})
        create_movement(db_session, 1, "in", 5, operator="admin")
        create_movement(db_session, 1, "in", 3, operator="tech")

        result = list_movements(db_session, operator="admin")
        assert result["total"] == 1


class TestGetMovement:
    def test_get_movement_success(self, db_session):
        create_part(db_session, {"name": "SFP", "part_number": "SFP-001", "quantity_in_stock": 10})
        create_movement(db_session, 1, "in", 5, reason="采购", operator="admin")
        result = get_movement(db_session, 1)
        assert result["reason"] == "采购"
        assert result["operator"] == "admin"

    def test_get_movement_not_found(self, db_session):
        with pytest.raises(ResourceNotFoundException):
            get_movement(db_session, 999)
