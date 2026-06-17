"""add fiber trunk and branch point tables

Revision ID: d1e2f3g4h5i6
Revises: c1d2e3f4g5h6
Create Date: 2024-06-17

预接式光纤主干+分支拓扑功能：
- 新增 fiber_trunk_links 表（主干光缆）
- 新增 fiber_branch_points 表（分支点）
- DeviceLink 表新增 branch_point_id、logical_uplink_device_id 字段
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd1e2f3g4h5i6'
down_revision = 'c1d2e3f4g5h6'
branch_labels = None
depends_on = None


def upgrade():
    # 创建 fiber_trunk_links 表
    op.create_table(
        'fiber_trunk_links',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('floor_plan_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(50), nullable=True),
        sa.Column('start_x_percent', sa.Float(), nullable=False),
        sa.Column('start_y_percent', sa.Float(), nullable=False),
        sa.Column('start_device_id', sa.Integer(), nullable=True),
        sa.Column('end_x_percent', sa.Float(), nullable=False),
        sa.Column('end_y_percent', sa.Float(), nullable=False),
        sa.Column('waypoints', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['floor_plan_id'], ['floor_plans.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['start_device_id'], ['devices.id'], ondelete='SET NULL'),
    )
    op.create_index('ix_fiber_trunk_links_floor_plan_id', 'fiber_trunk_links', ['floor_plan_id'])

    # 创建 fiber_branch_points 表
    op.create_table(
        'fiber_branch_points',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('trunk_link_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(50), nullable=True),
        sa.Column('position_percent', sa.Float(), nullable=False),
        sa.Column('x_percent', sa.Float(), nullable=True),
        sa.Column('y_percent', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['trunk_link_id'], ['fiber_trunk_links.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_fiber_branch_points_trunk_link_id', 'fiber_branch_points', ['trunk_link_id'])

    # DeviceLink 表新增字段
    op.add_column('device_links', sa.Column('branch_point_id', sa.Integer(), nullable=True))
    op.add_column('device_links', sa.Column('logical_uplink_device_id', sa.Integer(), nullable=True))
    op.create_index('ix_device_links_branch_point_id', 'device_links', ['branch_point_id'])
    op.create_foreign_key(
        'fk_device_links_branch_point_id',
        'device_links', 'fiber_branch_points',
        ['branch_point_id'], ['id'],
        ondelete='SET NULL'
    )
    op.create_foreign_key(
        'fk_device_links_logical_uplink',
        'device_links', 'devices',
        ['logical_uplink_device_id'], ['id'],
        ondelete='SET NULL'
    )


def downgrade():
    # 删除 DeviceLink 新增字段
    op.drop_constraint('fk_device_links_logical_uplink', 'device_links', type_='foreignkey')
    op.drop_constraint('fk_device_links_branch_point_id', 'device_links', type_='foreignkey')
    op.drop_index('ix_device_links_branch_point_id', 'device_links')
    op.drop_column('device_links', 'logical_uplink_device_id')
    op.drop_column('device_links', 'branch_point_id')

    # 删除 fiber_branch_points 表
    op.drop_index('ix_fiber_branch_points_trunk_link_id', 'fiber_branch_points')
    op.drop_table('fiber_branch_points')

    # 删除 fiber_trunk_links 表
    op.drop_index('ix_fiber_trunk_links_floor_plan_id', 'fiber_trunk_links')
    op.drop_table('fiber_trunk_links')