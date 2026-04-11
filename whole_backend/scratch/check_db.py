import asyncio
from sqlalchemy import inspect
from backend.db.database import engine

async def check():
    async with engine.connect() as conn:
        def get_columns(sync_conn):
            inspector = inspect(sync_conn)
            return inspector.get_columns("vitals")
            
        columns = await conn.run_sync(get_columns)
        for col in columns:
            print(f"Col: {col['name']} - {col['type']}")

if __name__ == "__main__":
    asyncio.run(check())
