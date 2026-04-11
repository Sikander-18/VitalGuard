import asyncio
import logging
from backend.db.database import engine, Base
from backend.db import models

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def init_db():
    logger.info("Initializing database...")
    async with engine.begin() as conn:
        # This will create all tables defined in models.py
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database initialized successfully.")

if __name__ == "__main__":
    asyncio.run(init_db())
