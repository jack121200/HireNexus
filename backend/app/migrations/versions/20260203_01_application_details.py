"""Add application details json field

Revision ID: 20260203_01
Revises: 20260127_01_initial_schema
Create Date: 2026-02-03 00:00:00
"""
from alembic import op
import sqlalchemy as sa

revision = "20260203_01"
down_revision = "20260127_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    column_names = {col["name"] for col in inspector.get_columns("applications")}
    if "application_details" not in column_names:
        op.add_column("applications", sa.Column("application_details", sa.JSON(), nullable=True))

    op.execute("UPDATE applications SET application_details = '{}' WHERE application_details IS NULL")
    op.alter_column(
        "applications",
        "application_details",
        existing_type=sa.JSON(),
        nullable=False,
    )


def downgrade() -> None:
    op.drop_column("applications", "application_details")
