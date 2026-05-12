"""add modules field to devices

Revision ID: add_modules_field
Revises: c1d2e3f4g5h6
Create Date: 2024-01-20

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_modules_field'
down_revision = 'c1d2e3f4g5h6'
branch_labels = None
depends_on = None


def upgrade():
    # 添加 modules 字段
    op.add_column('devices', sa.Column('modules', sa.Text(), nullable=True))


def downgrade():
    # 移除 modules 字段
    op.drop_column('devices', 'modules')