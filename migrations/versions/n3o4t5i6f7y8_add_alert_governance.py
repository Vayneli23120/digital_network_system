"""add_alert_governance

Revision ID: n3o4t5i6f7y8
Revises: n2o3t4i5f6y7
Create Date: 2026-08-15 18:00:00

通知模块三期：故障单静默/抑制字段
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'n3o4t5i6f7y8'
down_revision: Union[str, Sequence[str], None] = 'n2o3t4i5f6y7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('fault_records', schema=None) as batch_op:
        try:
            batch_op.add_column(sa.Column('silenced', sa.Boolean(), server_default='0', nullable=True))
        except Exception:
            pass
        try:
            batch_op.add_column(sa.Column('suppressed_by', sa.String(length=50), nullable=True))
        except Exception:
            pass


def downgrade() -> None:
    with op.batch_alter_table('fault_records', schema=None) as batch_op:
        for col in ('suppressed_by', 'silenced'):
            try:
                batch_op.drop_column(col)
            except Exception:
                pass
