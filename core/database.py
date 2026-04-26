"""PostgreSQL database connection and models."""

from datetime import datetime
from typing import Any

import asyncpg
from loguru import logger
from pydantic import BaseModel

from config.settings import get_settings


class User(BaseModel):
    """User model."""

    id: str
    email: str
    api_key: str
    tier: str = "free"
    monthly_budget: float = 10.0
    created_at: datetime


class UsageLog(BaseModel):
    """Usage log model."""

    id: str
    user_id: str
    model: str
    input_tokens: int
    output_tokens: int
    cost: float
    timestamp: datetime


class Tenant(BaseModel):
    """Tenant model."""

    id: str
    name: str
    owner_id: str
    settings: dict[str, Any]


class Database:
    """Async PostgreSQL database client."""

    def __init__(self):
        self._pool: asyncpg.Pool | None = None
        self._settings = get_settings()

    async def connect(self) -> None:
        """Establish database connection pool."""
        self._pool = await asyncpg.create_pool(
            self._settings.database_url,
            min_size=5,
            max_size=20,
            command_timeout=60,
        )
        logger.info("Database pool connected")

    async def disconnect(self) -> None:
        """Close database connection pool."""
        if self._pool:
            await self._pool.close()
            logger.info("Database pool disconnected")

    @property
    def pool(self) -> asyncpg.Pool:
        """Get connection pool, raising error if not connected."""
        if not self._pool:
            raise RuntimeError("Database not connected. Call connect() first.")
        return self._pool

    async def init_tables(self) -> None:
        """Initialize database tables."""
        async with self.pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    email VARCHAR(255) UNIQUE NOT NULL,
                    api_key VARCHAR(64) UNIQUE NOT NULL,
                    tier VARCHAR(50) DEFAULT 'free',
                    monthly_budget DECIMAL(10, 2) DEFAULT 10.0,
                    created_at TIMESTAMP DEFAULT NOW()
                );
            """)

            await conn.execute("""
                CREATE TABLE IF NOT EXISTS usage_logs (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
                    model VARCHAR(100) NOT NULL,
                    input_tokens INT NOT NULL,
                    output_tokens INT NOT NULL,
                    cost DECIMAL(10, 4) NOT NULL,
                    timestamp TIMESTAMP DEFAULT NOW()
                );
            """)

            await conn.execute("""
                CREATE TABLE IF NOT EXISTS tenants (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    name VARCHAR(255) NOT NULL,
                    owner_id UUID REFERENCES users(id) ON DELETE CASCADE,
                    settings JSONB DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT NOW()
                );
            """)

            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_usage_logs_user_id ON usage_logs(user_id);
                CREATE INDEX IF NOT EXISTS idx_usage_logs_timestamp ON usage_logs(timestamp);
                CREATE INDEX IF NOT EXISTS idx_tenants_owner_id ON tenants(owner_id);
            """)

        logger.info("Database tables initialized")

    async def create_user(
        self,
        email: str,
        api_key: str,
        tier: str = "free",
        monthly_budget: float = 10.0,
    ) -> User:
        """Create a new user."""
        async with self.pool.acquire() as conn:
            record = await conn.fetchrow(
                """
                INSERT INTO users (email, api_key, tier, monthly_budget)
                VALUES ($1, $2, $3, $4)
                RETURNING *
                """,
                email,
                api_key,
                tier,
                monthly_budget,
            )
        return User(**dict(record))

    async def get_user_by_api_key(self, api_key: str) -> User | None:
        """Get user by API key."""
        async with self.pool.acquire() as conn:
            record = await conn.fetchrow(
                "SELECT * FROM users WHERE api_key = $1",
                api_key,
            )
        return User(**dict(record)) if record else None

    async def get_user_by_id(self, user_id: str) -> User | None:
        """Get user by ID."""
        async with self.pool.acquire() as conn:
            record = await conn.fetchrow(
                "SELECT * FROM users WHERE id = $1",
                user_id,
            )
        return User(**dict(record)) if record else None

    async def update_user_budget(self, user_id: str, budget: float) -> None:
        """Update user's monthly budget."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                "UPDATE users SET monthly_budget = $1 WHERE id = $2",
                budget,
                user_id,
            )

    async def log_usage(
        self,
        user_id: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cost: float,
    ) -> UsageLog:
        """Log API usage."""
        async with self.pool.acquire() as conn:
            record = await conn.fetchrow(
                """
                INSERT INTO usage_logs (user_id, model, input_tokens, output_tokens, cost)
                VALUES ($1, $2, $3, $4, $5)
                RETURNING *
                """,
                user_id,
                model,
                input_tokens,
                output_tokens,
                cost,
            )
        return UsageLog(**dict(record))

    async def get_user_monthly_cost(self, user_id: str) -> float:
        """Get user's total cost for current month."""
        async with self.pool.acquire() as conn:
            result = await conn.fetchval(
                """
                SELECT COALESCE(SUM(cost), 0)
                FROM usage_logs
                WHERE user_id = $1
                AND EXTRACT(MONTH FROM timestamp) = EXTRACT(MONTH FROM NOW())
                AND EXTRACT(YEAR FROM timestamp) = EXTRACT(YEAR FROM NOW())
                """,
                user_id,
            )
        return float(result) if result else 0.0

    async def get_user_usage_stats(
        self, user_id: str, days: int = 30
    ) -> dict[str, Any]:
        """Get user usage statistics."""
        async with self.pool.acquire() as conn:
            stats = await conn.fetchrow(
                """
                SELECT
                    COUNT(*) as total_requests,
                    SUM(input_tokens) as total_input_tokens,
                    SUM(output_tokens) as total_output_tokens,
                    SUM(cost) as total_cost,
                    AVG(cost) as avg_cost_per_request
                FROM usage_logs
                WHERE user_id = $1
                AND timestamp >= NOW() - INTERVAL '1 day' * $2
                """,
                user_id,
                days,
            )
        return {
            "total_requests": stats["total_requests"] or 0,
            "total_input_tokens": stats["total_input_tokens"] or 0,
            "total_output_tokens": stats["total_output_tokens"] or 0,
            "total_cost": float(stats["total_cost"]) if stats["total_cost"] else 0.0,
            "avg_cost_per_request": float(stats["avg_cost_per_request"])
            if stats["avg_cost_per_request"]
            else 0.0,
        }

    async def create_tenant(
        self, name: str, owner_id: str, settings: dict[str, Any] | None = None
    ) -> Tenant:
        """Create a new tenant."""
        async with self.pool.acquire() as conn:
            record = await conn.fetchrow(
                """
                INSERT INTO tenants (name, owner_id, settings)
                VALUES ($1, $2, $3)
                RETURNING *
                """,
                name,
                owner_id,
                settings or {},
            )
        return Tenant(**dict(record))

    async def get_tenant_by_id(self, tenant_id: str) -> Tenant | None:
        """Get tenant by ID."""
        async with self.pool.acquire() as conn:
            record = await conn.fetchrow(
                "SELECT * FROM tenants WHERE id = $1",
                tenant_id,
            )
        return Tenant(**dict(record)) if record else None

    async def get_user_tenants(self, user_id: str) -> list[Tenant]:
        """Get all tenants for a user."""
        async with self.pool.acquire() as conn:
            records = await conn.fetch(
                "SELECT * FROM tenants WHERE owner_id = $1",
                user_id,
            )
        return [Tenant(**dict(record)) for record in records]

    async def health_check(self) -> bool:
        """Check database health."""
        try:
            async with self.pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False


# Global instance
_db: Database | None = None


async def get_db() -> Database:
    """Get global database instance."""
    global _db
    if _db is None:
        _db = Database()
        await _db.connect()
        await _db.init_tables()
    return _db


async def close_db() -> None:
    """Close global database connection."""
    global _db
    if _db:
        await _db.disconnect()
        _db = None
