"""add_notification_groups

Revision ID: n0t1f2y3g4r5
Revises: fe499cd6b6d6
Create Date: 2026-08-15 14:30:00

通知模块一期（v1.1）：用户组/排班/分发规则/升级策略/通知日志
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'n0t1f2y3g4r5'
down_revision: Union[str, Sequence[str], None] = 'f0a1b2c3d4e5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _create(table: str, *cols) -> None:
    """幂等建表（仓库迁移约定：已存在时跳过）。"""
    try:
        op.create_table(table, *cols)
    except Exception:
        pass


def upgrade() -> None:
    """Upgrade schema."""

    # ===== 用户组 =====
    _create('user_groups',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.String(length=500), nullable=True),
        sa.Column('is_oncall', sa.Boolean(), server_default='1', nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('user_groups', schema=None) as batch_op:
        batch_op.create_index('ix_user_groups_name', ['name'], unique=True)

    _create('user_group_members',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('group_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(length=100), nullable=False),
        sa.Column('is_leader', sa.Boolean(), server_default='0', nullable=True),
        sa.ForeignKeyConstraint(['group_id'], ['user_groups.id'], ondelete='CASCADE', name='fk_ugm_group'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE', name='fk_ugm_user'),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('user_group_members', schema=None) as batch_op:
        batch_op.create_index('ix_user_group_members_group_id', ['group_id'], unique=False)
        batch_op.create_index('ix_user_group_members_user_id', ['user_id'], unique=False)

    # ===== 排班表 =====
    _create('oncall_schedules',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('group_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(length=100), nullable=False),
        sa.Column('start_at', sa.DateTime(), nullable=False),
        sa.Column('end_at', sa.DateTime(), nullable=True),
        sa.Column('repeat_rule', sa.String(length=20), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['group_id'], ['user_groups.id'], ondelete='CASCADE', name='fk_ocs_group'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE', name='fk_ocs_user'),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('oncall_schedules', schema=None) as batch_op:
        batch_op.create_index('ix_oncall_schedules_group_id', ['group_id'], unique=False)
        batch_op.create_index('ix_oncall_schedules_user_id', ['user_id'], unique=False)

    # ===== 分发规则 =====
    _create('dispatch_rules',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('enabled', sa.Boolean(), server_default='1', nullable=True),
        sa.Column('priority', sa.Integer(), nullable=True),
        sa.Column('source_types', sa.Text(), nullable=True),
        sa.Column('device_types', sa.Text(), nullable=True),
        sa.Column('severities', sa.Text(), nullable=True),
        sa.Column('target_group_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['target_group_id'], ['user_groups.id'], ondelete='SET NULL', name='fk_dr_group'),
        sa.PrimaryKeyConstraint('id'),
    )

    # ===== 升级策略 =====
    _create('escalation_policies',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('enabled', sa.Boolean(), server_default='1', nullable=True),
        sa.Column('levels_json', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )

    # ===== 通知发送日志 =====
    _create('notification_logs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('event_type', sa.String(length=50), nullable=True),
        sa.Column('fault_id', sa.Integer(), nullable=True),
        sa.Column('maintenance_id', sa.Integer(), nullable=True),
        sa.Column('channel', sa.String(length=20), nullable=True),
        sa.Column('recipient', sa.String(length=200), nullable=True),
        sa.Column('title', sa.String(length=300), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('notification_logs', schema=None) as batch_op:
        batch_op.create_index('ix_notification_logs_event_type', ['event_type'], unique=False)
        batch_op.create_index('ix_notification_logs_fault_id', ['fault_id'], unique=False)
        batch_op.create_index('ix_notification_logs_created_at', ['created_at'], unique=False)

    # ===== fault_records 扩展 =====
    with op.batch_alter_table('fault_records', schema=None) as batch_op:
        try:
            batch_op.add_column(sa.Column('group_id', sa.Integer(), nullable=True))
        except Exception:
            pass
        try:
            batch_op.add_column(sa.Column('escalation_level', sa.Integer(), server_default='0', nullable=True))
        except Exception:
            pass
        try:
            batch_op.add_column(sa.Column('escalated_at', sa.DateTime(), nullable=True))
        except Exception:
            pass

    # ===== maintenance_records 扩展 =====
    with op.batch_alter_table('maintenance_records', schema=None) as batch_op:
        try:
            batch_op.add_column(sa.Column('group_id', sa.Integer(), nullable=True))
        except Exception:
            pass
        try:
            batch_op.add_column(sa.Column('escalation_level', sa.Integer(), server_default='0', nullable=True))
        except Exception:
            pass
        try:
            batch_op.add_column(sa.Column('escalated_at', sa.DateTime(), nullable=True))
        except Exception:
            pass


def downgrade() -> None:
    """Downgrade schema."""
    for table in ('notification_logs', 'escalation_policies', 'dispatch_rules',
                  'oncall_schedules', 'user_group_members', 'user_groups'):
        try:
            op.drop_table(table)
        except Exception:
            pass
