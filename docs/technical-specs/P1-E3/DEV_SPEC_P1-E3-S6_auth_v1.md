# Auth – JWT Login & Role-Based Access – Technical Specification

> **For AI Coding Assistants:** Implement checkpoints in order. Every protected endpoint must use `Depends(get_current_user)`. Dispatcher and driver are separate roles with separate UI entry points. Do not implement OAuth or third-party SSO here — plain email/password JWT only.

---

## Document Information

| Field | Value |
|-------|-------|
| **Feature Name** | Auth – JWT Login & Role-Based Access |
| **Epic / Story** | P1-E3-S6 |
| **Status** | ⬜ Not Started |
| **Version** | 1.0 |
| **Date** | 2026-03-29 |
| **Depends On** | P1-E2 (tenant middleware), P1-E3 User model |
| **Implementation Branch** | feat/p1-e3-s6-auth |

---

## Executive Summary

**Purpose:** Add JWT-based authentication so the app has real login. Two roles exist: `dispatcher` (ops manager — full dashboard access) and `driver` (sees only their own assigned stops). Auth token carries `user_id`, `tenant_id`, and `role`. After this, `X-Tenant-ID` header is no longer needed manually — it comes from the token.

### Key Deliverables

| Component | File | Status |
|-----------|------|--------|
| Password hashing utility | `app/core/security.py` | ⬜ |
| JWT encode/decode | `app/core/security.py` | ⬜ |
| Auth service (register, login) | `app/services/auth_service.py` | ⬜ |
| Auth router (POST /auth/register, /auth/login) | `app/api/v1/auth.py` | ⬜ |
| Updated deps.py (get_current_user) | `app/api/deps.py` | ⬜ |
| Update router.py | `app/api/router.py` | ⬜ |
| Add JWT deps to requirements.txt | `requirements.txt` | ⬜ |

### Success Criteria

- [ ] `POST /api/v1/auth/register` creates a user and returns a token
- [ ] `POST /api/v1/auth/login` returns JWT token for valid credentials
- [ ] Token contains `user_id`, `tenant_id`, `role`
- [ ] All domain endpoints accept `Authorization: Bearer <token>` instead of `X-Tenant-ID`
- [ ] Driver cannot access dispatcher-only endpoints (returns HTTP 403)

---

## 1. New Dependencies

Add to `requirements.txt`:
```
python-jose[cryptography]
passlib[bcrypt]
```

Add to `.env`:
```
JWT_SECRET_KEY=your-super-secret-key-change-in-production
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=1440
```

Add to `app/core/config.py` Settings class:
```python
JWT_SECRET_KEY: str = "change-me"
JWT_ALGORITHM: str = "HS256"
JWT_EXPIRE_MINUTES: int = 1440  # 24 hours
```

---

## 2. `app/core/security.py`

```python
from datetime import datetime, timedelta
from typing import Optional, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.JWT_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
```

---

## 3. `app/schemas/auth.py`

```python
from pydantic import BaseModel, EmailStr
from uuid import UUID


class RegisterRequest(BaseModel):
    email: str
    password: str
    full_name: str
    role: str = "dispatcher"  # dispatcher | driver
    tenant_id: UUID           # which tenant to register under


class LoginRequest(BaseModel):
    email: str
    password: str
    tenant_id: UUID           # required — one email can exist in multiple tenants


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: UUID
    tenant_id: UUID
    role: str
    full_name: str
```

---

## 4. `app/services/auth_service.py`

```python
from uuid import UUID
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models.user import User
from app.schemas.auth import RegisterRequest, LoginRequest
from app.core.security import hash_password, verify_password, create_access_token


def register_user(db: Session, data: RegisterRequest) -> dict:
    # Check if email already exists for this tenant
    existing = db.execute(
        select(User).where(
            User.email == data.email,
            User.tenant_id == data.tenant_id,
        )
    ).scalar_one_or_none()

    if existing:
        return None  # caller raises HTTP 409

    user = User(
        email=data.email,
        hashed_password=hash_password(data.password),
        full_name=data.full_name,
        role=data.role,
        tenant_id=data.tenant_id,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token({
        "sub": str(user.id),
        "tenant_id": str(user.tenant_id),
        "role": user.role,
    })

    return {
        "access_token": token,
        "token_type": "bearer",
        "user_id": user.id,
        "tenant_id": user.tenant_id,
        "role": user.role,
        "full_name": user.full_name,
    }


def login_user(db: Session, data: LoginRequest) -> Optional[dict]:
    user = db.execute(
        select(User).where(
            User.email == data.email,
            User.tenant_id == data.tenant_id,
            User.is_active == True,
        )
    ).scalar_one_or_none()

    if not user or not verify_password(data.password, user.hashed_password):
        return None  # caller raises HTTP 401

    token = create_access_token({
        "sub": str(user.id),
        "tenant_id": str(user.tenant_id),
        "role": user.role,
    })

    return {
        "access_token": token,
        "token_type": "bearer",
        "user_id": user.id,
        "tenant_id": user.tenant_id,
        "role": user.role,
        "full_name": user.full_name,
    }
```

---

## 5. `app/api/v1/auth.py`

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=TokenResponse, status_code=201)
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    result = auth_service.register_user(db, data)
    if result is None:
        raise HTTPException(status_code=409, detail="Email already registered for this tenant")
    return result


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    result = auth_service.login_user(db, data)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return result
```

---

## 6. Update `app/api/deps.py`

Replace the entire file — now tenant_id comes from JWT, not header:

```python
import logging
from typing import Optional
from uuid import UUID
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from jose import JWTError
from app.core.db import get_db
from app.core.security import decode_token
from app.models.user import User
from sqlalchemy import select

logger = logging.getLogger(__name__)

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    db: Session = Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    # Keep X-Tenant-ID as fallback for dev/testing only
    x_tenant_id: Optional[str] = Header(default=None),
) -> User:
    """
    Extracts user from JWT Bearer token.
    Falls back to X-Tenant-ID header (dev mode only — no user object returned).
    """
    if credentials:
        try:
            payload = decode_token(credentials.credentials)
            user_id = payload.get("sub")
            if not user_id:
                raise HTTPException(status_code=401, detail="Invalid token payload")

            user = db.execute(
                select(User).where(User.id == UUID(user_id), User.is_active == True)
            ).scalar_one_or_none()

            if not user:
                raise HTTPException(status_code=401, detail="User not found or inactive")

            return user
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate token",
                headers={"WWW-Authenticate": "Bearer"},
            )

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )


def require_tenant_id(
    current_user: User = Depends(get_current_user),
) -> str:
    """Returns tenant_id string from the authenticated user's token."""
    return str(current_user.tenant_id)


def require_dispatcher(current_user: User = Depends(get_current_user)) -> User:
    """Only allows dispatcher or admin roles."""
    if current_user.role not in ("dispatcher", "admin", "superadmin"):
        raise HTTPException(status_code=403, detail="Dispatcher role required")
    return current_user


def require_driver(current_user: User = Depends(get_current_user)) -> User:
    """Only allows driver role."""
    if current_user.role != "driver":
        raise HTTPException(status_code=403, detail="Driver role required")
    return current_user


def get_db_and_tenant(
    db: Session = Depends(get_db),
    tenant_id: str = Depends(require_tenant_id),
):
    """Convenience: returns (db, tenant_id) tuple."""
    return db, tenant_id
```

---

## 7. Update `app/api/router.py`

Add auth router:
```python
from app.api.v1 import auth
api_router.include_router(auth.router, prefix="/api/v1")
```

---

## 8. Update `scripts/seed_data.py`

Add a dispatcher and driver user for the demo tenant at the end of the `seed()` function:

```python
from app.core.security import hash_password

# Add after customers are created, before db.commit():
dispatcher = User(
    id=uuid.uuid4(), tenant_id=tenant.id,
    email="dispatcher@demo.com",
    hashed_password=hash_password("demo1234"),
    full_name="Demo Dispatcher",
    role="dispatcher", is_active=True,
)
driver_user = User(
    id=uuid.uuid4(), tenant_id=tenant.id,
    email="driver@demo.com",
    hashed_password=hash_password("demo1234"),
    full_name="Demo Driver",
    role="driver", is_active=True,
)
db.add(dispatcher)
db.add(driver_user)

print(f"  ✅ Demo users created")
print(f"     Dispatcher: dispatcher@demo.com / demo1234")
print(f"     Driver:     driver@demo.com / demo1234")
```

---

## 9. File Checklist

| Action | File | Status |
|--------|------|--------|
| ADD deps | `requirements.txt` (python-jose, passlib) | ⬜ |
| ADD config | `.env` + `app/core/config.py` (JWT fields) | ⬜ |
| CREATE | `app/core/security.py` | ⬜ |
| CREATE | `app/schemas/auth.py` | ⬜ |
| CREATE | `app/services/auth_service.py` | ⬜ |
| CREATE | `app/api/v1/auth.py` | ⬜ |
| REPLACE | `app/api/deps.py` | ⬜ |
| MODIFY | `app/api/router.py` | ⬜ |
| MODIFY | `scripts/seed_data.py` (add demo users) | ⬜ |

---

## 10. Verification

```bash
# Register a dispatcher
curl -s -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "dispatcher@demo.com",
    "password": "demo1234",
    "full_name": "Demo Dispatcher",
    "role": "dispatcher",
    "tenant_id": "<your-tenant-uuid>"
  }' | jq .

# Login
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "dispatcher@demo.com",
    "password": "demo1234",
    "tenant_id": "<your-tenant-uuid>"
  }' | jq -r .access_token)

# Use token on protected endpoint
curl -s http://localhost:8000/api/v1/depots/ \
  -H "Authorization: Bearer $TOKEN" | jq .

# Driver cannot access dispatcher endpoints
DRIVER_TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -d '{"email":"driver@demo.com","password":"demo1234","tenant_id":"<uuid>"}' \
  -H "Content-Type: application/json" | jq -r .access_token)

curl -s -X POST "http://localhost:8000/api/v1/plan/day?plan_date=2026-01-15" \
  -H "Authorization: Bearer $DRIVER_TOKEN"
# Expected: 403 Forbidden (if planning endpoint uses require_dispatcher)
```

---

**Document Status:** Not Started  
**Last Updated:** 2026-03-29
