from aiogram import Router, F
from aiogram.types import CallbackQuery
from app.db.session import AsyncSessionFactory
from app.services.courier import get_all_couriers
from app.services.orders import get_order_by_id, update_order_status
from app.services.settings_service import get_shop_channel_id
from app.services.telegram_notify import update_channel_message, notify_user_status
import logging

router = Router()
logger = logging.getLogger(__name__)


async def get_courier_by_channel(session, channel_id: int):
    """Kanal ID si bo'yicha kuryer topish"""
    from app.models.courier import Courier
    from sqlalchemy import select
    result = await session.execute(
        select(Courier).where(Courier.channel_id == channel_id, Courier.is_active == True)
    )
    return result.scalar_one_or_none()


@router.callback_query(F.data.startswith("courier_accept:"))
async def courier_accept(call: CallbackQuery):
    # Xabar qaysi chatdan keldi - o'sha chat_id kuryer kanaliga mos kelishi kerak
    chat_id = call.message.chat.id  # Kanal/guruh ID si
    order_id = int(call.data.split(":")[1])

    logger.info(f"courier_accept: chat_id={chat_id}, order_id={order_id}, from_user={call.from_user.id}")

    async with AsyncSessionFactory() as session:
        courier = await get_courier_by_channel(session, chat_id)

        if not courier:
            # Fallback: shaxsiy chat orqali ham tekshir
            from app.services.courier import get_courier_by_chat_id
            courier = await get_courier_by_chat_id(session, call.from_user.id)

        if not courier:
            all_c = await get_all_couriers(session)
            logger.warning(f"Courier not found. chat_id={chat_id}, user_id={call.from_user.id}, all={[(c.chat_id, c.channel_id, c.name) for c in all_c]}")
            await call.answer(
                f"❌ Bu kanal ro'yxatda yo'q.\nKanal ID: {chat_id}",
                show_alert=True
            )
            return

        order = await get_order_by_id(session, order_id)
        if not order:
            await call.answer("❌ Buyurtma topilmadi", show_alert=True)
            return

        order = await update_order_status(session, order_id, "OUT_FOR_DELIVERY")
        await notify_user_status(call.bot, order.user.tg_id, order)

        shop_channel_id = await get_shop_channel_id(session)
        if shop_channel_id and order.channel_message_id:
            await update_channel_message(call.bot, shop_channel_id, order.channel_message_id, order)

    await call.answer("✅ Qabul qildingiz!")
    try:
        await call.message.edit_text(
            call.message.text + "\n\n✅ QABUL QILINDI",
            reply_markup=None
        )
    except Exception:
        pass


@router.callback_query(F.data.startswith("courier_delivered:"))
async def courier_delivered(call: CallbackQuery):
    chat_id = call.message.chat.id
    order_id = int(call.data.split(":")[1])

    logger.info(f"courier_delivered: chat_id={chat_id}, order_id={order_id}")

    async with AsyncSessionFactory() as session:
        courier = await get_courier_by_channel(session, chat_id)

        if not courier:
            from app.services.courier import get_courier_by_chat_id
            courier = await get_courier_by_chat_id(session, call.from_user.id)

        if not courier:
            await call.answer(
                f"❌ Bu kanal ro'yxatda yo'q.\nKanal ID: {chat_id}",
                show_alert=True
            )
            return

        order = await get_order_by_id(session, order_id)
        if not order:
            await call.answer("❌ Buyurtma topilmadi", show_alert=True)
            return

        order = await update_order_status(session, order_id, "DELIVERED")
        await notify_user_status(call.bot, order.user.tg_id, order)

        shop_channel_id = await get_shop_channel_id(session)
        if shop_channel_id and order.channel_message_id:
            await update_channel_message(
                call.bot, shop_channel_id, order.channel_message_id, order, closed=True
            )

    await call.answer("✅ Yetkazildi!")
    try:
        await call.message.edit_text(
            call.message.text + "\n\n✅ YETKAZILDI",
            reply_markup=None
        )
    except Exception:
        pass
