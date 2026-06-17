# FastAPI Best Practices — Code Review Reference

## Dependency Injection
**Use `Depends` for:** DB sessions, authentication, config, shared clients.
```python
# Good: session closed automatically after request
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session

@router.get("/users/{id}")
async def get_user(id: UUID, db: AsyncSession = Depends(get_db)):
    ...
```
**Bad:** Creating DB session inside route handler — session never guaranteed to close.

---

## Response Models
Always declare `response_model` to:
1. Prevent accidental leaking of sensitive fields (e.g., `password_hash`)
2. Document the API automatically
3. Enable serialization validation

```python
@router.get("/users/{id}", response_model=UserResponse)  # NOT UserORM
async def get_user(id: UUID):
    ...
```

---

## Error Handling
**Use `HTTPException` for client errors, not 500s.**
```python
user = await get_user(db, user_id)
if not user:
    raise HTTPException(status_code=404, detail="User not found")
```

**Global exception handler for unexpected errors:**
```python
@app.exception_handler(Exception)
async def global_handler(request, exc):
    logger.error(f"Unhandled: {exc}", exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "Internal error"})
```
**Code review signal:** Routes returning `{"error": str(e)}` with status 200.

---

## Async Patterns
```python
# Bad: blocking call in async handler
@router.get("/fetch")
async def fetch(url: str):
    return requests.get(url).json()  # Blocks event loop

# Good:
async with httpx.AsyncClient() as client:
    return (await client.get(url)).json()
```

---

## Input Validation
Use Pydantic models for ALL request bodies. Never trust raw `dict` or `request.body()`.
```python
class CreateReviewRequest(BaseModel):
    repo_url: HttpUrl           # Validates URL format
    user_id: UUID
    experience_level: Literal["junior", "mid", "senior"]
```

---

## Background Tasks
For fire-and-forget operations (sending emails, logging):
```python
@router.post("/reviews")
async def create(background_tasks: BackgroundTasks, ...):
    review = await create_review(db, ...)
    background_tasks.add_task(send_confirmation_email, review.id)
    return review
```
For long-running operations (>5 seconds): use Celery, not BackgroundTasks.

---

## Common Mistakes to Flag

| Mistake | Severity |
|---|---|
| No `response_model` on endpoints returning DB models | Medium |
| Synchronous `requests` library in async handlers | High |
| Missing auth dependency on protected routes | Critical |
| `except Exception: pass` swallowing errors silently | High |
| Raw SQL strings in route handlers (no ORM/parameterized) | Critical |
| Returning full stack traces in error responses | Medium |
| No input validation on file upload size/type | Medium |
