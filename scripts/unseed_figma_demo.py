#!/usr/bin/env python3
"""
Remove all data seeded by seed_figma_demo.py.

Usage:
  python scripts/unseed_figma_demo.py
"""
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from app.core.db import SessionLocal
from app.models import Tenant

FIGMA_TENANT_SLUG = "acme-logistics-figma"


def main():
    db = SessionLocal()
    try:
        tenant = db.execute(
            select(Tenant).where(Tenant.slug == FIGMA_TENANT_SLUG)
        ).scalar_one_or_none()

        if not tenant:
            print(f"ℹ️  No tenant with slug '{FIGMA_TENANT_SLUG}' found — nothing to remove.")
            return

        print(f"🗑️  Removing figma demo tenant '{tenant.name}' and all cascade data...")
        db.delete(tenant)
        db.commit()
        print("✅  Done. All figma demo data removed.")

    except Exception as e:
        db.rollback()
        print(f"❌  Failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
