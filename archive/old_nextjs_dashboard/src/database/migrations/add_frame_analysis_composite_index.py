#!/usr/bin/env python3
"""
Create composite index on (result_id, frame_number) for frame_analysis table.
This is a lightweight migration-style script. In Alembic, this would be an upgrade step.
"""

import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
import os

DATABASE_URL = os.getenv(
	"DATABASE_URL",
	"postgresql+asyncpg://secureai:secureai_password@localhost:5432/secureai_db",
)

INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_frame_result_frame
ON frame_analysis (result_id, frame_number);
"""


async def main() -> None:
	engine = create_async_engine(DATABASE_URL, echo=False, pool_pre_ping=True)
	async with engine.begin() as conn:
		await conn.execute(text(INDEX_SQL))
	print("Composite index idx_frame_result_frame ensured.")


if __name__ == "__main__":
	asyncio.run(main())
