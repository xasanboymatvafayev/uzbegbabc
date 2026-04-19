from aiogram import Router, F
from aiogram.types import Message
from sqlalchemy import select
import json
import logging
import time

from app.db.session import AsyncSessionFactory
from app.services.orders import create_order, set_channel_message_id
from app.services.promo import validate_promo, use_promo
from app.services.settings_service import get_shop_channel_id
from app.services.telegram_notify import send_order_to_channel, notify_user_status
from app.models.user import User
from app.models.order import Order
from sqlalchemy import cast, String, desc

router = Router()
logger = logging.getLogger(__name__)

# Parallel so'rovlarni bloklash uchun (faqat ichki himoya)
_processing: set = set()
# In-memory cooldown — server restart bo'lsa reset bo'ladi, shuning uchun DB-check asosiy
_last_order_time: dict[int, float] = {}
ORDER_COOLDOWN = 60  # soniya


@router.message(F.web_app_data)
async def handle_webapp_data(message: Message):
    tg_id = message.from_user.id

    # Parallel so'rovni bloklash (bir vaqtda 2 ta xabar kelsa)
    if tg_id in _processing:
        logger.warning(f"Parallel order attempt blocked for {tg_id}")
        return  # Foydalanuvchiga xabar bermaymiz — shunchaki ignore
    _processing.add(tg_id)

    try:
        await _process_order(message, tg_id)
    finally:
        _processing.discard(tg_id)


async def _process_order(message: Message, tg_id: int):
    # In-memory cooldown (tez bloklash, xabar bermasdan)
    now = time.time()
    last = _last_order_time.get(tg_id, 0)
    if now - last < ORDER_COOLDOWN:
        logger.warning(f"In-memory cooldown: user {tg_id}")
        return  # Xabar bermaymiz

    # JSON parse
    try:
        data = json.loads(message.web_app_data.data)
    except Exception as e:
        logger.error(f"WebApp JSON parse error: {e}")
        await message.answer("❌ Buyurtmani qayta ishlashda xatolik.")
        return

    if data.get("type") != "order_create":
        return

    # Validatsiya
    total = data.get("total", 0)
    if total < 50000:
        await message.answer("❌ Minimal buyurtma summasi — 50 000 so'm.")
        return

    items = data.get("items", [])
    if not items:
        await message.answer("❌ Savat bo'sh.")
        return

    location = data.get("location", {})
    lat = location.get("lat")
    lng = location.get("lng")
    if not lat or not lng:
        await message.answer("❌ Yetkazib berish uchun joylashuvni belgilang.")
        return

    promo_code = data.get("promo_code")

    async with AsyncSessionFactory() as session:
        # User topish
        result = await session.execute(select(User).where(User.tg_id == tg_id))
        user = result.scalar_one_or_none()
        if not user:
            await message.answer("❌ Foydalanuvchi topilmadi. /start ni bosing.")
            return

        # DB-level duplicate check
        from datetime import datetime, timedelta, timezone
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=ORDER_COOLDOWN)
        dup_result = await session.execute(
            select(Order)
            .where(Order.user_id == user.id)
            .where(Order.created_at >= cutoff)
            .order_by(desc(Order.created_at))
            .limit(1)
        )
        dup = dup_result.scalar_one_or_none()
        if dup:
            _last_order_time[tg_id] = now
            logger.warning(f"DB duplicate blocked for user {tg_id}, order {dup.order_number}")
            return  # Xabar bermaymiz — foydalanuvchi allaqachon tasdiqlash olgan

        # Cooldown o'rnatish (DB yozishdan OLDIN)
        _last_order_time[tg_id] = now

        # Promo tekshirish
        if promo_code:
            promo_info = await validate_promo(session, promo_code)
            if not promo_info:
                await message.answer("❌ Promokod yaroqsiz yoki muddati o'tgan.")
                return
            await use_promo(session, promo_code)

        # Buyurtma yaratish
        order = await create_order(
            session=session,
            user_id=user.id,
            customer_name=data.get("customer_name", message.from_user.full_name),
            phone=data.get("phone", ""),
            comment=data.get("comment"),
            total=total,
            location_lat=lat,
            location_lng=lng,
            items=items,
            promo_code=promo_code,
        )

        # Foydalanuvchiga xabar
        await notify_user_status(message.bot, tg_id, order)

        # Shop kanalga yuborish
        shop_channel_id = await get_shop_channel_id(session)
        logger.info(f"Shop channel ID: {shop_channel_id}")
        if shop_channel_id:
            msg_id = await send_order_to_channel(message.bot, shop_channel_id, order)
            if msg_id:
                await set_channel_message_id(session, order.id, msg_id)
            else:
                logger.error(f"send_order_to_channel returned None for order {order.order_number}")
                from app.admin_api import _add_log
                _add_log("error", f"❌ #{order.order_number} buyurtma shop kanalga yuborilmadi (channel_id={shop_channel_id}). Bot admin emasmi?")
        else:
            logger.warning("shop_channel_id is 0 or None — kanal sozlanmagan!")
            from app.admin_api import _add_log
            _add_log("warn", "⚠️ Shop kanal ID sozlanmagan! Admin paneldan Sozlamalar > Shop kanal ID ni kiriting.")

    logger.info(f"✅ Order {order.order_number} created for user {tg_id}")
