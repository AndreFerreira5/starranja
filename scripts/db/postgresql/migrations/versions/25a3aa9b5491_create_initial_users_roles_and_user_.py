"""Create initial users, roles, and user_roles tables"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision = '...'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # --- 1. 'roles' Table ---
    op.create_table(
        'roles',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('name', sa.String(50), nullable=False, unique=True)
    )

    # --- 2. 'users' Table ---
    op.create_table(
        'users',
        sa.Column('id',
                  UUID(as_uuid=True),
                  primary_key=True,
                  server_default=sa.text('uuid_generate_v4()')
                  ),
        sa.Column('username',
                  sa.String(255),
                  nullable=False,
                  unique=True
                  ),
        sa.Column('email',
                  sa.String(255),
                  nullable=True,
                  unique=True
                  ),
        sa.Column('password_hash',
                  sa.String(255)
                  , nullable=False
                  ),
        sa.Column('full_name',
                  sa.String(255),
                  nullable=False
                  ),
        sa.Column('created_at',
                  sa.TIMESTAMP(timezone=True),
                  nullable=False,
                  server_default=sa.text('NOW()')
                  ),
        sa.Column('updated_at',
                  sa.TIMESTAMP(timezone=True),
                  nullable=False,
                  server_default=sa.text('NOW()')
                  )
    )

    # --- 3. 'user_roles' Junction Table ---
    op.create_table(
        'user_roles',
        sa.Column('user_id',
                  UUID(as_uuid=True),
                  sa.ForeignKey('users.id', ondelete='CASCADE'),
                  primary_key=True
                  ),
        sa.Column('role_id',
                  sa.Integer,
                  sa.ForeignKey('roles.id', ondelete='CASCADE'),
                  primary_key=True
                  )
    )


def downgrade():
    # To revert, we drop in the reverse order
    op.drop_table('user_roles')
    op.drop_table('users')
    op.drop_table('roles')
