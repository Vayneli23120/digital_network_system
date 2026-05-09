"""add_auto_status_fields

Revision ID: b7a8c9d0e1f2
Revises: fe499cd6b6d6
Create Date: 2026-05-09 08:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7a8c9d0e1f2'
down_revision: Union[str, Sequence[str], None] = None  # 独立迁移，不依赖版本链
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - 添加半自动状态机字段"""
    with op.batch_alter_table('maintenance_records', schema=None) as batch_op:
        # 诊断信息字段
        try:
            batch_op.add_column(sa.Column('diagnosis_text', sa.Text(), nullable=True))
        except Exception:
            pass
        try:
            batch_op.add_column(sa.Column('diagnosis_result', sa.String(50), nullable=True))
        except Exception:
            pass

        # 维修动作字段
        try:
            batch_op.add_column(sa.Column('repair_actions', sa.Text(), nullable=True))
        except Exception:
            pass

        # 验证信息字段
        try:
            batch_op.add_column(sa.Column('verification_result', sa.String(20), nullable=True))
        except Exception:
            pass
        try:
            batch_op.add_column(sa.Column('verification_notes', sa.Text(), nullable=True))
        except Exception:
            pass
        try:
            batch_op.add_column(sa.Column('verify_passed', sa.Boolean(), nullable=True, server_default='0'))
        except Exception:
            pass


def downgrade() -> None:
    """Downgrade schema - 移除半自动状态机字段"""
    with op.batch_alter_table('maintenance_records', schema=None) as batch_op:
        try:
            batch_op.drop_column('verify_passed')
        except Exception:
            pass
        try:
            batch_op.drop_column('verification_notes')
        except Exception:
            pass
        try:
            batch_op.drop_column('verification_result')
        except Exception:
            pass
        try:
            batch_op.drop_column('repair_actions')
        except Exception:
            pass
        try:
            batch_op.drop_column('diagnosis_result')
        except Exception:
            pass
        try:
            batch_op.drop_column('diagnosis_text')
        except Exception:
            pass