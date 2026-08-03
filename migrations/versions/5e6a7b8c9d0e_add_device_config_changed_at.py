"""add device config_changed_at

Revision ID: 5e6a7b8c9d0e
Revises: 5d16fa030a9a
Create Date: 2026-08-03

批次二·步骤5（会话级 SSH 凭证 + 备份提醒）：
- devices.config_changed_at 记录设备配置最后变更时间（部署成功 / 手动标记），
  供「需备份」列表判定「配置已变更需备份」原因。
幂等：仅当列不存在时添加。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5e6a7b8c9d0e'
down_revision: Union[str, Sequence[str], None] = '5d16fa030a9a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(bind, table: str, column: str) -> bool:
    inspector = sa.inspect(bind)
    if table not in inspector.get_table_names():
        return False
    return column in {c['name'] for c in inspector.get_columns(table)}


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    if not _has_column(bind, 'devices', 'config_changed_at'):
        op.add_column('devices', sa.Column('config_changed_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    if _has_column(bind, 'devices', 'config_changed_at'):
        op.drop_column('devices', 'config_changed_at')
