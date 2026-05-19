import argparse
import asyncio
import sys
from pathlib import Path

from sqlalchemy import text

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.database import engine
from app.routers.auth import ROLE_ADMIN, ROLE_VISITOR, get_password_hash


def parse_args():
    parser = argparse.ArgumentParser(description="Create a dashboard user.")
    parser.add_argument("--username", required=True, help="Username for the new account")
    parser.add_argument("--password", required=True, help="Password for the new account")
    parser.add_argument(
        "--role",
        choices=[ROLE_ADMIN, ROLE_VISITOR],
        default=ROLE_VISITOR,
        help="Role for the new account",
    )
    return parser.parse_args()


async def main():
    args = parse_args()
    async with engine.begin() as conn:
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS users (
                username VARCHAR(50) PRIMARY KEY,
                hashed_password VARCHAR(255) NOT NULL,
                role VARCHAR(20) NOT NULL DEFAULT 'admin',
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
            )
        """))
        await conn.execute(text("""
            ALTER TABLE users
            ADD COLUMN IF NOT EXISTS role VARCHAR(20) NOT NULL DEFAULT 'admin'
        """))

        existing = await conn.execute(
            text("SELECT username FROM users WHERE username = :username"),
            {"username": args.username},
        )
        if existing.scalar_one_or_none():
            raise SystemExit(f"User '{args.username}' already exists.")

        await conn.execute(
            text("""
                INSERT INTO users (username, hashed_password, role, is_active)
                VALUES (:username, :hashed_password, :role, TRUE)
            """),
            {
                "username": args.username,
                "hashed_password": get_password_hash(args.password),
                "role": args.role,
            },
        )

    await engine.dispose()
    print(f"Created {args.role} user '{args.username}'.")


if __name__ == "__main__":
    asyncio.run(main())
