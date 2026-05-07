"""RBAC service — permission checks and role management (P4-E4)."""
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.rbac import RbacRole
from app.models.user import User

# Built-in permission sets that map to legacy string roles.
# These are used for backward-compat when no custom RbacRole exists.
_BUILT_IN: dict[str, list[str]] = {
    "superadmin": ["*"],
    "admin":       ["plan:generate", "plan:read", "order:read", "order:write",
                    "driver:manage", "vehicle:manage", "depot:manage",
                    "audit:read", "governance:admin", "rbac:manage"],
    "dispatcher":  ["plan:generate", "plan:read", "order:read", "order:write",
                    "driver:manage", "vehicle:manage"],
    "driver":      ["order:read", "stop:update"],
}


def check_permission(user: User, permission: str, db: Session) -> bool:
    """Return True if user's role grants the requested permission.

    Checks custom RbacRole rows first; falls back to built-in role map.
    Superadmin wildcard "*" always grants.
    """
    # Try DB-defined role
    role_row = db.execute(
        select(RbacRole).where(
            RbacRole.tenant_id == user.tenant_id,
            RbacRole.name == user.role,
        )
    ).scalar_one_or_none()

    permissions: list[str] = (
        role_row.permissions if role_row else _BUILT_IN.get(user.role or "", [])
    )

    return "*" in permissions or permission in permissions


def create_role(
    db: Session,
    tenant_id: UUID,
    name: str,
    permissions: list[str],
    is_system: bool = False,
) -> RbacRole:
    role = RbacRole(
        tenant_id=tenant_id,
        name=name,
        permissions=permissions,
        is_system=is_system,
    )
    db.add(role)
    db.flush()
    return role


def list_roles(db: Session, tenant_id: UUID) -> list[RbacRole]:
    return db.execute(
        select(RbacRole).where(RbacRole.tenant_id == tenant_id)
    ).scalars().all()


def delete_role(db: Session, role_id: UUID, tenant_id: UUID) -> bool:
    """Delete a non-system role. Returns False if not found or is_system."""
    role = db.execute(
        select(RbacRole).where(
            RbacRole.id == role_id,
            RbacRole.tenant_id == tenant_id,
        )
    ).scalar_one_or_none()

    if not role or role.is_system:
        return False

    db.delete(role)
    db.flush()
    return True
