from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from app.db.session import AsyncSessionFactory
from app.services.courier import get_courier_by_chat_id, get_courier_by_id
from app.services.orders import get_order_by_id, update_order_status
from app.services.settings_service import get_shop_channel_id
from app.services.telegram_notify import update_channel_message, notify_user_status
from app.models.order import OrderStatus
import logging

router = Router()
logger = logging.getLogger(__name__)


@router.callback_query(F.data.startswith("courier_accept:"))
async def courier_accept(call: CallbackQuery):
    """Kuryer 'Qabul qildim' tugmasini bosadi — faqat o'sha kuryer bosa oladi"""
    user_chat_id = call.from_user.id
    order_id = int(call.data.split(":")[1])

    async with AsyncSessionFactory() as session:
        # Faqat shu chat_id ga mos kuryer tasdiqlashi mumkin
        courier = await get_courier_by_chat_id(session, user_chat_id)
        if not courier or not courier.is_active:
            await call.answer("❌ Siz ro'yxatdan o'tmagan kuryer siz.", show_alert=True)
            return

        order = await get_order_by_id(session, order_id)
        if not order:
            await call.answer("❌ Buyurtma topilmadi", show_alert=True)
            return

        # Buyurtma bu kuryerga tegishli ekanligini tekshirish
        if order.courier_id != courier.id:
            await call.answer("❌ Bu buyurtma sizga tegishli emas.", show_alert=True)
            return

        order = await update_order_status(session, order_id, OrderStatus.OUT_FOR_DELIVERY)

        # Foydalanuvchiga xabar
        await notify_user_status(call.bot, order.user.tg_id, order)

        # Shop kanalidagi xabarni yangilash
        shop_channel_id = await get_shop_channel_id(session)
        if shop_channel_id and order.channel_message_id:
            await update_channel_message(call.bot, shop_channel_id, order.channel_message_id, order)

    await call.answer("✅ Qabul qildingiz!")
    try:
        await call.message.edit_text(
            call.message.text + "\n\n✅ QABUL QILINDI — Yetkazilmoqda",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📦 Yetkazildi", callback_data=f"courier_delivered:{order_id}")]
            ])
        )
    except Exception:
        pass


@router.callback_query(F.data.startswith("courier_delivered:"))
async def courier_delivered(call: CallbackQuery):
    """Kuryer 'Yetkazildi' tugmasini bosadi — faqat o'sha kuryer bosa oladi"""
    user_chat_id = call.from_user.id
    order_id = int(call.data.split(":")[1])

    async with AsyncSessionFactory() as session:
        courier = await get_courier_by_chat_id(session, user_chat_id)
        if not courier or not courier.is_active:
            await call.answer("❌ Siz ro'yxatdan o'tmagan kuryer siz.", show_alert=True)
            return

        order = await get_order_by_id(session, order_id)
        if not order:
            await call.answer("❌ Buyurtma topilmadi", show_alert=True)
            return

        if order.courier_id != courier.id:
            await call.answer("❌ Bu buyurtma sizga tegishli emas.", show_alert=True)
            return

        order = await update_order_status(session, order_id, OrderStatus.DELIVERED)

        # Foydalanuvchiga xabar
        await notify_user_status(call.bot, order.user.tg_id, order)

        # Shop kanalidagi xabarni yopiq deb belgilash
        shop_channel_id = await get_shop_channel_id(session)
        if shop_channel_id and order.channel_message_id:
            await update_channel_message(
                call.bot, shop_channel_id, order.channel_message_id, order, closed=True
            )

    await call.answer("✅ Yetkazildi deb belgilandi!", show_alert=True)
    try:
        await call.message.edit_text(
            call.message.text + "\n\n✅ YETKAZILDI",
            reply_markup=None
        )
    except Exception:
        pass
