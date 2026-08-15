"""add_notification_policy

Revision ID: n2o3t4i5f6y7
Revises: n0t1f2y3g4r5
Create Date: 2026-08-15 16:00:00

通知模块二期：渠道/模板/策略/告警事件
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'n2o3t4i5f6y7'
down_revision: Union[str, Sequence[str], None] = 'n0t1f2y3g4r5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _create(table: str, *cols) -> None:
    try:
        op.create_table(table, *cols)
    except Exception:
        pass


def upgrade() -> None:
    """Upgrade schema."""

    _create('notification_channels',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('type', sa.String(length=20), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('enabled', sa.Boolean(), server_default='1', nullable=True),
        sa.Column('config_encrypted', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('notification_channels', schema=None) as batch_op:
        batch_op.create_index('ix_notification_channels_type', ['type'], unique=False)

    _create('notification_templates',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('channel_type', sa.String(length=20), nullable=True),
        sa.Column('subject_tpl', sa.Text(), nullable=True),
        sa.Column('body_tpl', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )

    _create('notification_policies',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('enabled', sa.Boolean(), server_default='1', nullable=True),
        sa.Column('priority', sa.Integer(), nullable=True),
        sa.Column('severities', sa.Text(), nullable=True),
        sa.Column('event_types', sa.Text(), nullable=True),
        sa.Column('target_type', sa.String(length=20), nullable=True),
        sa.Column('target_id', sa.Integer(), nullable=True),
        sa.Column('channels', sa.Text(), nullable=True),
        sa.Column('template_id', sa.Integer(), nullable=True),
        sa.Column('rate_limit_window_s', sa.Integer(), nullable=True),
        sa.Column('rate_limit_max', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['template_id'], ['notification_templates.id'], ondelete='SET NULL', name='fk_np_template'),
        sa.PrimaryKeyConstraint('id'),
    )

    _create('alert_events',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('source_type', sa.String(length=30), nullable=True),
        sa.Column('event_type', sa.String(length=50), nullable=True),
        sa.Column('fingerprint', sa.String(length=200), nullable=False),
        sa.Column('dedup_key', sa.String(length=200), nullable=True),
        sa.Column('severity', sa.String(length=20), nullable=True),
        sa.Column('labels_json', sa.Text(), nullable=True),
        sa.Column('annotations_json', sa.Text(), nullable=True),
        sa.Column('silenced', sa.Boolean(), server_default='0', nullable=True),
        sa.Column('suppressed_by', sa.String(length=200), nullable=True),
        sa.Column('fault_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('alert_events', schema=None) as batch_op:
        batch_op.create_index('ix_alert_events_source_type', ['source_type'], unique=False)
        batch_op.create_index('ix_alert_events_dedup_key', ['dedup_key'], unique=True)
        batch_op.create_index('ix_alert_events_created_at', ['created_at'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    for table in ('alert_events', 'notification_policies', 'notification_templates', 'notification_channels'):
        try:
            op.drop_table(table)
        except Exception:
            pass
