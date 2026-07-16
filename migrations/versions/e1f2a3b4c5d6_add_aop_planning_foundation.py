"""add AOP planning foundation

Revision ID: e1f2a3b4c5d6
Revises: d0e1f2a3b4c5
Create Date: 2026-07-16
"""

from alembic import op
import sqlalchemy as sa


revision = "e1f2a3b4c5d6"
down_revision = "d0e1f2a3b4c5"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "aop_programs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="draft", nullable=False),
        sa.Column("owner", sa.String(length=100), nullable=True),
        sa.Column("currency", sa.String(length=3), server_default="CNY", nullable=False),
        sa.Column("budget_amount", sa.DECIMAL(precision=14, scale=2), server_default="0", nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("year", "version", name="uq_aop_program_year_version"),
    )
    op.create_index("ix_aop_programs_year", "aop_programs", ["year"], unique=False)
    op.create_index("ix_aop_programs_status", "aop_programs", ["status"], unique=False)

    op.create_table(
        "aop_maintenance_windows",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("program_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("window_type", sa.String(length=30), nullable=False),
        sa.Column("start_at", sa.DateTime(), nullable=False),
        sa.Column("end_at", sa.DateTime(), nullable=False),
        sa.Column("timezone", sa.String(length=64), server_default="Asia/Shanghai", nullable=False),
        sa.Column("max_parallel_tasks", sa.Integer(), server_default="1", nullable=False),
        sa.Column("status", sa.String(length=20), server_default="draft", nullable=False),
        sa.Column("owner", sa.String(length=100), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint("end_at > start_at", name="ck_aop_window_valid_range"),
        sa.CheckConstraint("max_parallel_tasks > 0", name="ck_aop_window_parallel_positive"),
        sa.ForeignKeyConstraint(["program_id"], ["aop_programs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_aop_window_program_start",
        "aop_maintenance_windows",
        ["program_id", "start_at"],
        unique=False,
    )
    op.create_index(
        "ix_aop_maintenance_windows_window_type",
        "aop_maintenance_windows",
        ["window_type"],
        unique=False,
    )
    op.create_index(
        "ix_aop_maintenance_windows_start_at",
        "aop_maintenance_windows",
        ["start_at"],
        unique=False,
    )
    op.create_index(
        "ix_aop_maintenance_windows_end_at",
        "aop_maintenance_windows",
        ["end_at"],
        unique=False,
    )
    op.create_index(
        "ix_aop_maintenance_windows_status",
        "aop_maintenance_windows",
        ["status"],
        unique=False,
    )

    op.create_table(
        "aop_projects",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("program_id", sa.Integer(), nullable=False),
        sa.Column("project_code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("project_type", sa.String(length=30), nullable=False),
        sa.Column("device_id", sa.Integer(), nullable=True),
        sa.Column("device_name", sa.String(length=100), nullable=True),
        sa.Column("asset_scope", sa.Text(), nullable=True),
        sa.Column("current_version", sa.String(length=100), nullable=True),
        sa.Column("target_version", sa.String(length=100), nullable=True),
        sa.Column("planned_start", sa.DateTime(), nullable=False),
        sa.Column("planned_end", sa.DateTime(), nullable=True),
        sa.Column("preferred_window_type", sa.String(length=30), nullable=True),
        sa.Column("estimated_hours", sa.DECIMAL(precision=8, scale=2), server_default="1", nullable=False),
        sa.Column("estimated_cost", sa.DECIMAL(precision=14, scale=2), server_default="0", nullable=False),
        sa.Column("owner", sa.String(length=100), nullable=True),
        sa.Column("priority", sa.String(length=10), server_default="P3", nullable=False),
        sa.Column("risk_level", sa.String(length=20), server_default="medium", nullable=False),
        sa.Column("approval_status", sa.String(length=20), server_default="draft", nullable=False),
        sa.Column("status", sa.String(length=20), server_default="proposed", nullable=False),
        sa.Column("dependencies", sa.Text(), nullable=True),
        sa.Column("business_justification", sa.Text(), nullable=True),
        sa.Column("rollback_plan", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["program_id"], ["aop_programs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("program_id", "project_code", name="uq_aop_project_program_code"),
    )
    op.create_index(
        "idx_aop_project_program_status",
        "aop_projects",
        ["program_id", "status"],
        unique=False,
    )
    op.create_index("ix_aop_projects_project_type", "aop_projects", ["project_type"], unique=False)
    op.create_index("ix_aop_projects_planned_start", "aop_projects", ["planned_start"], unique=False)
    op.create_index("ix_aop_projects_priority", "aop_projects", ["priority"], unique=False)
    op.create_index("ix_aop_projects_risk_level", "aop_projects", ["risk_level"], unique=False)
    op.create_index("ix_aop_projects_approval_status", "aop_projects", ["approval_status"], unique=False)
    op.create_index("ix_aop_projects_status", "aop_projects", ["status"], unique=False)

    with op.batch_alter_table("maintenance_tasks") as batch_op:
        batch_op.add_column(sa.Column("aop_project_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("maintenance_window_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("scheduled_end", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column("estimated_hours", sa.DECIMAL(precision=8, scale=2), nullable=True))
        batch_op.add_column(
            sa.Column(
                "schedule_source",
                sa.String(length=30),
                server_default="legacy_plan",
                nullable=False,
            )
        )
        batch_op.create_foreign_key(
            "fk_maintenance_task_aop_project",
            "aop_projects",
            ["aop_project_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_foreign_key(
            "fk_maintenance_task_aop_window",
            "aop_maintenance_windows",
            ["maintenance_window_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index(
            "ix_maintenance_tasks_aop_project_id",
            ["aop_project_id"],
            unique=True,
        )
        batch_op.create_index(
            "ix_maintenance_tasks_maintenance_window_id",
            ["maintenance_window_id"],
            unique=False,
        )
        batch_op.create_index(
            "ix_maintenance_tasks_schedule_source",
            ["schedule_source"],
            unique=False,
        )


def downgrade():
    with op.batch_alter_table("maintenance_tasks") as batch_op:
        batch_op.drop_index("ix_maintenance_tasks_schedule_source")
        batch_op.drop_index("ix_maintenance_tasks_maintenance_window_id")
        batch_op.drop_index("ix_maintenance_tasks_aop_project_id")
        batch_op.drop_constraint("fk_maintenance_task_aop_window", type_="foreignkey")
        batch_op.drop_constraint("fk_maintenance_task_aop_project", type_="foreignkey")
        batch_op.drop_column("schedule_source")
        batch_op.drop_column("estimated_hours")
        batch_op.drop_column("scheduled_end")
        batch_op.drop_column("maintenance_window_id")
        batch_op.drop_column("aop_project_id")

    op.drop_index("ix_aop_projects_status", table_name="aop_projects")
    op.drop_index("ix_aop_projects_approval_status", table_name="aop_projects")
    op.drop_index("ix_aop_projects_risk_level", table_name="aop_projects")
    op.drop_index("ix_aop_projects_priority", table_name="aop_projects")
    op.drop_index("ix_aop_projects_planned_start", table_name="aop_projects")
    op.drop_index("ix_aop_projects_project_type", table_name="aop_projects")
    op.drop_index("idx_aop_project_program_status", table_name="aop_projects")
    op.drop_table("aop_projects")

    op.drop_index("ix_aop_maintenance_windows_status", table_name="aop_maintenance_windows")
    op.drop_index("ix_aop_maintenance_windows_end_at", table_name="aop_maintenance_windows")
    op.drop_index("ix_aop_maintenance_windows_start_at", table_name="aop_maintenance_windows")
    op.drop_index("ix_aop_maintenance_windows_window_type", table_name="aop_maintenance_windows")
    op.drop_index("idx_aop_window_program_start", table_name="aop_maintenance_windows")
    op.drop_table("aop_maintenance_windows")

    op.drop_index("ix_aop_programs_status", table_name="aop_programs")
    op.drop_index("ix_aop_programs_year", table_name="aop_programs")
    op.drop_table("aop_programs")