"""Add parsed_jd and preferred_skills to jobs table

Revision ID: 20260406_01
Revises: 20260203_01
Create Date: 2026-04-06 00:00:00
"""
from alembic import op
import sqlalchemy as sa

revision = "20260406_01"
down_revision = "20260203_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    column_names = {col["name"] for col in inspector.get_columns("jobs")}

    if "preferred_skills" not in column_names:
        op.add_column(
            "jobs",
            sa.Column("preferred_skills", sa.JSON(), nullable=True),
        )
        op.execute("UPDATE jobs SET preferred_skills = '[]' WHERE preferred_skills IS NULL")

    if "parsed_jd" not in column_names:
        op.add_column(
            "jobs",
            sa.Column("parsed_jd", sa.JSON(), nullable=True),
        )


def downgrade() -> None:
    op.drop_column("jobs", "parsed_jd")
    op.drop_column("jobs", "preferred_skills")
