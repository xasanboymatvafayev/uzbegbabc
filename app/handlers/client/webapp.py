from aiogram import Router, F
from aiogram.types import Message
from app.db.session import AsyncSessionFactory
from app.services.orders import create_order
from app.services.promo import validate_promo, use_promo
from app.services.settings_service import get_shop_channel_id
from app.services.telegram_notify import send_order_to_channel, notify_user_status
from app.services.orders import set_channel_message_id
from app.models.order import OrderStatus
from sqlalchemy import select
from app.models.user import User
import json
import logging

router = Router()
logger = logging.getLogger(__name__)


@router.message(F.web_app_data)
async def handle_webapp_data(message: Message):
    try:
        data = json.loads(message.web_app_data.data)
    except Exception as e:
        logger.error(f"Failed to parse WebApp data: {e}")
        await message.answer("❌ Ошибка при обработке заказа. Попробуйте ещё раз.")
        return

    if data.get("type") != "order_create":
        return

    total = data.get("total", 0)
    if total < 50000:
        await message.answer("❌ Минимальная сумма заказа — 50 000 сум.")
        return

    items = data.get("items", [])
    if not items:
        await message.answer("❌ Корзина пуста.")
        return

    promo_code = data.get("promo_code")
    location = data.get("location", {})
    lat = location.get("lat")
    lng = location.get("lng")

    if not lat or not lng:
        await message.answer("❌ Укажите местоположение для доставки.")
        return

    async with AsyncSessionFactory() as session:
        result = await session.execute(select(User).where(User.tg_id == message.from_user.id))
        user = result.scalar_one_or_none()
        if not user:
            await message.answer("❌ Пользователь не найден. Используйте /start")
            return

        # Validate promo
        if promo_code:
            promo_info = await validate_promo(session, promo_code)
            if not promo_info:
                await message.answer("❌ Промо-код недействителен или истёк.")
                return
            await use_promo(session, promo_code)

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

        # Notify user
        await notify_user_status(message.bot, message.from_user.id, order)

        # Send to admin channel
        shop_channel_id = await get_shop_channel_id(session)
        if shop_channel_id:
            msg_id = await send_order_to_channel(message.bot, shop_channel_id, order)
            if msg_id:
                await set_channel_message_id(session, order.id, msg_id)
