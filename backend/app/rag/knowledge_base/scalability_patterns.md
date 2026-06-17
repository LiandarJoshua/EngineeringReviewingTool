# Scalability Patterns — Code Review Reference

## Caching
**When:** Same expensive computation or DB query requested repeatedly.
**TTL strategy:** Short TTL for frequently-changing data (30–60s), long for stable data (1hr+).
**Code review signals:**
- No caching on expensive list endpoints
- Cache keys don't include all query parameters → wrong data returned
- No cache invalidation when underlying data changes

---

## N+1 Query Detection
The most common scalability killer.
```python
# N+1: 1 query for posts + N queries for authors
posts = Post.objects.all()
for post in posts:
    print(post.author.name)  # Triggers a DB query per post
```
**Fix:** `Post.objects.select_related("author").all()`

**SQLAlchemy:**
```python
db.query(Post).options(joinedload(Post.author)).all()
```

---

## Pagination
**Never return unbounded lists.** Always paginate.
```python
# Bad: returns all records
@router.get("/findings")
def get_findings(db: Session):
    return db.query(Finding).all()

# Good: cursor-based or offset pagination
@router.get("/findings")
def get_findings(page: int = 1, size: int = 20, db: Session):
    return db.query(Finding).offset((page-1)*size).limit(size).all()
```

---

## Async I/O
**Use async for:** HTTP calls, DB queries, file I/O, external API calls.
**Do NOT use async for:** CPU-bound work (model inference, image processing) — offload to thread pool or Celery.

```python
# Blocking: kills async server throughput
@app.get("/slow")
async def slow():
    import time
    time.sleep(5)  # Blocks event loop for ALL requests

# Fix:
import asyncio
await asyncio.sleep(5)  # OR offload to thread:
await asyncio.get_event_loop().run_in_executor(None, blocking_func)
```

---

## Connection Pool Exhaustion
**Symptom:** Timeouts under load. All pool connections held open.
**Code review signals:**
- DB session not closed after use (missing `finally: db.close()`)
- Pool size too small for concurrency level
- Long-running transactions preventing connection release

**SQLAlchemy config:**
```python
engine = create_engine(url, pool_size=10, max_overflow=20, pool_timeout=30)
```

---

## Rate Limiting
**Why:** Protect against abuse and ensure fair resource allocation.
**Code review signal:** No rate limiting on auth endpoints, public APIs, or file upload endpoints.

**FastAPI example:**
```python
from slowapi import Limiter
limiter = Limiter(key_func=get_remote_address)

@router.post("/login")
@limiter.limit("5/minute")
async def login(request: Request, ...):
    ...
```

---

## Horizontal Scaling Readiness
For a service to scale horizontally, it must be stateless — no in-memory state between requests.
**Code review signals:**
- In-memory session storage (`sessions = {}` global dict)
- Local file system used for user uploads (not object storage)
- Celery results stored in memory (not Redis/DB backend)
- WebSocket connections that require sticky sessions without a pub/sub layer

---

## Database Index Usage
**Code review signals:**
- Filtering on columns without indexes: `WHERE email = ?` on `users.email` with no index
- `LIKE '%search%'` on large tables (can't use B-tree index)
- `ORDER BY` on non-indexed columns causing full table scans
