"""add per-scenario connected-call cost

Revision ID: 0008_scenario_cost_per_connected
Revises: 0007_agent_filter_indexes
Create Date: 2026-02-25 10:15:00.000000
"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "0008_scenario_cost_per_connected"
down_revision = "0007_agent_filter_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE scenarios ADD COLUMN IF NOT EXISTS cost_per_connected INTEGER")
    op.execute(
        """
        UPDATE scenarios AS s
        SET cost_per_connected = COALESCE(cfg.cost_per_connected, 150)
        FROM schedule_configs AS cfg
        WHERE s.company_id = cfg.company_id
          AND s.cost_per_connected IS NULL
        """
    )
    op.execute("UPDATE scenarios SET cost_per_connected = 150 WHERE cost_per_connected IS NULL")


def downgrade() -> None:
    op.execute("ALTER TABLE scenarios DROP COLUMN IF EXISTS cost_per_connected")
