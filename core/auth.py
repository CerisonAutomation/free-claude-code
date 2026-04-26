"""Authentication and authorization system."""

import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from loguru import logger
from passlib.context import CryptContext

from config.settings import get_settings
from core.database import Database, User, get_db

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

settings = get_settings()

# JWT settings
JWT_SECRET = (
    settings.anthropic_auth_token
    if hasattr(settings, "anthropic_auth_token") and settings.anthropic_auth_token
    else secrets.token_urlsafe(32)
)
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION = timedelta(days=30)


def generate_api_key() -> str:
    """Generate a secure API key."""
    return f"fcc_{secrets.token_urlsafe(32)}"


def hash_password(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def create_jwt_token(
    data: dict[str, Any], expires_delta: timedelta | None = None
) -> str:
    """Create a JWT token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + JWT_EXPIRATION
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return encoded_jwt


def decode_jwt_token(token: str) -> dict[str, Any] | None:
    """Decode and verify a JWT token."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except JWTError as e:
        logger.warning(f"JWT decode error: {e}")
        return None


async def get_current_user_by_api_key(
    api_key: str = Security(api_key_header),
    db: Database = Depends(get_db),
) -> User:
    """Get current user by API key."""
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required",
        )

    user = await db.get_user_by_api_key(api_key)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )

    return user


async def get_current_user_by_jwt(
    credentials: HTTPAuthorizationCredentials = Security(security),
    db: Database = Depends(get_db),
) -> User:
    """Get current user by JWT token."""
    token = credentials.credentials
    payload = decode_jwt_token(token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    user_id: str | None = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    user = await db.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return user


async def get_current_user(
    api_key: str = Security(api_key_header),
    credentials: HTTPAuthorizationCredentials = Security(security),
    db: Database = Depends(get_db),
) -> User:
    """Get current user by API key or JWT token."""
    # Try API key first
    if api_key:
        user = await db.get_user_by_api_key(api_key)
        if user:
            return user

    # Try JWT token
    if credentials:
        token = credentials.credentials
        payload = decode_jwt_token(token)
        if payload:
            user_id = payload.get("sub")
            if user_id:
                user = await db.get_user_by_id(user_id)
                if user:
                    return user

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required",
    )


class RateLimiter:
    """Rate limiting middleware."""

    def __init__(self):
        self.redis = None

    async def _get_redis(self):
        from core.redis_client import get_redis

        if self.redis is None:
            self.redis = await get_redis()
        return self.redis

    async def check_rate_limit(
        self,
        user_id: str,
        tier: str,
    ) -> tuple[bool, int]:
        """Check if user is within rate limits."""
        redis = await self._get_redis()

        # Rate limits by tier
        limits = {
            "free": (100, 60),  # 100 requests per minute
            "pro": (1000, 60),  # 1000 requests per minute
            "enterprise": (10000, 60),  # 10000 requests per minute
        }

        limit, window = limits.get(tier, limits["free"])
        key = f"user:{user_id}"

        allowed, remaining = await redis.rate_limit_check(key, limit, window)

        if not allowed:
            logger.warning(f"Rate limit exceeded for user {user_id} (tier: {tier})")

        return allowed, remaining


async def check_rate_limit(
    user: User = Depends(get_current_user),
) -> User:
    """Dependency to check rate limit before request."""
    limiter = RateLimiter()
    allowed, remaining = await limiter.check_rate_limit(user.id, user.tier)

    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded",
            headers={
                "X-RateLimit-Limit": str(user.tier),
                "X-RateLimit-Remaining": str(remaining),
                "Retry-After": "60",
            },
        )

    return user


async def check_budget(
    user: User = Depends(get_current_user),
    db: Database = Depends(get_db),
) -> User:
    """Dependency to check if user has budget remaining."""
    monthly_cost = await db.get_user_monthly_cost(user.id)

    if monthly_cost >= user.monthly_budget:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Monthly budget exceeded",
            headers={
                "X-Monthly-Budget": str(user.monthly_budget),
                "X-Monthly-Spent": str(monthly_cost),
            },
        )

    return user


# For backward compatibility - allow requests without auth
async def optional_auth(
    api_key: str = Security(api_key_header),
    credentials: HTTPAuthorizationCredentials = Security(security),
    db: Database = Depends(get_db),
) -> User | None:
    """Optional authentication - returns None if no credentials provided."""
    if not api_key and not credentials:
        return None

    try:
        return await get_current_user(api_key, credentials, db)
    except HTTPException:
        return None
