from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.promo import Promo
from typing import Optional
from datetime import datetime, timezone
import secrets
import string


def generate_promo_code(length: int = 8) -> str:
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


async def validate_promo(session: AsyncSession, code: str) -> Optional[dict]:
    result = await session.execute(select(Promo).where(Promo.code == code.upper()))
    promo = result.scalar_one_or_none()
    if not promo:
        return None
    if not promo.is_active:
        return None
    if promo.expires_at and promo.expires_at < datetime.now(timezone.utc):
        return None
    if promo.usage_limit and promo.used_count >= promo.usage_limit:
        return None
    return {"discount_percent": promo.discount_percent, "code": promo.code}


async def use_promo(session: AsyncSession, code: str):
    result = await session.execute(select(Promo).where(Promo.code == code.upper()))
    promo = result.scalar_one_or_none()
    if promo:
        promo.used_count += 1
        await session.commit()


async def create_promo(
    session: AsyncSession,
    code: str,
    discount_percent: float,
    expires_at=None,
    usage_limit=None,
) -> Promo:
    promo = Promo(
        code=code.upper(),
        discount_percent=discount_percent,
        expires_at=expires_at,
        usage_limit=usage_limit,
    )
    session.add(promo)
    await session.commit()
    await session.refresh(promo)
    return promo


async def get_all_promos(session: AsyncSession):
    result = await session.execute(select(Promo).order_by(Promo.created_at.desc()))
    return result.scalars().all()
