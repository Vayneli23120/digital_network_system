"""add_maintenance_status_system

Revision ID: fe499cd6b6d6
Revises: add_sn_to_movements
Create Date: 2026-05-09 00:06:16.601875

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fe499cd6b6d6'
down_revision: Union[str, Sequence[str], None] = 'add_sn_to_movements'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 维修事件时间线表（如果不存在）
    try:
        op.create_table('maintenance_events',
            sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
            sa.Column('maintenance_id', sa.Integer(), nullable=False),
            sa.Column('event_type', sa.String(length=20), nullable=False),
            sa.Column('event_time', sa.DateTime(), nullable=False),
            sa.Column('operator', sa.String(length=100), nullable=True),
            sa.Column('notes', sa.String(length=500), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['maintenance_id'], ['maintenance_records.id'], ondelete='CASCADE', name='fk_maintenance_events_maintenance_id'),
            sa.PrimaryKeyConstraint('id')
        )
        with op.batch_alter_table('maintenance_events', schema=None) as batch_op:
            batch_op.create_index('ix_maintenance_events_event_time', ['event_time'], unique=False)
            batch_op.create_index('ix_maintenance_events_maintenance_id', ['maintenance_id'], unique=False)
    except Exception:
        pass  # 表已存在

    # 添加维修记录状态字段
    with op.batch_alter_table('maintenance_records', schema=None) as batch_op:
        try:
            batch_op.add_column(sa.Column('status', sa.String(length=20), nullable=True, server_default='created'))
            batch_op.create_index('ix_maintenance_records_status', ['status'], unique=False)
        except Exception:
            pass
        try:
            batch_op.add_column(sa.Column('diagnosing_at', sa.DateTime(), nullable=True))
        except Exception:
            pass
        try:
            batch_op.add_column(sa.Column('repairing_at', sa.DateTime(), nullable=True))
        except Exception:
            pass
        try:
            batch_op.add_column(sa.Column('verifying_at', sa.DateTime(), nullable=True))
        except Exception:
            pass
        try:
            batch_op.add_column(sa.Column('completed_at', sa.DateTime(), nullable=True))
        except Exception:
            pass
        try:
            batch_op.add_column(sa.Column('cancelled_at', sa.DateTime(), nullable=True))
        except Exception:
            pass
        try:
            batch_op.add_column(sa.Column('current_owner', sa.String(length=100), nullable=True))
        except Exception:
            pass
        try:
            batch_op.add_column(sa.Column('priority', sa.String(length=10), nullable=True, server_default='P3'))
            batch_op.create_index('ix_maintenance_records_priority', ['priority'], unique=False)
        except Exception:
            pass
        try:
            batch_op.add_column(sa.Column('sla_deadline', sa.DateTime(), nullable=True))
        except Exception:
            pass

    # 为现有记录设置默认状态
    try:
        op.execute("UPDATE maintenance_records SET status='created' WHERE status IS NULL OR status = ''")
        op.execute("UPDATE maintenance_records SET priority='P3' WHERE priority IS NULL OR priority = ''")
    except Exception:
        pass


def downgrade() -> None:
    """Downgrade schema."""
    # 删除维修记录状态字段
    with op.batch_alter_table('maintenance_records', schema=None) as batch_op:
        try:
            batch_op.drop_index('ix_maintenance_records_status')
        except Exception:
            pass
        try:
            batch_op.drop_index('ix_maintenance_records_priority')
        except Exception:
            pass
        try:
            batch_op.drop_column('sla_deadline')
        except Exception:
            pass
        try:
            batch_op.drop_column('priority')
        except Exception:
            pass
        try:
            batch_op.drop_column('current_owner')
        except Exception:
            pass
        try:
            batch_op.drop_column('cancelled_at')
        except Exception:
            pass
        try:
            batch_op.drop_column('completed_at')
        except Exception:
            pass
        try:
            batch_op.drop_column('verifying_at')
        except Exception:
            pass
        try:
            batch_op.drop_column('repairing_at')
        except Exception:
            pass
        try:
            batch_op.drop_column('diagnosing_at')
        except Exception:
            pass
        try:
            batch_op.drop_column('status')
        except Exception:
            pass

    # 删除维修事件时间线表
    try:
        with op.batch_alter_table('maintenance_events', schema=None) as batch_op:
            batch_op.drop_index('ix_maintenance_events_maintenance_id')
            batch_op.drop_index('ix_maintenance_events_event_time')
        op.drop_table('maintenance_events')
    except Exception:
        pass