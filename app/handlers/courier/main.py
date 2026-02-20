from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from app.db.session import AsyncSessionFactory
from app.services.courier import get_courier_by_chat_id
from app.services.orders import get_order_by_id, update_order_status
from app.services.settings_service import get_shop_channel_id
from app.services.telegram_notify import update_channel_message, notify_user_status
from app.models.order import OrderStatus
import logging

router = Router()
logger = logging.getLogger(__name__)


def get_status_keyboard(is_active: bool) -> InlineKeyboardMarkup:
    """Holatga qarab tugmalar: bosilgan holat ko'rinib turadi"""
    if is_active:
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ 🟢 Ishda (hozirgi)", callback_data="courier_status:active")],
            [InlineKeyboardButton(text="🔴 Ishda emas", callback_data="courier_status:inactive")],
        ])
    else:
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🟢 Ishda", callback_data="courier_status:active")],
            [InlineKeyboardButton(text="✅ 🔴 Ishda emas (hozirgi)", callback_data="courier_status:inactive")],
        ])


@router.message(Command("status"))
async def courier_status_cmd(message: Message):
    """Faqat ro'yxatdagi kuryerlar uchun"""
    chat_id = message.from_user.id
    async with AsyncSessionFactory() as session:
        courier = await get_courier_by_chat_id(session, chat_id)

    if not courier:
        # Kuryer emas — javob bermaymiz (boshqa handlerga tegmasin)
        return

    status_text = "🟢 Ishda (aktiv)" if courier.is_active else "🔴 Ishda emas"
    await message.answer(
        f"👤 {courier.name}\n"
        f"📊 Hozirgi holat: {status_text}\n\n"
        f"Holatni o'zgartirish:",
        reply_markup=get_status_keyboard(courier.is_active)
    )


@router.callback_query(F.data == "courier_status:active")
async def set_courier_active(call: CallbackQuery):
    chat_id = call.from_user.id
    async with AsyncSessionFactory() as session:
        courier = await get_courier_by_chat_id(session, chat_id)
        if not courier:
            await call.answer("❌ Siz kuryer emassiz.", show_alert=True)
            return
        if courier.is_active:
            await call.answer("Siz allaqachon ishdaSiz!", show_alert=False)
            return
        courier.is_active = True
        await session.commit()
        name = courier.name

    await call.answer("✅ Siz endi ishdaSiz!", show_alert=True)
    await call.message.edit_text(
        f"👤 {name}\n"
        f"📊 Hozirgi holat: 🟢 Ishda (aktiv)\n\n"
        f"Holatni o'zgartirish:",
        reply_markup=get_status_keyboard(True)
    )


@router.callback_query(F.data == "courier_status:inactive")
async def set_courier_inactive(call: CallbackQuery):
    chat_id = call.from_user.id
    async with AsyncSessionFactory() as session:
        courier = await get_courier_by_chat_id(session, chat_id)
        if not courier:
            await call.answer("❌ Siz kuryer emassiz.", show_alert=True)
            return
        if not courier.is_active:
            await call.answer("Siz allaqachon ishda emassiz!", show_alert=False)
            return
        courier.is_active = False
        await session.commit()
        name = courier.name

    await call.answer("🔴 Siz endi ishda emasiz.", show_alert=True)
    await call.message.edit_text(
        f"👤 {name}\n"
        f"📊 Hozirgi holat: 🔴 Ishda emas\n\n"
        f"Holatni o'zgartirish:",
        reply_markup=get_status_keyboard(False)
    )


# ===== BUYURTMA QABUL VA YETKAZISH =====

@router.callback_query(F.data.startswith("courier_accept:"))
async def courier_accept(call: CallbackQuery):
    user_chat_id = call.from_user.id
    order_id = int(call.data.split(":")[1])

    async with AsyncSessionFactory() as session:
        courier = await get_courier_by_chat_id(session, user_chat_id)
        if not courier or not courier.is_active:
            await call.answer("❌ Siz ro'yxatdan o'tmagan yoki aktiv emas.", show_alert=True)
            return

        order = await get_order_by_id(session, order_id)
        if not order:
            await call.answer("❌ Buyurtma topilmadi", show_alert=True)
            return

        # Faqat o'sha kuryerga tayinlangan buyurtmani qabul qila oladi
        if order.courier_id != courier.id:
            await call.answer("❌ Bu buyurtma sizga tegishli emas.", show_alert=True)
            return

        order = await update_order_status(session, order_id, OrderStatus.OUT_FOR_DELIVERY)
        await notify_user_status(call.bot, order.user.tg_id, order)

        shop_channel_id = await get_shop_channel_id(session)
        if shop_channel_id and order.channel_message_id:
            await update_channel_message(call.bot, shop_channel_id, order.channel_message_id, order)

    await call.answer("✅ Qabul qildingiz!")
    try:
        await call.message.edit_text(
            call.message.text + "\n\n✅ QABUL QILINDI",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📦 Yetkazildi", callback_data=f"courier_delivered:{order_id}")]
            ])
        )
    except Exception:
        pass


@router.callback_query(F.data.startswith("courier_delivered:"))
async def courier_delivered(call: CallbackQuery):
    user_chat_id = call.from_user.id
    order_id = int(call.data.split(":")[1])

    async with AsyncSessionFactory() as session:
        courier = await get_courier_by_chat_id(session, user_chat_id)
        if not courier or not courier.is_active:
            await call.answer("❌ Siz ro'yxatdan o'tmagan yoki aktiv emas.", show_alert=True)
            return

        order = await get_order_by_id(session, order_id)
        if not order:
            await call.answer("❌ Buyurtma topilmadi", show_alert=True)
            return

        if order.courier_id != courier.id:
            await call.answer("❌ Bu buyurtma sizga tegishli emas.", show_alert=True)
            return

        order = await update_order_status(session, order_id, OrderStatus.DELIVERED)
        await notify_user_status(call.bot, order.user.tg_id, order)

        shop_channel_id = await get_shop_channel_id(session)
        if shop_channel_id and order.channel_message_id:
            await update_channel_message(
                call.bot, shop_channel_id, order.channel_message_id, order, closed=True
            )

    await call.answer("✅ Yetkazildi!", show_alert=True)
    try:
        await call.message.edit_text(
            call.message.text + "\n\n✅ YETKAZILDI",
            reply_markup=None
        )
    except Exception:
        pass
