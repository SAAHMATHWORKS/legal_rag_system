from psycopg_pool import AsyncConnectionPool
from psycopg.rows import dict_row
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from config.settings import settings

class PostgresCheckpointer:
    def __init__(self):
        self.pool = None
        self.checkpointer = None

    async def initialize(self):
        """Initialize PostgreSQL connection pool and checkpointer"""
        try:
            self.pool = AsyncConnectionPool(
                conninfo=settings.DATABASE_URL,
                max_size=10,
                min_size=2,
                kwargs={"row_factory": dict_row, "autocommit": True},
                open=False,
            )
            
            await self.pool.open()
            self.checkpointer = AsyncPostgresSaver(self.pool)
            await self.checkpointer.setup()
            
            print("✅ PostgreSQL checkpointer initialized")
            return True
            
        except Exception as e:
            print(f"❌ PostgreSQL initialization failed: {e}")
            return False

    async def close(self):
        """Close PostgreSQL connection pool"""
        if self.pool:
            await self.pool.close()
            print("✅ PostgreSQL connection closed")