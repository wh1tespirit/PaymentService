"""outbox pending partial index

Revision ID: b1c7f0a94d12
Revises: e4ea52ab396e
Create Date: 2026-08-19 16:20:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'b1c7f0a94d12'
down_revision: str | Sequence[str] | None = 'e4ea52ab396e'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Меняет индекс по всем статусам на частичный индекс под запрос relay."""
    op.drop_index(op.f('ix_outbox_status'), table_name='outbox')
    op.create_index(
        'ix_outbox_pending',
        'outbox',
        ['created_at'],
        unique=False,
        postgresql_where=sa.text("status = 'pending'"),
    )


def downgrade() -> None:
    op.drop_index('ix_outbox_pending', table_name='outbox')
    op.create_index(op.f('ix_outbox_status'), 'outbox', ['status'], unique=False)
