"""add serial_number to spare_part_movements

Revision ID: add_sn_to_movements
Revises: a1b2c3d4e5f6
Create Date: 2026-05-07

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_sn_to_movements'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade():
    # Add serial_number column to spare_part_movements table
    op.add_column('spare_part_movements', sa.Column('serial_number', sa.String(100), nullable=True))


def downgrade():
    # Remove serial_number column from spare_part_movements table
    op.drop_column('spare_part_movements', 'serial_number')