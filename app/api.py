import hashlib
import hmac
import json
import urllib.parse
from fastapi import HTTPException, Query, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import settings
from app.db.session import AsyncSessionFactory
from app.services.foods import get_all_categories
from app.services.promo import validate_promo
from typing import Optional
import logging

logger = logging.getLogger(__name__)


def verify_telegram_init_data(init_data: str) -> Optional[dict]:
    try:
        parsed = dict(urllib.parse.parse_qsl(init_data, keep_blank_values=True))
        received_hash = parsed.pop("hash", None)
        if not received_hash:
            return None
        data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed.items()))
        secret_key = hmac.new(b"WebAppData", settings.BOT_TOKEN.encode(), hashlib.sha256).digest()
        calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(calculated_hash, received_hash):
            return None
        user_data = parsed.get("user")
        if user_data:
            return json.loads(user_data)
        return parsed
    except Exception as e:
        logger.error(f"InitData verify error: {e}")
        return None


async def get_db():
    async with AsyncSessionFactory() as session:
        yield session


async def api_categories(
    init_data: str = Query(default=""),
    session: AsyncSession = Depends(get_db),
):
    if init_data and not verify_telegram_init_data(init_data):
        raise HTTPException(status_code=403, detail="Invalid initData")
    cats = await get_all_categories(session)
    return [{"id": c.id, "name": c.name} for c in cats]


async def api_foods(
    category_id: Optional[int] = Query(default=None),
    sort: Optional[str] = Query(default=None),
    init_data: str = Query(default=""),
    session: AsyncSession = Depends(get_db),
):
    if init_data and not verify_telegram_init_data(init_data):
        raise HTTPException(status_code=403, detail="Invalid initData")

    from sqlalchemy import select
    from app.models.food import Food as FoodModel

    query = select(FoodModel).where(FoodModel.is_active == True)
    if category_id:
        query = query.where(FoodModel.category_id == category_id)
    if sort == "rating":
        query = query.order_by(FoodModel.rating.desc())
    elif sort == "new":
        query = query.order_by(FoodModel.created_at.desc())
    elif sort == "price_asc":
        query = query.order_by(FoodModel.price.asc())
    elif sort == "price_desc":
        query = query.order_by(FoodModel.price.desc())

    result = await session.execute(query)
    foods = result.scalars().all()
    return [
        {
            "id": f.id,
            "name": f.name,
            "description": f.description,
            "price": f.price,
            "rating": f.rating,
            "is_new": f.is_new,
            "image_url": f.image_url,
            "category_id": f.category_id,
        }
        for f in foods
    ]


async def api_promo_validate(
    code: str = Query(...),
    init_data: str = Query(default=""),
    session: AsyncSession = Depends(get_db),
):
    if init_data and not verify_telegram_init_data(init_data):
        raise HTTPException(status_code=403, detail="Invalid initData")
    result = await validate_promo(session, code)
    if not result:
        raise HTTPException(status_code=404, detail="Promo-kod topilmadi yoki muddati o'tgan")
    return result


# ─────────────────────────────────────────────
# POST /api/orders  — brauzerdan buyurtma qabul qilish
# ─────────────────────────────────────────────
from pydantic import BaseModel
from typing import List, Any
from sqlalchemy import select, desc
from app.models.user import User
from app.models.order import Order
from app.services.orders import create_order, set_channel_message_id
from app.services.promo import use_promo
from app.services.settings_service import get_shop_channel_id
import time

_order_cooldown: dict[int, float] = {}
ORDER_COOLDOWN = 60


class OrderItemIn(BaseModel):
    food_id: int
    name: str
    qty: int
    price: float


class OrderCreateRequest(BaseModel):
    items: List[OrderItemIn]
    total: float
    customer_name: str
    phone: str
    comment: str | None = None
    location: dict
    promo_code: str | None = None
    created_at_client: str | None = None


async def api_create_order(
    body: OrderCreateRequest,
    init_data: str = Query(default=""),
    session: AsyncSession = Depends(get_db),
):
    """Brauzer va Telegram WebApp uchun buyurtma yaratish endpointi."""
    # Telegram initData bilan foydalanuvchini topish
    tg_user = None
    if init_data:
        tg_user = verify_telegram_init_data(init_data)

    # Validatsiya
    if body.total < 50000:
        raise HTTPException(status_code=400, detail="Minimal buyurtma summasi — 50 000 so'm.")
    if not body.items:
        raise HTTPException(status_code=400, detail="Savat bo'sh.")
    lat = body.location.get("lat")
    lng = body.location.get("lng")
    if not lat or not lng:
        raise HTTPException(status_code=400, detail="Joylashuv ko'rsatilmagan.")

    # Foydalanuvchini topish (Telegram ID bo'lsa)
    user = None
    if tg_user:
        tg_id = tg_user.get("id")
        if tg_id:
            # Cooldown tekshirish
            now = time.time()
            last = _order_cooldown.get(tg_id, 0)
            if now - last < ORDER_COOLDOWN:
                # DB da ham tekshirish
                from datetime import datetime, timedelta, timezone
                cutoff = datetime.now(timezone.utc) - timedelta(seconds=ORDER_COOLDOWN)
                dup_result = await session.execute(
                    select(Order)
                    .join(User, Order.user_id == User.id)
                    .where(User.tg_id == tg_id)
                    .where(Order.created_at >= cutoff)
                    .order_by(desc(Order.created_at))
                    .limit(1)
                )
                if dup_result.scalar_one_or_none():
                    raise HTTPException(status_code=429, detail="Iltimos, biroz kuting.")
            _order_cooldown[tg_id] = now

            result = await session.execute(select(User).where(User.tg_id == tg_id))
            user = result.scalar_one_or_none()

    # Agar user topilmasa — telefon raqam bo'yicha qidirish yoki yangi yaratish
    if not user:
        # Guest foydalanuvchi yaratish (Telegram ID si yo'q)
        import random
        guest_tg_id = -(random.randint(10_000_000, 99_999_999))  # manfiy — real Telegram ID emas
        user = User(
            tg_id=guest_tg_id,
            full_name=body.customer_name,
            username=None,
        )
        session.add(user)
        await session.flush()

    # Promo tekshirish
    if body.promo_code:
        promo_info = await validate_promo(session, body.promo_code)
        if not promo_info:
            raise HTTPException(status_code=400, detail="Promokod yaroqsiz yoki muddati o'tgan.")
        await use_promo(session, body.promo_code)

    # Buyurtma yaratish
    items_data = [i.model_dump() for i in body.items]
    order = await create_order(
        session=session,
        user_id=user.id,
        customer_name=body.customer_name,
        phone=body.phone,
        comment=body.comment,
        total=body.total,
        location_lat=lat,
        location_lng=lng,
        items=items_data,
        promo_code=body.promo_code,
    )

    # Admin kanalga yuborish
    shop_channel_id = await get_shop_channel_id(session)
    if shop_channel_id:
        from aiogram import Bot
        from app.config import settings
        from app.services.telegram_notify import send_order_to_channel
        _bot = Bot(token=settings.BOT_TOKEN)
        try:
            msg_id = await send_order_to_channel(_bot, shop_channel_id, order)
            if msg_id:
                await set_channel_message_id(session, order.id, msg_id)
        finally:
            await _bot.session.close()

    return {
        "ok": True,
        "order_number": order.order_number,
        "total": order.total,
        "message": f"✅ Buyurtmangiz #{order.order_number} qabul qilindi!",
    }
