import asyncio
import sys
from pathlib import Path

# Add project root to path BEFORE imports
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import create_async_engine  # noqa: E402

from src.config import settings  # noqa: E402


async def init_roles():
    """Initialize the 4 predefined roles in the database"""
    engine = create_async_engine(str(settings.database.AUTH_DATABASE_URL))

    async with engine.begin() as conn:
        await conn.execute(
            text("""
            INSERT INTO roles (name) VALUES
                ('mecanico'),
                ('mecanico_gerente'),
                ('gerente'),
                ('admin')
            ON CONFLICT (name) DO NOTHING;
        """)
        )

        print("Roles initialized successfully!")

        result = await conn.execute(text("SELECT id, name FROM roles ORDER BY id"))
        roles = result.fetchall()

        print("\nAvailable roles:")
        for role in roles:
            print(f"  ID {role[0]}: {role[1]}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(init_roles())
