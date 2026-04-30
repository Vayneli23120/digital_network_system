"""add_fault_maintenance_link_and_planned_maintenance

Revision ID: 0edd00553d29
Revises: 9de5d0857961
Create Date: 2026-04-30 12:40:48.705481

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0edd00553d29'
down_revision: Union[str, Sequence[str], None] = '9de5d0857961'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # SQLite 不支持 ALTER TABLE ADD CONSTRAINT，直接添加列（不创建外键约束）

    # 1. FaultRecord 增加 maintenance_id 字段
    op.add_column('fault_records', sa.Column('maintenance_id', sa.Integer(), nullable=True))

    # 2. MaintenanceRecord 增加 fault_id 字段
    op.add_column('maintenance_records', sa.Column('fault_id', sa.Integer(), nullable=True))

    # 3. 新建 maintenance_plans 表
    op.create_table(
        'maintenance_plans',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('device_id', sa.Integer(), nullable=True),
        sa.Column('device_name', sa.String(length=100), nullable=True),
        sa.Column('plan_type', sa.String(length=20), nullable=False),
        sa.Column('cycle_days', sa.Integer(), nullable=True),
        sa.Column('next_date', sa.DateTime(), nullable=False),
        sa.Column('data_basis', sa.Text(), nullable=True),
        sa.Column('auto_generate', sa.Boolean(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['device_id'], ['devices.id'], ondelete='SET NULL'),
    )
    op.create_index('ix_maintenance_plans_plan_type', 'maintenance_plans', ['plan_type'], unique=False)
    op.create_index('ix_maintenance_plans_next_date', 'maintenance_plans', ['next_date'], unique=False)
    op.create_index('ix_maintenance_plans_status', 'maintenance_plans', ['status'], unique=False)

    # 4. 新建 maintenance_tasks 表
    op.create_table(
        'maintenance_tasks',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('plan_id', sa.Integer(), nullable=True),
        sa.Column('device_id', sa.Integer(), nullable=True),
        sa.Column('device_name', sa.String(length=100), nullable=True),
        sa.Column('task_no', sa.String(length=50), nullable=False),
        sa.Column('scheduled_date', sa.DateTime(), nullable=False),
        sa.Column('actual_date', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('maintenance_id', sa.Integer(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('task_no'),
        sa.ForeignKeyConstraint(['plan_id'], ['maintenance_plans.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['device_id'], ['devices.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['maintenance_id'], ['maintenance_records.id']),
    )
    op.create_index('ix_maintenance_tasks_scheduled_date', 'maintenance_tasks', ['scheduled_date'], unique=False)
    op.create_index('ix_maintenance_tasks_status', 'maintenance_tasks', ['status'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    # 删除 maintenance_tasks 表
    op.drop_index('ix_maintenance_tasks_status', table_name='maintenance_tasks')
    op.drop_index('ix_maintenance_tasks_scheduled_date', table_name='maintenance_tasks')
    op.drop_table('maintenance_tasks')

    # 删除 maintenance_plans 表
    op.drop_index('ix_maintenance_plans_status', table_name='maintenance_plans')
    op.drop_index('ix_maintenance_plans_next_date', table_name='maintenance_plans')
    op.drop_index('ix_maintenance_plans_plan_type', table_name='maintenance_plans')
    op.drop_table('maintenance_plans')

    # 删除新增的字段（SQLite 不需要先删除约束）
    op.drop_column('maintenance_records', 'fault_id')
    op.drop_column('fault_records', 'maintenance_id')