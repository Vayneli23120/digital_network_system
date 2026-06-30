"""add_device_interface_peer_columns

Revision ID: c30eb4f78004
Revises: a7b8c9d0e1f2
Create Date: 2026-06-30 11:28:10.054470

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'c30eb4f78004'
down_revision: Union[str, Sequence[str], None] = 'a7b8c9d0e1f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('device_interfaces', sa.Column('peer_device_id', sa.Integer(), nullable=True))
    op.add_column('device_interfaces', sa.Column('peer_device_name', sa.String(length=200), nullable=True))
    op.add_column('device_interfaces', sa.Column('peer_ip', sa.String(length=64), nullable=True))
    op.add_column('device_interfaces', sa.Column('peer_if_name', sa.String(length=100), nullable=True))
    op.add_column('device_interfaces', sa.Column('neighbor_source', sa.String(length=20), nullable=True))
    op.add_column('device_interfaces', sa.Column('neighbor_updated_at', sa.DateTime(), nullable=True))
    op.create_index(op.f('ix_device_interfaces_peer_device_id'), 'device_interfaces', ['peer_device_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_device_interfaces_peer_device_id'), table_name='device_interfaces')
    op.drop_column('device_interfaces', 'neighbor_updated_at')
    op.drop_column('device_interfaces', 'neighbor_source')
    op.drop_column('device_interfaces', 'peer_if_name')
    op.drop_column('device_interfaces', 'peer_ip')
    op.drop_column('device_interfaces', 'peer_device_name')
    op.drop_column('device_interfaces', 'peer_device_id')
