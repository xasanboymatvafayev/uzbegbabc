from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.filters import Command
from sqlalchemy import select
from app.db.session import AsyncSessionFactory
from app.models.courier import Courier
from app.services.orders import get_order_by_id, update_order_status
from app.services.settings_service import get_shop_channel_id
from app.services.telegram_notify import update_channel_message, notify_user_status
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import logging

router = Router()
logger = logging.getLogger(__name__)


def get_delivered_keyboard(order_id: int) -> InlineKeyboardMarkup:
    """Faqat 'Yetkazildi' tugmasi"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📦 Yetkazildi", callback_data=f"courier_delivered:{order_id}")]
    ])


def get_courier_status_keyboard() -> InlineKeyboardMarkup:
    """Kuryer holati tugmalari"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🟢 Ishda", callback_data="courier_status:active"),
            InlineKeyboardButton(text="🔴 Ishda emas", callback_data="courier_status:inactive"),
        ]
    ])


async def get_courier_by_channel(session, channel_id: int):
    result = await session.execute(
        select(Courier).where(Courier.channel_id == channel_id)
    )
    return result.scalar_one_or_none()


async def get_courier_by_chat(session, chat_id: int):
    result = await session.execute(
        select(Courier).where(Courier.chat_id == chat_id)
    )
    return result.scalar_one_or_none()


@router.callback_query(F.data.startswith("courier_accept:"))
async def courier_accept(call: CallbackQuery):
    chat_id = call.message.chat.id
    order_id = int(call.data.split(":")[1])

    async with AsyncSessionFactory() as session:
        courier = await get_courier_by_channel(session, chat_id)
        if not courier:
            courier = await get_courier_by_chat(session, call.from_user.id)
        if not courier:
            await call.answer(f"❌ Kanal ro'yxatda yo'q. ID: {chat_id}", show_alert=True)
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

    await call.answer("✅ Qabul qilindi!")
    # Faqat "Yetkazildi" tugmasini qoldirish
    try:
        await call.message.edit_reply_markup(
            reply_markup=get_delivered_keyboard(order_id)
        )
    except Exception as e:
        logger.error(f"Edit markup error: {e}")


@router.callback_query(F.data.startswith("courier_delivered:"))
async def courier_delivered(call: CallbackQuery):
    chat_id = call.message.chat.id
    order_id = int(call.data.split(":")[1])

    async with AsyncSessionFactory() as session:
        courier = await get_courier_by_channel(session, chat_id)
        if not courier:
            courier = await get_courier_by_chat(session, call.from_user.id)
        if not courier:
            await call.answer(f"❌ Kanal ro'yxatda yo'q. ID: {chat_id}", show_alert=True)
            return

        order = await get_order_by_id(session, order_id)
        if not order:
            await call.answer("❌ Buyurtma topilmadi", show_alert=True)
            return

        # DELIVERED ga o'tkazish (statistika uchun delivered_at yoziladi)
        order = await update_order_status(session, order_id, "DELIVERED")
        await notify_user_status(call.bot, order.user.tg_id, order)

        # Shop kanaldan o'chirish (delete qilish yoki tugmalarni olib tashlash)
        shop_channel_id = await get_shop_channel_id(session)
        if shop_channel_id and order.channel_message_id:
            try:
                await call.bot.delete_message(
                    chat_id=shop_channel_id,
                    message_id=order.channel_message_id
                )
            except Exception:
                # O'chira olmasak yopiq holatga o'tkazamiz
                await update_channel_message(
                    call.bot, shop_channel_id, order.channel_message_id, order, closed=True
                )

    await call.answer("✅ Yetkazildi!")
    # Kuryer kanalida xabarni yangilash
    try:
        await call.message.edit_text(
            call.message.text + "\n\n✅ YETKAZILDI ✅",
            reply_markup=None
        )
    except Exception as e:
        logger.error(f"Edit text error: {e}")


@router.callback_query(F.data.startswith("courier_status:"))
async def courier_status_toggle(call: CallbackQuery):
    """Kuryer holati: ishda / ishda emas"""
    chat_id = call.from_user.id
    new_status = call.data.split(":")[1]  # "active" or "inactive"

    async with AsyncSessionFactory() as session:
        courier = await get_courier_by_chat(session, chat_id)
        if not courier:
            await call.answer("❌ Siz kuryerlar ro'yxatida yo'qsiz!", show_alert=True)
            return

        courier.is_active = (new_status == "active")
        await session.commit()

    status_text = "🟢 Siz endi ishdasiz!" if new_status == "active" else "🔴 Siz ishda emas holatdasiz"
    await call.answer(status_text, show_alert=True)

    try:
        await call.message.edit_reply_markup(reply_markup=get_courier_status_keyboard())
    except Exception:
        pass


@router.message(Command("status"))
async def courier_status_command(message: Message):
    """Kuryer /status buyrug'i - holat o'zgartirish"""
    async with AsyncSessionFactory() as session:
        courier = await get_courier_by_chat(session, message.from_user.id)
        if not courier:
            await message.answer("❌ Siz kuryerlar ro'yxatida yo'qsiz!")
            return

    status = "🟢 Ishda" if courier.is_active else "🔴 Ishda emas"
    await message.answer(
        f"Sizning holatiz: {status}\n\nHolatni o'zgartirish:",
        reply_markup=get_courier_status_keyboard()
    )
