"""add api_connectors, data_submissions.version, findings.classification

Revision ID: 0001_sat_sa
Revises:
Create Date: 2026-09-29

This is the first SAT-SA migration. It adds only the new objects needed
for the API connector feature, dataset versioning, and negative-space
classification. Existing tables are created by Base.metadata.create_all()
and are not touched here.

Idempotent: each operation is guarded so re-running is safe on a DB that
already has the columns/table.
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0001_sat_sa"
down_revision = None
branch_labels = None
depends_on = None


def _has_column(inspector, table: str, column: str) -> bool:
    try:
        cols = [c["name"] for c in inspector.get_columns(table)]
    except Exception:
        return False
    return column in cols


def _has_table(inspector, table: str) -> bool:
    try:
        return table in inspector.get_table_names()
    except Exception:
        return False


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # ------------------------------------------------------------------
    # 1. data_submissions.version
    # ------------------------------------------------------------------
    if not _has_column(inspector, "data_submissions", "version"):
        with op.batch_alter_table("data_submissions") as batch:
            batch.add_column(
                sa.Column(
                    "version",
                    sa.Integer(),
                    nullable=False,
                    server_default="1",
                )
            )
        op.create_index(
            "ix_data_submissions_version",
            "data_submissions",
            ["entity_id", "period_id", "file_name", "version"],
            unique=False,
        )

    # ------------------------------------------------------------------
    # 2. findings.classification
    # ------------------------------------------------------------------
    if not _has_column(inspector, "findings", "classification"):
        with op.batch_alter_table("findings") as batch:
            batch.add_column(
                sa.Column("classification", sa.String(length=32), nullable=True)
            )
        op.create_index(
            "ix_findings_classification",
            "findings",
            ["classification"],
            unique=False,
        )

    # ------------------------------------------------------------------
    # 3. api_connectors
    # ------------------------------------------------------------------
    if not _has_table(inspector, "api_connectors"):
        op.create_table(
            "api_connectors",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("name", sa.String(length=128), nullable=False),
            sa.Column("connector_type", sa.String(length=32), nullable=False),
            sa.Column("base_url", sa.String(length=255), nullable=True),
            sa.Column("mode", sa.String(length=32), nullable=False, server_default="PERIODIC_PULL"),
            sa.Column("is_demo", sa.Boolean(), nullable=False, server_default=sa.text("1")),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="CONFIGURED"),
            sa.Column("payload_types", sa.String(length=255), nullable=True),
            sa.Column("last_run_at", sa.DateTime(), nullable=True),
            sa.Column("last_run_summary", sa.JSON(), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )
        op.create_index("ix_api_connectors_status", "api_connectors", ["status"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _has_table(inspector, "api_connectors"):
        op.drop_index("ix_api_connectors_status", table_name="api_connectors")
        op.drop_table("api_connectors")

    if _has_column(inspector, "findings", "classification"):
        op.drop_index("ix_findings_classification", table_name="findings")
        with op.batch_alter_table("findings") as batch:
            batch.drop_column("classification")

    if _has_column(inspector, "data_submissions", "version"):
        op.drop_index("ix_data_submissions_version", table_name="data_submissions")
        with op.batch_alter_table("data_submissions") as batch:
            batch.drop_column("version")