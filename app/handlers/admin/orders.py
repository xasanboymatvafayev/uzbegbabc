from aiogram import Router, F
from aiogram.types import CallbackQuery
from app.db.session import AsyncSessionFactory
from app.services.orders import get_order_by_id, update_order_status
from app.services.courier import get_active_couriers, get_courier_by_id
from app.services.settings_service import get_shop_channel_id
from app.services.telegram_notify import update_channel_message, notify_user_status, notify_courier
from app.models.order import OrderStatus
from app.keyboards.admin import get_courier_assign_keyboard
from app.config import settings
import logging

router = Router()
logger = logging.getLogger(__name__)


def is_admin(uid: int): return uid in settings.admin_ids


@router.callback_query(F.data.startswith("admin_status:"))
async def admin_change_status(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer("❌ Ruxsat yo'q")
        return
    _, order_id_str, status_str = call.data.split(":")
    order_id = int(order_id_str)
    try:
        new_status = OrderStatus(status_str)
    except ValueError:
        await call.answer("❌ Noto'g'ri status")
        return

    async with AsyncSessionFactory() as session:
        order = await update_order_status(session, order_id, new_status)
        if not order:
            await call.answer("❌ Buyurtma topilmadi")
            return

        await notify_user_status(call.bot, order.user.tg_id, order)

        shop_channel_id = await get_shop_channel_id(session)
        if shop_channel_id and order.channel_message_id:
            closed = new_status in (OrderStatus.DELIVERED, OrderStatus.CANCELED)
            await update_channel_message(call.bot, shop_channel_id, order.channel_message_id, order, closed=closed)

    from app.models.order import STATUS_LABELS
    status_label = STATUS_LABELS.get(new_status, new_status)
    await call.answer(f"✅ Status: {status_label}")


@router.callback_query(F.data.startswith("assign_courier_start:"))
async def assign_courier_start(call: CallbackQuery):
    order_id = int(call.data.split(":")[1])
    async with AsyncSessionFactory() as session:
        couriers = await get_active_couriers(session)
        if not couriers:
            await call.answer("Aktiv kuryerlar yo'q!", show_alert=True)
            return
        order = await get_order_by_id(session, order_id)
        if not order:
            await call.answer("Buyurtma topilmadi", show_alert=True)
            return

    await call.message.edit_reply_markup(
        reply_markup=get_courier_assign_keyboard(couriers, order_id)
    )


@router.callback_query(F.data == "assign_cancel")
async def assign_cancel(call: CallbackQuery):
    await call.answer("Bekor qilindi")
    async with AsyncSessionFactory() as session:
        from sqlalchemy import select
        from app.models.order import Order
        result = await session.execute(
            select(Order).where(Order.channel_message_id == call.message.message_id)
        )
        order = result.scalar_one_or_none()
        if order:
            from app.services.telegram_notify import get_admin_channel_keyboard
            await call.message.edit_reply_markup(reply_markup=get_admin_channel_keyboard(order))


@router.callback_query(F.data.startswith("assign_courier:"))
async def assign_courier(call: CallbackQuery):
    parts = call.data.split(":")
    order_id = int(parts[1])
    courier_id = int(parts[2])

    async with AsyncSessionFactory() as session:
        courier = await get_courier_by_id(session, courier_id)
        if not courier:
            await call.answer("Kuryer topilmadi", show_alert=True)
            return

        order = await update_order_status(
            session, order_id, OrderStatus.COURIER_ASSIGNED, courier_id=courier_id
        )
        if not order:
            await call.answer("Buyurtma topilmadi", show_alert=True)
            return

        await notify_user_status(call.bot, order.user.tg_id, order)

        # Kuryerning o'z kanaliga yuborish
        success = await notify_courier(call.bot, courier, order)

        shop_channel_id = await get_shop_channel_id(session)
        if shop_channel_id and order.channel_message_id:
            await update_channel_message(call.bot, shop_channel_id, order.channel_message_id, order)

    if success:
        await call.answer(f"✅ {courier.name} ga yuborildi!")
    else:
        await call.answer("⚠️ Kuryerga xabar yuborishda xato")
