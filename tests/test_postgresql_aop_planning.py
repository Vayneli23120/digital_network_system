"""PostgreSQL concurrency validation for annual AOP task generation."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from threading import Barrier
from uuid import uuid4

import pytest

from app.features.planned_maintenance.aop_router import schedule_program
from app.shared.models import (
    AopMaintenanceWindow,
    AopProgram,
    AopProject,
    MaintenanceTask,
)


@pytest.mark.postgresql
def test_concurrent_aop_generation_creates_one_task(db_manager):
    test_id = uuid4().hex
    setup_session = db_manager.get_session()
    program = AopProgram(
        year=2099,
        version=int(test_id[:7], 16),
        name=f"AOP-PG-Program-{test_id}",
        status="approved",
    )
    setup_session.add(program)
    setup_session.flush()
    window = AopMaintenanceWindow(
        program_id=program.id,
        name=f"AOP-PG-Window-{test_id}",
        window_type="shutdown",
        start_at=datetime(2099, 1, 1, 0),
        end_at=datetime(2099, 1, 1, 8),
        max_parallel_tasks=1,
        status="approved",
    )
    project = AopProject(
        program_id=program.id,
        project_code=f"AOP-PG-{test_id}",
        name=f"AOP-PG-Project-{test_id}",
        project_type="upgrade",
        planned_start=datetime(2098, 12, 1),
        preferred_window_type="shutdown",
        estimated_hours=2,
        approval_status="approved",
    )
    setup_session.add_all([window, project])
    setup_session.commit()
    program_id = program.id
    project_id = project.id
    setup_session.close()

    start_barrier = Barrier(2)

    def generate_from_independent_session():
        session = db_manager.get_session()
        try:
            start_barrier.wait(timeout=15)
            return schedule_program(program_id, session)
        finally:
            session.close()

    verification_session = db_manager.get_session()
    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [
                executor.submit(generate_from_independent_session),
                executor.submit(generate_from_independent_session),
            ]
            results = [future.result(timeout=30) for future in futures]

        assert sorted(len(result["generated_task_ids"]) for result in results) == [0, 1]
        assert sorted(len(result["existing_task_ids"]) for result in results) == [0, 1]

        tasks = verification_session.query(MaintenanceTask).filter(
            MaintenanceTask.aop_project_id == project_id
        ).all()
        returned_task_ids = {
            task_id
            for result in results
            for task_id in result["generated_task_ids"] + result["existing_task_ids"]
        }

        assert len(tasks) == 1
        assert returned_task_ids == {tasks[0].id}
        assert tasks[0].schedule_source == "aop"
    finally:
        verification_session.rollback()
        verification_session.query(MaintenanceTask).filter(
            MaintenanceTask.aop_project_id == project_id
        ).delete(synchronize_session=False)
        verification_session.query(AopProject).filter(
            AopProject.program_id == program_id
        ).delete(synchronize_session=False)
        verification_session.query(AopMaintenanceWindow).filter(
            AopMaintenanceWindow.program_id == program_id
        ).delete(synchronize_session=False)
        verification_session.query(AopProgram).filter(
            AopProgram.id == program_id
        ).delete(synchronize_session=False)
        verification_session.commit()
        verification_session.close()