"""Cost tracking and budget management."""

from dataclasses import dataclass
from typing import Any

from loguru import logger

from core.database import Database, get_db


@dataclass
class ModelPricing:
    """Pricing information for a model."""

    input_price: float  # Price per 1M input tokens
    output_price: float  # Price per 1M output tokens


# Model pricing database (prices per 1M tokens)
MODEL_PRICING: dict[str, ModelPricing] = {
    # NVIDIA NIM
    "nvidia_nim/z-ai/glm4.7": ModelPricing(input_price=0.1, output_price=0.2),
    "nvidia_nim/meta/llama-3.1-405b-instruct": ModelPricing(
        input_price=0.15, output_price=0.3
    ),
    "nvidia_nim/mistralai/mistral-large": ModelPricing(
        input_price=0.2, output_price=0.4
    ),
    # OpenRouter
    "open_router/deepseek/deepseek-r1": ModelPricing(
        input_price=0.14, output_price=0.28
    ),
    "open_router/deepseek/deepseek-chat": ModelPricing(
        input_price=0.14, output_price=0.28
    ),
    "open_router/anthropic/claude-3-5-sonnet": ModelPricing(
        input_price=3.0, output_price=15.0
    ),
    "open_router/anthropic/claude-3-5-haiku": ModelPricing(
        input_price=0.8, output_price=4.0
    ),
    "open_router/openai/gpt-4o": ModelPricing(input_price=2.5, output_price=10.0),
    "open_router/openai/gpt-4o-mini": ModelPricing(input_price=0.15, output_price=0.6),
    # DeepSeek
    "deepseek/deepseek-r1": ModelPricing(input_price=0.14, output_price=0.28),
    "deepseek/deepseek-chat": ModelPricing(input_price=0.14, output_price=0.28),
    # Default fallback
    "default": ModelPricing(input_price=0.1, output_price=0.2),
}


class CostTracker:
    """Track API costs and enforce budgets."""

    def __init__(self):
        self.db: Database | None = None

    async def _get_db(self) -> Database:
        """Get database instance."""
        if self.db is None:
            self.db = await get_db()
        return self.db

    def get_model_pricing(self, model: str) -> ModelPricing:
        """Get pricing for a model."""
        return MODEL_PRICING.get(model, MODEL_PRICING["default"])

    def calculate_cost(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
    ) -> float:
        """Calculate cost for a request."""
        pricing = self.get_model_pricing(model)
        input_cost = (input_tokens / 1_000_000) * pricing.input_price
        output_cost = (output_tokens / 1_000_000) * pricing.output_price
        return input_cost + output_cost

    async def track_usage(
        self,
        user_id: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
    ) -> float:
        """Track usage and return cost."""
        cost = self.calculate_cost(model, input_tokens, output_tokens)
        db = await self._get_db()

        await db.log_usage(
            user_id=user_id,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=cost,
        )

        logger.info(
            f"Usage tracked: user={user_id} model={model} "
            f"input_tokens={input_tokens} output_tokens={output_tokens} cost=${cost:.4f}"
        )

        return cost

    async def check_budget(
        self,
        user_id: str,
        estimated_cost: float,
    ) -> tuple[bool, float, float]:
        """Check if user has budget for this request.

        Returns:
            (allowed, current_monthly_cost, remaining_budget)
        """
        db = await self._get_db()
        user = await db.get_user_by_id(user_id)

        if not user:
            logger.error(f"User {user_id} not found")
            return False, 0.0, 0.0

        monthly_cost = await db.get_user_monthly_cost(user_id)
        remaining_budget = user.monthly_budget - monthly_cost

        allowed = estimated_cost <= remaining_budget

        if not allowed:
            logger.warning(
                f"Budget exceeded for user {user_id}: "
                f"monthly_cost=${monthly_cost:.2f} budget=${user.monthly_budget:.2f} "
                f"estimated=${estimated_cost:.4f}"
            )

        return allowed, monthly_cost, remaining_budget

    async def get_user_stats(
        self,
        user_id: str,
        days: int = 30,
    ) -> dict[str, Any]:
        """Get user usage statistics."""
        db = await self._get_db()
        user = await db.get_user_by_id(user_id)

        if not user:
            return {}

        stats = await db.get_user_usage_stats(user_id, days)
        monthly_cost = await db.get_user_monthly_cost(user_id)

        return {
            "user_id": user_id,
            "tier": user.tier,
            "monthly_budget": user.monthly_budget,
            "monthly_cost": monthly_cost,
            "remaining_budget": user.monthly_budget - monthly_cost,
            "budget_utilization": (monthly_cost / user.monthly_budget * 100)
            if user.monthly_budget > 0
            else 0,
            **stats,
        }

    async def get_model_stats(
        self,
        user_id: str,
        days: int = 30,
    ) -> list[dict[str, Any]]:
        """Get per-model usage statistics."""
        db = await self._get_db()

        async with db.pool.acquire() as conn:
            records = await conn.fetch(
                """
                SELECT
                    model,
                    COUNT(*) as request_count,
                    SUM(input_tokens) as total_input_tokens,
                    SUM(output_tokens) as total_output_tokens,
                    SUM(cost) as total_cost
                FROM usage_logs
                WHERE user_id = $1
                AND timestamp >= NOW() - INTERVAL '$2 days'
                GROUP BY model
                ORDER BY total_cost DESC
                """,
                user_id,
                days,
            )

        return [
            {
                "model": record["model"],
                "request_count": record["request_count"],
                "total_input_tokens": record["total_input_tokens"],
                "total_output_tokens": record["total_output_tokens"],
                "total_cost": float(record["total_cost"]),
            }
            for record in records
        ]

    async def get_daily_cost_trend(
        self,
        user_id: str,
        days: int = 30,
    ) -> list[dict[str, Any]]:
        """Get daily cost trend."""
        db = await self._get_db()

        async with db.pool.acquire() as conn:
            records = await conn.fetch(
                """
                SELECT
                    DATE(timestamp) as date,
                    SUM(cost) as daily_cost,
                    COUNT(*) as request_count
                FROM usage_logs
                WHERE user_id = $1
                AND timestamp >= NOW() - INTERVAL '$2 days'
                GROUP BY DATE(timestamp)
                ORDER BY date DESC
                """,
                user_id,
                days,
            )

        return [
            {
                "date": str(record["date"]),
                "daily_cost": float(record["daily_cost"]),
                "request_count": record["request_count"],
            }
            for record in records
        ]


# Global instance
_cost_tracker: CostTracker | None = None


async def get_cost_tracker() -> CostTracker:
    """Get global cost tracker instance."""
    global _cost_tracker
    if _cost_tracker is None:
        _cost_tracker = CostTracker()
    return _cost_tracker
