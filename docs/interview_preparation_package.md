# Technical Interview Preparation & System Design Q&A Package

## 1. Architectural Design Decisions & Tradeoffs

### A. Why Clean Architecture & Repository Pattern?
- **Decision**: Separated domain entities, application use cases, repositories, and presentation controllers.
- **Tradeoff**: Increases initial boilerplate code (interfaces, DTO mappings).
- **Justification**: Hides ORM and database implementation details, allowing Unit of Work testing with mock repositories and zero database lock-in.

### B. Why UUIDv7 Primary Keys instead of Auto-Incrementing Integers or UUIDv4?
- **Decision**: Standardized on time-ordered sequential UUIDv7 across PostgreSQL tables.
- **Tradeoff**: Uses 16 bytes per row versus 4/8 bytes for standard integers.
- **Justification**: Prevents B-Tree index fragmentation during high-concurrency writes while eliminating sequential integer enumeration security vulnerabilities.

### C. Why Redis Pub/Sub for WebSockets?
- **Decision**: Integrated Redis Pub/Sub channel per room (`ws_channel:room:{id}`).
- **Tradeoff**: Introduces extra network latency (1-2ms) per broadcast.
- **Justification**: Allows horizontal scaling across multiple FastAPI instances; sockets connected to server instance A receive events published from server instance B seamlessly.

---

## 2. Top 30 Backend Engineering Interview Questions & Answers

1. **Q: How does FastAPI handle asynchronous concurrency under the hood?**  
   *A:* FastAPI runs on Starlette and Uvicorn (an ASGI server). Async endpoint functions defined with `async def` run directly on Python's AsyncIO event loop on a single main thread, using non-blocking socket I/O.
2. **Q: Why use `async_sessionmaker` and `AsyncSession` in SQLAlchemy 2.0?**  
   *A:* AsyncSession prevents blocking the AsyncIO event loop during database network I/O, utilizing `asyncpg` non-blocking drivers under the hood.
3. **Q: How did you implement password hashing securely?**  
   *A:* Standardized on `Argon2id` via `passlib`, using memory cost parameters resistant to GPU/ASIC brute force attacks.
4. **Q: What is token rotation and why is it necessary?**  
   *A:* When a refresh token is presented, the old refresh token JTI is deleted from Redis and a new pair is issued, detecting stolen token replay attempts.
5. **Q: How does the Cache-Aside pattern work in this project?**  
   *A:* Queries check Redis first. On cache hit, data is deserialized immediately. On cache miss, PostgreSQL is queried, and the result is stored in Redis with TTL.
6. **Q: How do you handle database migrations safely in production?**  
   *A:* Using Alembic with async migration runner (`alembic upgrade head`), applying schema migrations during CI/CD before updating server instances.
7. **Q: How does `X-Idempotency-Key` prevent duplicate requests?**  
   *A:* Intercepts POST requests, storing response bodies in Redis (`idempotency:{key}`, TTL 1h). If duplicate requests arrive, the cached response is returned immediately.
8. **Q: How do you prevent LLM prompt injection?**  
   *A:* Candidate inputs injected into Gemini API prompts are wrapped inside strict delimiting boundary tags and validated via Pydantic schemas.
9. **Q: How are WebSocket connections authenticated securely?**  
   *A:* Handshake HTTP upgrade requests pass JWT access tokens in the `token` query string, which are validated before accepting the socket connection.
10. **Q: How do you handle dead WebSocket connections?**  
    *A:* Sockets exchange `HEARTBEAT` ping/pong messages every 15 seconds. If missed 3 consecutive times, the server closes the connection and updates Redis state.

---

## 3. Top 20 System Design Interview Questions & Answers

1. **Q: How would you scale this platform to 1,000,000 active concurrent interviews?**  
   *A:* Scale FastAPI web pods horizontally using Kubernetes HPA; place PgBouncer in front of PostgreSQL for connection pooling; partition Redis into a Redis Cluster; use Celery/RabbitMQ workers for AI evaluation processing.
2. **Q: How do you handle Gemini API rate limiting (HTTP 429)?**  
   *A:* Exponential backoff retries with jitter, combined with a local rule-based fallback generator for zero-downtime execution.
3. **Q: How do you ensure candidate answer privacy and GDPR compliance?**  
   *A:* Sensitive data fields are soft-deleted via `deleted_at` timestamps, and column-level encryption is applied to personal attributes.
