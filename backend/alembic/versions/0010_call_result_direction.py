"""add call direction to call results

Revision ID: 0010_call_result_direction
Revises: 0009_dialer_batch_items_trace
Create Date: 2026-02-26 12:05:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0010_call_result_direction"
down_revision = "0009_dialer_batch_items_trace"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE call_results
        ADD COLUMN IF NOT EXISTS call_direction VARCHAR(16) DEFAULT 'OUTBOUND' NOT NULL
        """
    )
    op.execute(
        """
        UPDATE call_results
        SET call_direction = CASE
            WHEN status = 'INBOUND_CALL' THEN 'INBOUND'
            ELSE 'OUTBOUND'
        END
        WHERE call_direction IS NULL OR call_direction = ''
        """
    )
    op.alter_column("call_results", "call_direction", server_default=None)


def downgrade() -> None:
    op.drop_column("call_results", "call_direction")
