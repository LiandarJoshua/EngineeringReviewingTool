# Clean Architecture — Code Review Reference

## Core Principle
Dependencies must point inward. Inner layers (entities, use cases) know nothing about outer layers (DB, HTTP, UI).

```
[Frameworks & Drivers] → [Interface Adapters] → [Use Cases] → [Entities]
```

## The Dependency Rule
- Entities: pure business objects, no imports from frameworks
- Use Cases (Application Layer): orchestrates entities, no HTTP/DB imports
- Interface Adapters: converts between use case format and external format (controllers, presenters, gateways)
- Frameworks & Drivers: FastAPI, SQLAlchemy, Redis — only at the outermost layer

## Common Violations to Detect

### 1. Direct DB access in route handlers
```python
# Violation: HTTP layer reaching into DB directly
@router.post("/orders")
def create_order(data: OrderIn, db: Session = Depends()):
    order = Order(user_id=data.user_id, total=data.total)
    db.add(order)  # DB logic in route handler
    db.commit()
    return order
```
**Fix:** Route handler should call a use case function. The use case calls a repository interface.

### 2. Business logic in models
```python
# Violation: SQLAlchemy model doing business logic
class User(Base):
    def apply_discount(self, pct):
        self.balance *= (1 - pct)  # Business logic in persistence model
```

### 3. Importing ORM models in use cases
```python
from app.db.models import User  # Violation: use case depends on ORM
```
**Fix:** Use case depends on a plain dataclass or Pydantic model.

## Layered Architecture (common in web services)
When full Clean Architecture is overkill, a 3-layer approach is acceptable:
1. **Presentation** (routes/controllers)
2. **Service** (business logic)
3. **Repository** (data access)

The rule: presentation → service → repository. Never skip a layer.

## Anti-patterns
- God classes / God modules (one file doing everything)
- Circular imports between modules
- Shared mutable global state
- Direct instantiation of dependencies (use dependency injection)

## Good Signals
- `services/` or `use_cases/` directory separate from `routes/` and `models/`
- Repository pattern: `UserRepository` with `get`, `create`, `update` methods
- Dependency injection (FastAPI `Depends`, constructor injection)
- Interfaces/protocols defining boundaries between layers
