from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, cast, String
from sqlalchemy.orm import selectinload
from app.models.order import Order, OrderStatus
from app.models.order_item import OrderItem
from typing import List, Optional
import uuid
from datetime import datetime, timezone


def generate_order_number() -> str:
    return f"F{uuid.uuid4().hex[:8].upper()}"


async def create_order(
    session: AsyncSession,
    user_id: int,
    customer_name: str,
    phone: str,
    comment: Optional[str],
    total: float,
    location_lat: Optional[float],
    location_lng: Optional[float],
    items: list,
    promo_code: Optional[str] = None,
) -> Order:
    order_number = generate_order_number()
    order = Order(
        order_number=order_number,
        user_id=user_id,
        customer_name=customer_name,
        phone=phone,
        comment=comment,
        total=total,
        status="NEW",
        location_lat=location_lat,
        location_lng=location_lng,
        promo_code=promo_code,
    )
    session.add(order)
    await session.flush()

    for item in items:
        oi = OrderItem(
            order_id=order.id,
            food_id=item.get("food_id"),
            name_snapshot=item["name"],
            price_snapshot=item["price"],
            qty=item["qty"],
            line_total=item["price"] * item["qty"],
        )
        session.add(oi)

    await session.commit()
    await session.refresh(order)
    return order


async def get_order_by_id(session: AsyncSession, order_id: int) -> Optional[Order]:
    result = await session.execute(
        select(Order)
        .options(selectinload(Order.items), selectinload(Order.user), selectinload(Order.courier))
        .where(Order.id == order_id)
    )
    return result.scalar_one_or_none()


async def get_order_by_number(session: AsyncSession, order_number: str) -> Optional[Order]:
    result = await session.execute(
        select(Order)
        .options(selectinload(Order.items), selectinload(Order.user), selectinload(Order.courier))
        .where(Order.order_number == order_number)
    )
    return result.scalar_one_or_none()


async def get_user_orders(session: AsyncSession, user_id: int, limit: int = 10) -> List[Order]:
    result = await session.execute(
        select(Order)
        .options(selectinload(Order.items))
        .where(Order.user_id == user_id)
        .order_by(Order.created_at.desc())
        .limit(limit)
    )
    return result.scalars().all()


async def get_active_orders(session: AsyncSession) -> List[Order]:
    active_statuses = ["NEW", "CONFIRMED", "COOKING", "COURIER_ASSIGNED", "OUT_FOR_DELIVERY"]
    result = await session.execute(
        select(Order)
        .options(selectinload(Order.items), selectinload(Order.user), selectinload(Order.courier))
        .where(cast(Order.status, String).in_(active_statuses))
        .order_by(Order.created_at.desc())
    )
    return result.scalars().all()


async def update_order_status(
    session: AsyncSession, order_id: int, status, **kwargs
) -> Optional[Order]:
    order = await get_order_by_id(session, order_id)
    if not order:
        return None
    # Store as string to avoid enum cast issues
    order.status = status.value if hasattr(status, 'value') else str(status)
    if str(status) in ("DELIVERED", "OrderStatus.DELIVERED"):
        order.delivered_at = datetime.now(timezone.utc)
    for k, v in kwargs.items():
        setattr(order, k, v)
    await session.commit()
    await session.refresh(order)
    return order


async def set_channel_message_id(session: AsyncSession, order_id: int, message_id: int):
    order = await get_order_by_id(session, order_id)
    if order:
        order.channel_message_id = message_id
        await session.commit()
