"""retire Gen1/Gen2 topology models and wipe stale topology data

Revision ID: f3a4b5c6d7e8
Revises: e2f3g4h5i6j7
Create Date: 2024-06-24

统一到 Gen3 图模型（TopoNode + TopoEdge + DevicePort），退役 Gen1/Gen2：
- 删除 device_links（Gen1 设备链路）
- 删除 fiber_branch_points（Gen2 分支点）
- 删除 fiber_trunk_links（Gen2 主干光缆）
- 清空遗留拓扑数据（topo_edges / topo_nodes / device_ports / device_nodes），
  保留 floor_plans（平面图）。设备需重新放置，放置时自动生成端口与拓扑节点。
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f3a4b5c6d7e8'
down_revision = 'e2f3g4h5i6j7'
branch_labels = None
depends_on = None


def _has_table(bind, name: str) -> bool:
    inspector = sa.inspect(bind)
    return name in inspector.get_table_names()


def upgrade():
    bind = op.get_bind()

    # 1) 清空遗留拓扑数据（保留 floor_plans）
    #    按外键依赖顺序删除：topo_edges -> topo_nodes -> device_ports -> device_nodes
    for table in ('topo_edges', 'topo_nodes', 'device_ports', 'device_nodes'):
        if _has_table(bind, table):
            op.execute(sa.text(f'DELETE FROM {table}'))

    # 2) 删除 Gen1/Gen2 表（含外键，按依赖顺序）
    #    device_links -> fiber_branch_points -> fiber_trunk_links
    if _has_table(bind, 'device_links'):
        op.drop_table('device_links')
    if _has_table(bind, 'fiber_branch_points'):
        op.drop_table('fiber_branch_points')
    if _has_table(bind, 'fiber_trunk_links'):
        op.drop_table('fiber_trunk_links')


def downgrade():
    # 仅重建表结构（无法恢复已清空的数据）

    # fiber_trunk_links
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

    # fiber_branch_points
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

    # device_links
    op.create_table(
        'device_links',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('floor_plan_id', sa.Integer(), nullable=False),
        sa.Column('from_node_id', sa.Integer(), nullable=True),
        sa.Column('to_node_id', sa.Integer(), nullable=False),
        sa.Column('link_role', sa.String(20), nullable=False, server_default='uplink'),
        sa.Column('link_group', sa.String(40), nullable=True),
        sa.Column('link_type', sa.String(20), nullable=False, server_default='fiber'),
        sa.Column('waypoints', sa.Text(), nullable=True),
        sa.Column('branch_point_id', sa.Integer(), nullable=True),
        sa.Column('logical_uplink_device_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['floor_plan_id'], ['floor_plans.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['from_node_id'], ['device_nodes.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['to_node_id'], ['device_nodes.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['branch_point_id'], ['fiber_branch_points.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['logical_uplink_device_id'], ['devices.id'], ondelete='SET NULL'),
    )
    op.create_index('ix_device_links_floor_plan_id', 'device_links', ['floor_plan_id'])
    op.create_index('ix_device_links_from_node_id', 'device_links', ['from_node_id'])
    op.create_index('ix_device_links_to_node_id', 'device_links', ['to_node_id'])
    op.create_index('ix_device_links_link_group', 'device_links', ['link_group'])
    op.create_index('ix_device_links_branch_point_id', 'device_links', ['branch_point_id'])
