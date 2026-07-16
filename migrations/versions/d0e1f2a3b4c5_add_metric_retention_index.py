"""add device metric retention index

Revision ID: d0e1f2a3b4c5
Revises: b8c9d0e1f2a3
Create Date: 2026-07-16
"""

from alembic import op


revision = "d0e1f2a3b4c5"
down_revision = "b8c9d0e1f2a3"
branch_labels = None
depends_on = None


def upgrade():
    op.create_index(
        "idx_device_metric_ts",
        "device_metric_samples",
        ["ts"],
        unique=False,
    )


def downgrade():
    op.drop_index("idx_device_metric_ts", table_name="device_metric_samples")