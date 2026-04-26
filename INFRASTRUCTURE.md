# Infrastructure Components

This document describes the infrastructure components available in the proxy.

## Implemented Components

### 1. Redis Client (`core/redis_client.py`)
- **Purpose**: Rate limiting, caching, session storage
- **Features**:
  - Token bucket rate limiting
  - Key-value caching with TTL
  - Session management
  - Counter operations
  - Health checks
- **Status**: ✅ Integrated in runtime startup/shutdown
- **Usage**: Available via `await get_redis()`

### 2. PostgreSQL Database (`core/database.py`)
- **Purpose**: User management, usage logging, multi-tenancy
- **Features**:
  - User CRUD operations
  - Usage logging with cost tracking
  - Tenant management
  - Monthly cost aggregation
  - Usage statistics
- **Status**: ✅ Integrated in runtime startup/shutdown
- **Usage**: Available via `await get_db()`

### 3. Authentication (`core/auth.py`)
- **Purpose**: JWT and API key authentication
- **Features**:
  - JWT token generation/validation
  - API key verification
  - Password hashing
  - Rate limiting by tier
  - Budget checking
- **Status**: ✅ Implemented, ready for integration
- **Usage**: Available as FastAPI dependencies

### 4. Cost Tracker (`core/cost_tracker.py`)
- **Purpose**: Track API costs and enforce budgets
- **Features**:
  - Model pricing database
  - Cost calculation per request
  - Usage logging
  - Budget enforcement
  - User statistics
  - Per-model statistics
  - Daily cost trends
- **Status**: ✅ Implemented, ready for integration
- **Usage**: Available via `await get_cost_tracker()`

### 5. Semantic Cache (`core/semantic_cache.py`)
- **Purpose**: Cache responses to reduce costs
- **Features**:
  - Exact match caching
  - Cache key generation
  - Cache statistics
  - TTL management
- **Status**: ✅ Implemented, ready for integration
- **Usage**: Available via `await get_semantic_cache()`

### 6. Intelligent Router (`core/intelligent_router.py`)
- **Purpose**: Select optimal providers based on cost/latency/quality
- **Features**:
  - Multiple routing strategies (cost, latency, quality, balanced)
  - Provider scoring
  - Dynamic provider selection
- **Status**: ✅ Implemented, ready for integration
- **Usage**: Available via `IntelligentRouter`

### 7. Failover Manager (`core/failover.py`)
- **Purpose**: Automatic failover across providers
- **Features**:
  - Circuit breaker pattern
  - Provider health tracking
  - Automatic retry with fallback
  - Health checks
- **Status**: ✅ Implemented, ready for integration
- **Usage**: Available via `FailoverManager`

## Integration Status

### Currently Integrated
- ✅ Redis client (runtime startup/shutdown)
- ✅ PostgreSQL database (runtime startup/shutdown)

### Available for Future Integration
- 🔲 Authentication system (for protected endpoints)
- 🔲 Cost tracking (for usage analytics)
- 🔲 Semantic caching (for cost reduction)
- 🔲 Intelligent routing (for provider optimization)
- 🔲 Failover manager (for high availability)

## Environment Variables

### Required for Infrastructure
```bash
REDIS_URL="redis://localhost:6379/0"  # Auto-configured by Render
DATABASE_URL="postgresql://postgres:postgres@localhost:5432/freeclaude"  # Auto-configured by Render
```

### Optional for Features
```bash
ANTHROPIC_AUTH_TOKEN="freecc"  # For authentication
```

## Deployment

All infrastructure components are included in the Docker image and will be available when deployed to Render. Redis and PostgreSQL are automatically provisioned by Render based on `render.yaml`.

## Future Work

To integrate the additional components:

1. **Authentication**: Add `Depends(get_current_user)` to protected routes
2. **Cost Tracking**: Call `await cost_tracker.track_usage()` after each request
3. **Semantic Cache**: Check cache before making provider requests
4. **Intelligent Routing**: Use router to select providers dynamically
5. **Failover**: Wrap provider calls with failover manager

These components are designed to be modular and can be integrated incrementally as needed.
