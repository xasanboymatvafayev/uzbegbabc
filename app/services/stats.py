from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, cast, String
from app.models.order import Order, OrderStatus
from app.models.order_item import OrderItem
from datetime import datetime, timedelta, timezone


async def get_stats(session: AsyncSession, period: str = "today") -> dict:
    now = datetime.now(timezone.utc)
    if period == "today":
        since = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "week":
        since = now - timedelta(days=7)
    else:
        since = now - timedelta(days=30)

    orders_r = await session.execute(
        select(func.count()).where(Order.created_at >= since)
    )
    orders_count = orders_r.scalar() or 0

    delivered_r = await session.execute(
        select(func.count()).where(
            cast(Order.status, String) == "DELIVERED",
            Order.delivered_at >= since
        )
    )
    delivered_count = delivered_r.scalar() or 0

    revenue_r = await session.execute(
        select(func.sum(Order.total)).where(
            cast(Order.status, String) == "DELIVERED",
            Order.delivered_at >= since
        )
    )
    revenue = revenue_r.scalar() or 0

    active_statuses = ["NEW", "CONFIRMED", "COOKING", "COURIER_ASSIGNED", "OUT_FOR_DELIVERY"]
    active_r = await session.execute(
        select(func.count()).where(
            cast(Order.status, String).in_(active_statuses)
        )
    )
    active_count = active_r.scalar() or 0

    top_foods_r = await session.execute(
        select(OrderItem.name_snapshot, func.sum(OrderItem.qty).label("total_qty"))
        .join(Order, Order.id == OrderItem.order_id)
        .where(Order.created_at >= since)
        .group_by(OrderItem.name_snapshot)
        .order_by(func.sum(OrderItem.qty).desc())
        .limit(5)
    )
    top_foods = [{"name": row[0], "qty": row[1]} for row in top_foods_r]

    return {
        "orders_count": orders_count,
        "delivered_count": delivered_count,
        "revenue": revenue,
        "active_count": active_count,
        "top_foods": top_foods,
        "period": period,
    }
