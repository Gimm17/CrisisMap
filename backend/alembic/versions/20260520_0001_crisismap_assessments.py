"""create crisismap assessment persistence table

Revision ID: 20260520_0001
Revises:
Create Date: 2026-05-20
"""

from __future__ import annotations

from alembic import op

revision = "20260520_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS crisismap_assessments (
            assessment_id TEXT PRIMARY KEY,
            created_at TIMESTAMPTZ NOT NULL,
            record_json JSONB NOT NULL,
            aoi_geojson JSONB,
            aoi_geom geometry(Polygon, 4326)
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS crisismap_assessments_aoi_gix ON crisismap_assessments USING GIST (aoi_geom)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS crisismap_assessments_aoi_gix")
    op.execute("DROP TABLE IF EXISTS crisismap_assessments")
