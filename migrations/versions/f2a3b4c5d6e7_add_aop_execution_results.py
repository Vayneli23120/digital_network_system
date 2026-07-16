"""add AOP execution result fields

Revision ID: f2a3b4c5d6e7
Revises: e1f2a3b4c5d6
Create Date: 2026-07-16
"""

from alembic import op
import sqlalchemy as sa


revision = "f2a3b4c5d6e7"
down_revision = "e1f2a3b4c5d6"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("aop_projects") as batch_op:
        batch_op.add_column(sa.Column("actual_hours", sa.DECIMAL(precision=8, scale=2), nullable=True))
        batch_op.add_column(sa.Column("actual_cost", sa.DECIMAL(precision=14, scale=2), nullable=True))
        batch_op.add_column(sa.Column("completion_result", sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column("completion_notes", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("completed_at", sa.DateTime(), nullable=True))


def downgrade():
    with op.batch_alter_table("aop_projects") as batch_op:
        batch_op.drop_column("completed_at")
        batch_op.drop_column("completion_notes")
        batch_op.drop_column("completion_result")
        batch_op.drop_column("actual_cost")
        batch_op.drop_column("actual_hours")
