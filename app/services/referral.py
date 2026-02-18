from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.user import User
from app.models.order import Order, OrderStatus
from typing import Optional


async def get_or_create_user(
    session: AsyncSession,
    tg_id: int,
    username: Optional[str],
    full_name: str,
    ref_tg_id: Optional[int] = None,
) -> tuple[User, bool]:
    result = await session.execute(select(User).where(User.tg_id == tg_id))
    user = result.scalar_one_or_none()
    if user:
        return user, False

    ref_user = None
    if ref_tg_id and ref_tg_id != tg_id:
        r = await session.execute(select(User).where(User.tg_id == ref_tg_id))
        ref_user = r.scalar_one_or_none()

    user = User(
        tg_id=tg_id,
        username=username,
        full_name=full_name,
        ref_by_user_id=ref_user.id if ref_user else None,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user, True


async def get_referral_stats(session: AsyncSession, user_id: int) -> dict:
    ref_count_r = await session.execute(
        select(func.count()).where(User.ref_by_user_id == user_id)
    )
    ref_count = ref_count_r.scalar() or 0

    orders_count_r = await session.execute(
        select(func.count()).where(Order.user_id == user_id)
    )
    orders_count = orders_count_r.scalar() or 0

    delivered_r = await session.execute(
        select(func.count()).where(
            Order.user_id == user_id, Order.status == OrderStatus.DELIVERED
        )
    )
    delivered_count = delivered_r.scalar() or 0

    return {
        "ref_count": ref_count,
        "orders_count": orders_count,
        "paid_or_delivered_count": delivered_count,
    }
