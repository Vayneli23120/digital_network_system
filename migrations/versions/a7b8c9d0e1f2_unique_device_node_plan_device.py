"""add unique constraint on device_nodes(floor_plan_id, device_id)

Revision ID: a7b8c9d0e1f2
Revises: f3a4b5c6d7e8
Create Date: 2026-06-24

防止同一设备在同一平面图上被重复放置（双击/并发导致的重复 DeviceNode）。
- 先按 (floor_plan_id, device_id) 去重，保留最小 id 的那一行；
- 再添加唯一约束 uq_device_node_plan_device。
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a7b8c9d0e1f2'
down_revision = 'f3a4b5c6d7e8'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()

    # 1. 去重：删除同一 (floor_plan_id, device_id) 下 id 较大的重复行，保留最早的一行
    bind.execute(sa.text(
        """
        DELETE FROM device_nodes
        WHERE id NOT IN (
            SELECT min_id FROM (
                SELECT MIN(id) AS min_id
                FROM device_nodes
                GROUP BY floor_plan_id, device_id
            ) AS keep
        )
        """
    ))

    # 2. 添加唯一约束（batch 模式兼容 SQLite 与 PostgreSQL）
    with op.batch_alter_table('device_nodes') as batch_op:
        batch_op.create_unique_constraint(
            'uq_device_node_plan_device', ['floor_plan_id', 'device_id']
        )


def downgrade():
    with op.batch_alter_table('device_nodes') as batch_op:
        batch_op.drop_constraint('uq_device_node_plan_device', type_='unique')
