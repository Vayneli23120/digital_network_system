"""add_monitor_screen_models

Revision ID: a1b2c3d4e5f6
Revises: 0edd00553d29
Create Date: 2026-05-06 10:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '0edd00553d29'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. devices 表添加 device_type 字段
    op.add_column('devices', sa.Column('device_type', sa.String(50), nullable=True, default='switch'))
    op.create_index('ix_devices_device_type', 'devices', ['device_type'], unique=False)

    # 2. 新建 floor_plans 表
    op.create_table(
        'floor_plans',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('image_path', sa.String(500), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )

    # 3. 新建 device_nodes 表
    op.create_table(
        'device_nodes',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('device_id', sa.Integer(), nullable=False),
        sa.Column('floor_plan_id', sa.Integer(), nullable=False),
        sa.Column('x_percent', sa.DECIMAL(5, 2), nullable=False),
        sa.Column('y_percent', sa.DECIMAL(5, 2), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['device_id'], ['devices.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['floor_plan_id'], ['floor_plans.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_device_nodes_device_id', 'device_nodes', ['device_id'], unique=False)
    op.create_index('ix_device_nodes_floor_plan_id', 'device_nodes', ['floor_plan_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    # 删除 device_nodes 表
    op.drop_index('ix_device_nodes_floor_plan_id', table_name='device_nodes')
    op.drop_index('ix_device_nodes_device_id', table_name='device_nodes')
    op.drop_table('device_nodes')

    # 删除 floor_plans 表
    op.drop_table('floor_plans')

    # 删除 devices 表的 device_type 字段
    op.drop_index('ix_devices_device_type', table_name='devices')
    op.drop_column('devices', 'device_type')