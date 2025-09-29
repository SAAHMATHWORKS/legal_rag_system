# database/postgres_checkpointer.py - CORRECT VERSION
from psycopg_pool import AsyncConnectionPool
from psycopg.rows import dict_row
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver  # ✅ Correct import
from langgraph.checkpoint.memory import MemorySaver
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class PostgresCheckpointer:
    def __init__(self, database_url: str, max_connections: int = 10, min_connections: int = 2):
        self.database_url = database_url
        self.max_connections = max_connections
        self.min_connections = min_connections
        self.pool: Optional[AsyncConnectionPool] = None
        self.checkpointer: Optional[AsyncPostgresSaver] = None  # ✅ Correct type
        self._is_initialized = False

    async def initialize(self) -> bool:
        """Initialize PostgreSQL connection pool and checkpointer"""
        try:
            # Create async connection pool
            self.pool = AsyncConnectionPool(
                conninfo=self.database_url,
                max_size=self.max_connections,
                min_size=self.min_connections,
                kwargs={"row_factory": dict_row, "autocommit": True},
                open=False,
            )
            
            await self.pool.open()
            
            # ✅ CORRECT: Use AsyncPostgresSaver with AsyncConnectionPool
            self.checkpointer = AsyncPostgresSaver(self.pool)
            await self.checkpointer.setup()  # ✅ Async setup method
            
            self._is_initialized = True
            logger.info("✅ PostgreSQL checkpointer initialized successfully with AsyncPostgresSaver")
            return True
            
        except Exception as e:
            logger.error(f"❌ PostgreSQL initialization failed: {e}")
            
            # Fallback to in-memory
            try:
                from langgraph.checkpoint.memory_aio import AsyncMemorySaver  # ✅ Async memory saver
                self.checkpointer = AsyncMemorySaver()
                logger.warning("🔄 Falling back to async in-memory checkpointer")
                self._is_initialized = True
                return True
            except ImportError:
                # Fallback to sync MemorySaver if async not available
                self.checkpointer = MemorySaver()
                logger.warning("🔄 Falling back to sync in-memory checkpointer")
                self._is_initialized = True
                return True
            except Exception as fallback_error:
                logger.error(f"❌ Even fallback failed: {fallback_error}")
                return False

    async def close(self):
        """Close connections with proper cleanup"""
        if self.pool:
            await self.pool.close()
            logger.info("✅ PostgreSQL connection pool closed")
        
        self._is_initialized = False

    async def health_check(self) -> dict:
        """Check the health of the PostgreSQL connection"""
        if not self._is_initialized or not self.pool:
            return {"status": "uninitialized", "healthy": False}
        
        try:
            async with self.pool.connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("SELECT 1")
                    result = await cur.fetchone()
            
            return {
                "status": "healthy", 
                "healthy": True,
                "connection_count": self.pool.size if hasattr(self.pool, 'size') else "unknown"
            }
        except Exception as e:
            return {"status": f"unhealthy: {str(e)}", "healthy": False}

    def is_initialized(self) -> bool:
        """Check if checkpointer is properly initialized"""
        return self._is_initialized and self.checkpointer is not None

    def get_checkpointer(self) -> AsyncPostgresSaver:
        """Get the underlying checkpointer instance"""
        if not self.is_initialized():
            raise RuntimeError("Checkpointer not initialized. Call initialize() first.")
        return self.checkpointer