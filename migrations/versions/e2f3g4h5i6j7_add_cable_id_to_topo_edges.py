"""add cable_id and cable_no to topo_edges

Revision ID: e2f3g4h5i6j7
Revises: 383cadd7b057
Create Date: 2024-06-23

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e2f3g4h5i6j7'
down_revision = '383cadd7b057'
branch_labels = None
depends_on = None


def upgrade():
    # Add cable_id column to topo_edges
    op.add_column('topo_edges', sa.Column('cable_id', sa.Integer(), nullable=True))
    op.create_index('ix_topo_edges_cable_id', 'topo_edges', ['cable_id'], unique=False)

    # Add cable_no column to topo_edges
    op.add_column('topo_edges', sa.Column('cable_no', sa.String(50), nullable=True))


def downgrade():
    # Remove cable_no column
    op.drop_column('topo_edges', 'cable_no')

    # Remove cable_id column and index
    op.drop_index('ix_topo_edges_cable_id', 'topo_edges')
    op.drop_column('topo_edges', 'cable_id')