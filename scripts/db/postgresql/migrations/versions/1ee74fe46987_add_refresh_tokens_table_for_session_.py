"""Add refresh_tokens table for session management

Revision ID: 1ee74fe46987
Revises: ...
Create Date: 2025-11-05 15:35:41.348990

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision: str = "1ee74fe46987"
down_revision: str | Sequence[str] | None = "..."
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade():
    op.create_table(
        "refresh_tokens",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(255), nullable=False, unique=True),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("is_revoked", sa.Boolean, nullable=False, server_default=sa.text("false")),
    )


def downgrade():
    op.drop_table("refresh_tokens")
    pass
