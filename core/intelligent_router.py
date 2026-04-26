"""Intelligent request routing based on cost, latency, and quality."""

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from loguru import logger


class RoutingStrategy(StrEnum):
    """Routing strategies."""

    CHEAPEST = "cheapest"
    FASTEST = "fastest"
    HIGHEST_QUALITY = "highest_quality"
    BALANCED = "balanced"
    ADAPTIVE = "adaptive"


@dataclass
class ProviderScore:
    """Score for a provider."""

    provider: str
    model: str
    cost_score: float  # Lower is better
    latency_score: float  # Lower is better
    quality_score: float  # Higher is better
    health_score: float  # Higher is better
    final_score: float  # Higher is better


class IntelligentRouter:
    """Route requests to optimal providers based on multiple factors."""

    def __init__(self):
        self.provider_health: dict[str, bool] = {
            "nvidia_nim": True,
            "open_router": True,
            "deepseek": True,
        }
        self.provider_latency: dict[str, float] = {
            "nvidia_nim": 0.5,  # seconds
            "open_router": 0.8,
            "deepseek": 0.6,
        }

        # Model quality scores (0-1)
        self.model_quality: dict[str, float] = {
            "nvidia_nim/z-ai/glm4.7": 0.7,
            "nvidia_nim/meta/llama-3.1-405b-instruct": 0.85,
            "open_router/anthropic/claude-3-5-sonnet": 0.95,
            "open_router/anthropic/claude-3-5-haiku": 0.8,
            "open_router/openai/gpt-4o": 0.92,
            "open_router/openai/gpt-4o-mini": 0.75,
            "open_router/deepseek/deepseek-r1": 0.75,
            "deepseek/deepseek-chat": 0.7,
        }

        # Available models per provider
        self.provider_models: dict[str, list[str]] = {
            "nvidia_nim": [
                "nvidia_nim/z-ai/glm4.7",
                "nvidia_nim/meta/llama-3.1-405b-instruct",
            ],
            "open_router": [
                "open_router/anthropic/claude-3-5-sonnet",
                "open_router/anthropic/claude-3-5-haiku",
                "open_router/openai/gpt-4o",
                "open_router/openai/gpt-4o-mini",
                "open_router/deepseek/deepseek-r1",
            ],
            "deepseek": [
                "deepseek/deepseek-chat",
            ],
        }

    def estimate_complexity(self, request: dict[str, Any]) -> float:
        """Estimate request complexity (0-1).

        Factors:
        - Prompt length
        - Number of messages
        - Tool calls
        - Context size
        """
        messages = request.get("messages", [])
        if not messages:
            return 0.0

        # Calculate total prompt length
        total_length = sum(len(msg.get("content", "")) for msg in messages)

        # Check for tool calls
        has_tools = any("tool_use" in msg for msg in messages)

        # Complexity based on length (cap at 1.0)
        length_complexity = min(total_length / 10000, 1.0)

        # Boost complexity for tool calls
        tool_complexity = 0.3 if has_tools else 0.0

        # Number of messages factor
        message_complexity = min(len(messages) / 20, 0.2)

        total_complexity = length_complexity + tool_complexity + message_complexity
        return min(total_complexity, 1.0)

    def score_provider(
        self,
        provider: str,
        model: str,
        complexity: float,
        strategy: RoutingStrategy = RoutingStrategy.BALANCED,
    ) -> ProviderScore:
        """Score a provider for a request."""
        from core.cost_tracker import MODEL_PRICING

        # Get pricing
        pricing = MODEL_PRICING.get(model, MODEL_PRICING["default"])

        # Cost score (inverse of price)
        avg_price = (pricing.input_price + pricing.output_price) / 2
        cost_score = 1.0 / (avg_price + 0.01)  # Avoid division by zero

        # Latency score (inverse of latency)
        latency = self.provider_latency.get(provider, 1.0)
        latency_score = 1.0 / (latency + 0.01)

        # Quality score
        quality_score = self.model_quality.get(model, 0.5)

        # Health score
        health_score = 1.0 if self.provider_health.get(provider, False) else 0.0

        # Calculate final score based on strategy
        if strategy == RoutingStrategy.CHEAPEST:
            final_score = cost_score * 0.7 + health_score * 0.3
        elif strategy == RoutingStrategy.FASTEST:
            final_score = latency_score * 0.7 + health_score * 0.3
        elif strategy == RoutingStrategy.HIGHEST_QUALITY:
            final_score = quality_score * 0.7 + health_score * 0.3
        elif strategy == RoutingStrategy.BALANCED:
            final_score = (
                cost_score * 0.3
                + latency_score * 0.2
                + quality_score * 0.3
                + health_score * 0.2
            )
        else:  # ADAPTIVE
            # For adaptive, weight by complexity
            if complexity < 0.3:
                # Simple requests - prioritize cost
                final_score = cost_score * 0.6 + health_score * 0.4
            elif complexity < 0.7:
                # Medium requests - balanced
                final_score = (
                    cost_score * 0.3
                    + latency_score * 0.2
                    + quality_score * 0.3
                    + health_score * 0.2
                )
            else:
                # Complex requests - prioritize quality
                final_score = quality_score * 0.6 + health_score * 0.4

        return ProviderScore(
            provider=provider,
            model=model,
            cost_score=cost_score,
            latency_score=latency_score,
            quality_score=quality_score,
            health_score=health_score,
            final_score=final_score,
        )

    def select_provider(
        self,
        request: dict[str, Any],
        strategy: RoutingStrategy = RoutingStrategy.ADAPTIVE,
        allowed_models: list[str] | None = None,
    ) -> tuple[str, str]:
        """Select the best provider and model for a request.

        Returns:
            (provider, model)
        """
        complexity = self.estimate_complexity(request)

        # Get all available models
        all_models = []
        for provider, models in self.provider_models.items():
            all_models.extend(
                (provider, model)
                for model in models
                if allowed_models is None or model in allowed_models
            )

        # Score each option
        scores = []
        for provider, model in all_models:
            if not self.provider_health.get(provider, True):
                continue

            score = self.score_provider(provider, model, complexity, strategy)
            scores.append(score)

        # Sort by final score (descending)
        scores.sort(key=lambda x: x.final_score, reverse=True)

        if not scores:
            logger.warning("No healthy providers available")
            # Fallback to first available
            for provider, models in self.provider_models.items():
                if models:
                    return provider, models[0]

        best = scores[0]
        logger.info(
            f"Selected provider={best.provider} model={best.model} "
            f"complexity={complexity:.2f} score={best.final_score:.2f}"
        )

        return best.provider, best.model

    def update_provider_health(self, provider: str, healthy: bool) -> None:
        """Update provider health status."""
        self.provider_health[provider] = healthy
        logger.info(f"Provider {provider} health updated to {healthy}")

    def update_provider_latency(self, provider: str, latency: float) -> None:
        """Update provider latency (exponential moving average)."""
        current = self.provider_latency.get(provider, 1.0)
        # EMA with alpha=0.3
        new_latency = 0.3 * latency + 0.7 * current
        self.provider_latency[provider] = new_latency
        logger.info(
            f"Provider {provider} latency updated: {current:.3f}s -> {new_latency:.3f}s"
        )

    def get_routing_stats(self) -> dict[str, Any]:
        """Get routing statistics."""
        return {
            "provider_health": self.provider_health,
            "provider_latency": self.provider_latency,
            "model_quality": self.model_quality,
        }


# Global instance
_router: IntelligentRouter | None = None


def get_router() -> IntelligentRouter:
    """Get global router instance."""
    global _router
    if _router is None:
        _router = IntelligentRouter()
    return _router
