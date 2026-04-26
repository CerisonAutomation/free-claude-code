"""Automatic failover across multiple providers."""

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any

from loguru import logger


class ProviderStatus(StrEnum):
    """Provider health status."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class ProviderHealth:
    """Health status of a provider."""

    provider: str
    status: ProviderStatus
    last_check: datetime
    error_count: int
    success_count: int
    last_error: str | None = None
    avg_latency: float = 0.0


class CircuitBreaker:
    """Circuit breaker pattern for provider failover."""

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type[Exception] | tuple[type[Exception], ...] = Exception,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.failure_count = 0
        self.last_failure_time: datetime | None = None
        self.state = "closed"  # closed, open, half-open

    async def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection."""
        if self.state == "open":
            if self._should_attempt_reset():
                self.state = "half-open"
                logger.info("Circuit breaker transitioning to half-open")
            else:
                raise Exception("Circuit breaker is OPEN")

        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise e

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        if self.last_failure_time is None:
            return True
        return datetime.now(UTC) - self.last_failure_time > timedelta(
            seconds=self.recovery_timeout
        )

    def _on_success(self):
        """Handle successful call."""
        self.failure_count = 0
        self.state = "closed"

    def _on_failure(self):
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = datetime.now(UTC)

        if self.failure_count >= self.failure_threshold:
            self.state = "open"
            logger.warning(
                f"Circuit breaker opened after {self.failure_count} failures"
            )


class FailoverManager:
    """Manage automatic failover across providers."""

    def __init__(self):
        self.provider_health: dict[str, ProviderHealth] = {
            "nvidia_nim": ProviderHealth(
                provider="nvidia_nim",
                status=ProviderStatus.HEALTHY,
                last_check=datetime.now(UTC),
                error_count=0,
                success_count=0,
            ),
            "open_router": ProviderHealth(
                provider="open_router",
                status=ProviderStatus.HEALTHY,
                last_check=datetime.now(UTC),
                error_count=0,
                success_count=0,
            ),
            "deepseek": ProviderHealth(
                provider="deepseek",
                status=ProviderStatus.HEALTHY,
                last_check=datetime.now(UTC),
                error_count=0,
                success_count=0,
            ),
        }

        self.circuit_breakers: dict[str, CircuitBreaker] = {
            "nvidia_nim": CircuitBreaker(failure_threshold=5, recovery_timeout=60),
            "open_router": CircuitBreaker(failure_threshold=5, recovery_timeout=60),
            "deepseek": CircuitBreaker(failure_threshold=5, recovery_timeout=60),
        }

        # Provider fallback chain
        self.fallback_chain: dict[str, list[str]] = {
            "nvidia_nim": ["open_router", "deepseek"],
            "open_router": ["nvidia_nim", "deepseek"],
            "deepseek": ["nvidia_nim", "open_router"],
        }

    async def call_with_failover(
        self,
        request: dict[str, Any],
        primary_provider: str,
        primary_model: str,
        call_func,  # Function to call provider
    ) -> tuple[Any, str, str]:
        """Execute request with automatic failover.

        Returns:
            (response, actual_provider, actual_model)
        """
        providers_to_try = [
            primary_provider,
            *self.fallback_chain.get(primary_provider, []),
        ]

        last_error = None

        for provider in providers_to_try:
            health = self.provider_health.get(provider)
            if not health or health.status == ProviderStatus.UNHEALTHY:
                logger.info(f"Skipping unhealthy provider: {provider}")
                continue

            circuit_breaker = self.circuit_breakers.get(provider)
            if circuit_breaker is None:
                logger.warning(f"No circuit breaker for provider: {provider}")
                continue

            if circuit_breaker.state == "open":
                logger.info(f"Circuit breaker open for provider: {provider}")
                continue

            try:
                logger.info(f"Attempting provider: {provider}")
                start_time = datetime.now(UTC)

                response = await circuit_breaker.call(
                    call_func, provider, primary_model, request
                )

                latency = (datetime.now(UTC) - start_time).total_seconds()
                self._record_success(provider, latency)

                return response, provider, primary_model

            except Exception as e:
                last_error = e
                logger.warning(f"Provider {provider} failed: {e}")
                self._record_failure(provider, str(e))
                continue

        # All providers failed
        logger.error(f"All providers failed. Last error: {last_error}")
        raise Exception(f"All providers failed: {last_error}")

    def _record_success(self, provider: str, latency: float) -> None:
        """Record successful call."""
        health = self.provider_health.get(provider)
        if health:
            health.success_count += 1
            health.error_count = 0
            health.last_check = datetime.now(UTC)
            health.status = ProviderStatus.HEALTHY

            # Update average latency (EMA)
            if health.avg_latency == 0:
                health.avg_latency = latency
            else:
                health.avg_latency = 0.3 * latency + 0.7 * health.avg_latency

            # Update router latency
            from core.intelligent_router import get_router

            router = get_router()
            router.update_provider_latency(provider, latency)
            router.update_provider_health(provider, True)

    def _record_failure(self, provider: str, error: str) -> None:
        """Record failed call."""
        health = self.provider_health.get(provider)
        if health:
            health.error_count += 1
            health.last_check = datetime.now(UTC)
            health.last_error = error

            # Update status based on error count
            if health.error_count >= 10:
                health.status = ProviderStatus.UNHEALTHY
            elif health.error_count >= 5:
                health.status = ProviderStatus.DEGRADED

            # Update router health
            from core.intelligent_router import get_router

            router = get_router()
            if health.status == ProviderStatus.UNHEALTHY:
                router.update_provider_health(provider, False)

    async def health_check(self, provider: str, check_func) -> bool:
        """Perform health check on a provider."""
        try:
            result = await asyncio.wait_for(check_func(provider), timeout=5.0)
            self._record_success(provider, 0.0)
            return result
        except Exception as e:
            self._record_failure(provider, str(e))
            return False

    async def health_check_all(self, check_func) -> dict[str, bool]:
        """Perform health checks on all providers."""
        results = {}
        tasks = []

        for provider in self.provider_health:
            task = self.health_check(provider, check_func)
            tasks.append((provider, task))

        for provider, task in tasks:
            results[provider] = await task

        return results

    def get_provider_status(self, provider: str) -> ProviderHealth | None:
        """Get health status of a provider."""
        return self.provider_health.get(provider)

    def get_all_statuses(self) -> dict[str, ProviderHealth]:
        """Get health status of all providers."""
        return self.provider_health.copy()

    def reset_provider(self, provider: str) -> None:
        """Reset a provider's health status."""
        health = self.provider_health.get(provider)
        if health:
            health.status = ProviderStatus.HEALTHY
            health.error_count = 0
            health.last_check = datetime.now(UTC)

        circuit_breaker = self.circuit_breakers.get(provider)
        if circuit_breaker:
            circuit_breaker.state = "closed"
            circuit_breaker.failure_count = 0

        logger.info(f"Reset provider: {provider}")

    def get_failover_stats(self) -> dict[str, Any]:
        """Get failover statistics."""
        return {
            "provider_health": {
                k: {
                    "status": v.status.value,
                    "error_count": v.error_count,
                    "success_count": v.success_count,
                    "avg_latency": v.avg_latency,
                }
                for k, v in self.provider_health.items()
            },
            "circuit_breakers": {
                k: {
                    "state": v.state,
                    "failure_count": v.failure_count,
                }
                for k, v in self.circuit_breakers.items()
            },
        }


# Global instance
_failover_manager: FailoverManager | None = None


def get_failover_manager() -> FailoverManager:
    """Get global failover manager instance."""
    global _failover_manager
    if _failover_manager is None:
        _failover_manager = FailoverManager()
    return _failover_manager
