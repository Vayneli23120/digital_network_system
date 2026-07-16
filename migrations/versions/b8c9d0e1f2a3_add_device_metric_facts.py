"""add canonical device metric fact table

Revision ID: b8c9d0e1f2a3
Revises: c30eb4f78004
Create Date: 2026-07-16
"""

from alembic import op
import sqlalchemy as sa


revision = "b8c9d0e1f2a3"
down_revision = "c30eb4f78004"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "device_metric_samples",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("device_id", sa.Integer(), nullable=False),
        sa.Column("ts", sa.DateTime(), nullable=False),
        sa.Column("source", sa.String(length=30), server_default="snmp_live", nullable=False),
        sa.Column("collection_status", sa.String(length=20), server_default="partial", nullable=False),
        sa.Column("cpu_percent", sa.Float(), nullable=True),
        sa.Column("memory_percent", sa.Float(), nullable=True),
        sa.Column("memory_used_mb", sa.Float(), nullable=True),
        sa.Column("memory_total_mb", sa.Float(), nullable=True),
        sa.Column("temperature_c", sa.Float(), nullable=True),
        sa.Column("uptime_days", sa.Integer(), nullable=True),
        sa.Column("interfaces_up", sa.Integer(), nullable=True),
        sa.Column("interfaces_down", sa.Integer(), nullable=True),
        sa.Column("interfaces_total", sa.Integer(), nullable=True),
        sa.Column("total_errors", sa.BigInteger(), nullable=True),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_device_metric_device_ts",
        "device_metric_samples",
        ["device_id", "ts"],
        unique=False,
    )


def downgrade():
    op.drop_index("idx_device_metric_device_ts", table_name="device_metric_samples")
    op.drop_table("device_metric_samples")