from aiogram import Router, F
from aiogram.types import CallbackQuery
from app.db.session import AsyncSessionFactory
from app.services.courier import get_courier_by_chat_id
from app.services.orders import get_order_by_id, update_order_status
from app.services.settings_service import get_shop_channel_id
from app.services.telegram_notify import update_channel_message, notify_user_status
from app.models.order import OrderStatus
import logging

router = Router()
logger = logging.getLogger(__name__)


async def is_courier(bot_obj, chat_id: int) -> bool:
    async with AsyncSessionFactory() as session:
        courier = await get_courier_by_chat_id(session, chat_id)
        return courier is not None and courier.is_active


@router.callback_query(F.data.startswith("courier_accept:"))
async def courier_accept(call: CallbackQuery):
    chat_id = call.from_user.id
    order_id = int(call.data.split(":")[1])

    async with AsyncSessionFactory() as session:
        courier = await get_courier_by_chat_id(session, chat_id)
        if not courier or not courier.is_active:
            await call.answer("❌ Siz ro'yxatdan o'tmagan kuryer siz.", show_alert=True)
            return

        order = await get_order_by_id(session, order_id)
        if not order:
            await call.answer("❌ Buyurtma topilmadi", show_alert=True)
            return

        order = await update_order_status(session, order_id, OrderStatus.OUT_FOR_DELIVERY)

        # Notify user
        await notify_user_status(call.bot, order.user.tg_id, order)

        # Update channel message
        shop_channel_id = await get_shop_channel_id(session)
        if shop_channel_id and order.channel_message_id:
            await update_channel_message(call.bot, shop_channel_id, order.channel_message_id, order)

    await call.answer("✅ Qabul qildingiz!")
    await call.message.edit_text(
        call.message.text + "\n\n✅ QABUL QILINDI",
        reply_markup=None
    )


@router.callback_query(F.data.startswith("courier_delivered:"))
async def courier_delivered(call: CallbackQuery):
    chat_id = call.from_user.id
    order_id = int(call.data.split(":")[1])

    async with AsyncSessionFactory() as session:
        courier = await get_courier_by_chat_id(session, chat_id)
        if not courier or not courier.is_active:
            await call.answer("❌ Siz ro'yxatdan o'tmagan kuryer siz.", show_alert=True)
            return

        order = await get_order_by_id(session, order_id)
        if not order:
            await call.answer("❌ Buyurtma topilmadi", show_alert=True)
            return

        order = await update_order_status(session, order_id, OrderStatus.DELIVERED)

        # Notify user
        await notify_user_status(call.bot, order.user.tg_id, order)

        # Update channel message — mark as closed
        shop_channel_id = await get_shop_channel_id(session)
        if shop_channel_id and order.channel_message_id:
            await update_channel_message(
                call.bot, shop_channel_id, order.channel_message_id, order, closed=True
            )

    await call.answer("✅ Yetkazildi deb belgilandi!")
    await call.message.edit_text(
        call.message.text + "\n\n✅ YETKAZILDI",
        reply_markup=None
    )
