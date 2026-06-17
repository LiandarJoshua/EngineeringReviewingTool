# Designing Data-Intensive Applications — Key Concepts for Code Review

## Replication
**Single-leader:** One primary accepts writes; replicas read-only. Good for read-heavy workloads.
**Multi-leader / leaderless:** Write to multiple nodes. More complex conflict resolution.

**Code review signals:**
- No retry logic on DB writes → data loss under network partition
- Assuming synchronous replication → stale reads ignored
- No handling of `read-your-writes` consistency (user writes, immediately reads, sees stale data)

---

## Partitioning (Sharding)
**By key range:** Good for range queries; risk of hot partitions.
**By hash:** Even distribution; loses range query ability.

**Code review signal:** Choosing partition key on a low-cardinality field (e.g., `status` with 3 values) → all writes go to one shard.

---

## Transactions and Isolation Levels

| Level | Prevents |
|---|---|
| Read Uncommitted | Nothing |
| Read Committed | Dirty reads |
| Repeatable Read | Dirty + non-repeatable reads |
| Serializable | All anomalies (slowest) |

**Common bug:** Using `READ COMMITTED` and assuming no phantom reads. Two transactions checking "is username taken" can both see it as available and both insert.

**Code review signals:**
- Long-running transactions holding locks
- No transaction on multi-step operations that must be atomic
- `SELECT ... FOR UPDATE` missing on optimistic locking patterns

---

## Caching Patterns

### Cache-aside (Lazy Loading)
1. Check cache → 2. On miss, read DB → 3. Write to cache.
```python
data = cache.get(key)
if not data:
    data = db.query(...)
    cache.set(key, data, ttl=300)
```
**Risk:** Cache stampede on cold start. Fix with lock or probabilistic early expiration.

### Write-through
Write to cache and DB simultaneously. Cache always has fresh data. Higher write latency.

### Write-behind (Write-back)
Write to cache, asynchronously flush to DB. Fast writes, risk of data loss on crash.

**Code review signals:**
- No TTL on cache entries → stale data forever
- Cache keys not including all relevant parameters → cache poisoning
- No cache invalidation on writes → reads return stale data

---

## N+1 Query Problem
Loading a list, then querying DB once per item:
```python
users = db.query(User).all()
for user in users:
    orders = db.query(Order).filter(Order.user_id == user.id).all()  # N+1!
```
**Fix:** `db.query(User).options(joinedload(User.orders)).all()`

**Detection:** Any loop containing a DB query call.

---

## Connection Pooling
**Why:** New DB connections are expensive (~50ms). Pool reuses connections.
**Code review signals:**
- Creating new `Engine` per request
- No pool size configured (`pool_size`, `max_overflow`)
- Connections not released (context manager not used)

---

## Async I/O for Scalability
**When to use:** I/O-bound workloads (DB, HTTP calls, file I/O).
**When NOT to use:** CPU-bound (use multiprocessing or workers instead).

**Code review signals:**
- `requests.get()` in an async FastAPI handler → blocks the event loop
- Use `httpx.AsyncClient` instead
- `time.sleep()` in async code → use `asyncio.sleep()`
