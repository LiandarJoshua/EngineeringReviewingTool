# Design Patterns — Code Review Reference

## Creational Patterns

### Singleton
**When:** One shared instance (DB connection pool, config, logger).
**Python idiom:** Module-level instance or `lru_cache` on a factory function.
```python
@lru_cache
def get_settings() -> Settings:
    return Settings()
```
**Anti-pattern:** Manual `_instance` checks with global state are fragile.

### Factory Method
**When:** Creating objects whose type is determined at runtime.
```python
def get_storage_backend(type: str) -> StorageBackend:
    if type == "s3": return S3Backend()
    if type == "local": return LocalBackend()
    raise ValueError(f"Unknown type: {type}")
```

### Builder
**When:** Constructing complex objects step by step.
Common in query builders, report generators.

---

## Structural Patterns

### Repository
**When:** Abstract data access so business logic doesn't know the DB.
```python
class UserRepository:
    def get(self, user_id: UUID) -> User: ...
    def create(self, data: UserCreate) -> User: ...
    def delete(self, user_id: UUID) -> None: ...
```
**Violation to detect:** Calling `db.query(User).filter(...)` directly in service layer.

### Adapter
**When:** Wrapping an external library to isolate its interface.
```python
class OllamaAdapter:
    def generate(self, prompt: str) -> str:
        return self._client.invoke(prompt).content
```

### Facade
**When:** Simplifying a complex subsystem behind a single interface.
The LangGraph orchestrator is a facade over 11 agents.

---

## Behavioral Patterns

### Strategy
**When:** Interchangeable algorithms behind a common interface.
```python
class Scorer(Protocol):
    def score(self, findings: List[Finding]) -> float: ...

class WeightedScorer:
    def score(self, findings): ...

class ThresholdScorer:
    def score(self, findings): ...
```

### Observer / Event
**When:** Decoupled notifications (e.g., publish stage completion to Redis pub/sub).
**Code smell:** Direct method calls between unrelated modules for side effects.

### Chain of Responsibility
**When:** Processing requests through a pipeline of handlers.
LangGraph is essentially a chain of responsibility.

---

## Anti-patterns to Detect in Code Review

| Anti-pattern | Symptom | Fix |
|---|---|---|
| God Class | Single class > 500 lines, doing everything | Split by responsibility |
| Magic Numbers | `if score > 73:` | Named constants |
| Shotgun Surgery | One change requires edits in 10 files | Group related logic |
| Anemic Domain Model | Models have only getters/setters, all logic in services | Move logic into domain |
| Primitive Obsession | Strings for IDs, emails, statuses everywhere | Typed value objects |
| Long Parameter List | Function takes 7+ positional args | Bundle into dataclass |
