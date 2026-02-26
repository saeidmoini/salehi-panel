"""add dialer batch item trace table

Revision ID: 0009_dialer_batch_items_trace
Revises: 0008_scenario_cost_per_connected
Create Date: 2026-02-26 11:45:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0009_dialer_batch_items_trace"
down_revision = "0008_scenario_cost_per_connected"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "dialer_batch_items",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("batch_id", sa.String(length=64), nullable=False),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("phone_number_id", sa.Integer(), sa.ForeignKey("numbers.id"), nullable=False),
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reported_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("report_batch_id", sa.String(length=64), nullable=True),
        sa.Column("report_call_result_id", sa.Integer(), sa.ForeignKey("call_results.id"), nullable=True),
        sa.Column("report_attempted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("report_status", sa.String(length=32), nullable=True),
        sa.Column("report_scenario_id", sa.Integer(), nullable=True),
        sa.Column("report_outbound_line_id", sa.Integer(), nullable=True),
        sa.Column("report_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_dialer_batch_items_batch_id", "dialer_batch_items", ["batch_id"], unique=False)
    op.create_index("ix_dialer_batch_items_company_id", "dialer_batch_items", ["company_id"], unique=False)
    op.create_index("ix_dialer_batch_items_phone_number_id", "dialer_batch_items", ["phone_number_id"], unique=False)
    op.create_index(
        "ix_dialer_batch_items_report_call_result_id",
        "dialer_batch_items",
        ["report_call_result_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_dialer_batch_items_report_call_result_id", table_name="dialer_batch_items")
    op.drop_index("ix_dialer_batch_items_phone_number_id", table_name="dialer_batch_items")
    op.drop_index("ix_dialer_batch_items_company_id", table_name="dialer_batch_items")
    op.drop_index("ix_dialer_batch_items_batch_id", table_name="dialer_batch_items")
    op.drop_table("dialer_batch_items")
