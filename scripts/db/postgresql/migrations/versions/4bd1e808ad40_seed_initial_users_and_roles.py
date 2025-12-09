"""Seed initial users and roles"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID
import argon2
from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = '4bd1e808ad40'
down_revision: Union[str, Sequence[str], None] = '1ee74fe46987'
branch_labels = None
depends_on = None


def hash_password(plain_password: str) -> str:
    ph = argon2.PasswordHasher(
        time_cost=2,
        memory_cost=19456,
        parallelism=1,
        hash_len=16,
        salt_len=16,
        type=argon2.Type.ID,
    )
    return ph.hash(plain_password)


def upgrade():
    # Create ad-hoc table representations
    roles_table = sa.table(
        "roles",
        sa.column("id", sa.Integer),
        sa.column("name", sa.String),
    )

    users_table = sa.table(
        "users",
        sa.column("id", UUID),
        sa.column("username", sa.String),
        sa.column("email", sa.String),
        sa.column("password_hash", sa.String),
        sa.column("full_name", sa.String),
    )

    bind = op.get_bind()

    # 1. Insert Roles (Updated to match Python script)
    # We use names relevant to your app: 'mecanico', 'mecanico_gerente', 'gerente', 'admin'
    existing_roles = bind.execute(sa.text("SELECT name FROM roles")).fetchall()
    existing_role_names = {r[0] for r in existing_roles}

    roles_to_insert = [
        {"name": "mecanico"},
        {"name": "mecanico_gerente"},
        {"name": "gerente"},
        {"name": "admin"},
    ]

    # Filter out existing roles
    final_roles = [r for r in roles_to_insert if r["name"] not in existing_role_names]

    if final_roles:
        op.bulk_insert(roles_table, final_roles)

    # 2. Insert Users
    users_data = [
        {
            "username": "admin_user",
            "email": "admin@starranja.com",
            "password_hash": hash_password("AdminPass123!"),
            "full_name": "System Administrator",
            "role": "admin"
        },
        {
            "username": "manager_user",
            "email": "manager@starranja.com",
            "password_hash": hash_password("ManagerPass123!"),
            "full_name": "Gerente User",
            "role": "gerente"
        },
        {
            "username": "mechanic_user",
            "email": "mechanic@starranja.com",
            "password_hash": hash_password("MechanicPass123!"),
            "full_name": "Mecanico User",
            "role": "mecanico"
        },
    ]

    for user in users_data:
        # Check if user exists
        exists = bind.execute(
            sa.text("SELECT 1 FROM users WHERE email = :email OR username = :username"),
            {"email": user["email"], "username": user["username"]}
        ).scalar()

        if not exists:
            # Insert user
            op.execute(
                users_table.insert().values(
                    username=user["username"],
                    email=user["email"],
                    password_hash=user["password_hash"],
                    full_name=user["full_name"]
                )
            )

    # 3. Insert User-Role Mappings
    # Maps the users created above to the correct roles
    op.execute(
        sa.text("""
            INSERT INTO user_roles (user_id, role_id)
            SELECT u.id, r.id
            FROM users u, roles r
            WHERE (u.username, r.name) IN (
                ('admin_user', 'admin'),
                ('manager_user', 'gerente'),
                ('mechanic_user', 'mecanico')
            )
            AND NOT EXISTS (
                SELECT 1 FROM user_roles ur 
                WHERE ur.user_id = u.id AND ur.role_id = r.id
            );
        """)
    )

def downgrade():
    op.execute(sa.text("DELETE FROM user_roles"))
    op.execute(sa.text("DELETE FROM users"))
    # Be careful deleting roles if other users might be using them
    op.execute(sa.text("DELETE FROM roles WHERE name IN ('mecanico', 'mecanico_gerente', 'gerente', 'admin')"))
