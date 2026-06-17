"""merge heads

Revision ID: 383cadd7b057
Revises: add_modules_field, b7a8c9d0e1f2, d1e2f3g4h5i6, fe499cd6b6d6
Create Date: 2026-06-17 18:29:28.782269

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '383cadd7b057'
down_revision: Union[str, Sequence[str], None] = ('add_modules_field', 'b7a8c9d0e1f2', 'd1e2f3g4h5i6', 'fe499cd6b6d6')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
