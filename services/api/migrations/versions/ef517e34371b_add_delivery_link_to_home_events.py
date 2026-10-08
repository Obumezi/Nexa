"""add delivery link to home events

Revision ID: ef517e34371b
Revises: 045904046832
Create Date: 2026-09-27 23:00:30.088604

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'ef517e34371b'
down_revision: str | Sequence[str] | None = '045904046832'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""

    with op.batch_alter_table("home_events", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "related_delivery_id",
                sa.String(length=36),
                nullable=True,
            )
        )
        batch_op.create_foreign_key(
            "fk_home_events_related_delivery_id_deliveries",
            "deliveries",
            ["related_delivery_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    """Downgrade schema."""

    with op.batch_alter_table("home_events", schema=None) as batch_op:
        batch_op.drop_constraint(
            "fk_home_events_related_delivery_id_deliveries",
            type_="foreignkey",
        )
        batch_op.drop_column("related_delivery_id")

    # ### end Alembic commands ###
