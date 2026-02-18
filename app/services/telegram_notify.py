from aiogram import Bot
from app.models.order import Order, OrderStatus, STATUS_LABELS
from app.models.courier import Courier
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import logging

logger = logging.getLogger(__name__)


def format_order_items(order: Order) -> str:
    lines = []
    for item in order.items:
        lines.append(f"  • {item.name_snapshot} x{item.qty} = {int(item.line_total):,} сум")
    return "\n".join(lines)


def get_admin_channel_keyboard(order: Order) -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text="✅ Подтвержден", callback_data=f"admin_status:{order.id}:CONFIRMED"),
            InlineKeyboardButton(text="🍳 Готовится", callback_data=f"admin_status:{order.id}:COOKING"),
        ],
        [
            InlineKeyboardButton(text="🚴 Назначить курьера", callback_data=f"assign_courier_start:{order.id}"),
            InlineKeyboardButton(text="❌ Отменить", callback_data=f"admin_status:{order.id}:CANCELED"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_closed_order_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[])


def format_admin_channel_message(order: Order) -> str:
    status_label = STATUS_LABELS.get(order.status, order.status)
    geo_link = ""
    if order.location_lat and order.location_lng:
        geo_link = f"\n📍 <a href='https://maps.google.com/?q={order.location_lat},{order.location_lng}'>Локация #{order.order_number}</a>"

    items_text = format_order_items(order)
    user = order.user
    username_str = f"(@{user.username})" if user.username else ""

    return (
        f"{'🆕' if order.status == OrderStatus.NEW else '📦'} Заказ #{order.order_number}\n"
        f"👤 {user.full_name} {username_str}\n"
        f"📞 {order.phone}\n"
        f"💰 {int(order.total):,} сум\n"
        f"🕒 {order.created_at.strftime('%d.%m.%Y %H:%M')}\n"
        f"📦 Статус: {status_label}{geo_link}\n\n"
        f"🍽️ Состав:\n{items_text}"
        + (f"\n\n💬 {order.comment}" if order.comment else "")
    )


async def send_order_to_channel(bot: Bot, channel_id: int, order: Order) -> int | None:
    if not channel_id:
        return None
    try:
        msg = await bot.send_message(
            chat_id=channel_id,
            text=format_admin_channel_message(order),
            reply_markup=get_admin_channel_keyboard(order),
            parse_mode="HTML",
        )
        return msg.message_id
    except Exception as e:
        logger.error(f"Failed to send to channel: {e}")
        return None


async def update_channel_message(bot: Bot, channel_id: int, message_id: int, order: Order, closed: bool = False):
    if not channel_id or not message_id:
        return
    try:
        keyboard = get_closed_order_keyboard() if closed else get_admin_channel_keyboard(order)
        await bot.edit_message_text(
            chat_id=channel_id,
            message_id=message_id,
            text=format_admin_channel_message(order),
            reply_markup=keyboard,
            parse_mode="HTML",
        )
    except Exception as e:
        logger.error(f"Failed to update channel message: {e}")


async def notify_user_status(bot: Bot, user_tg_id: int, order: Order):
    status = order.status
    status_label = STATUS_LABELS.get(status, status)
    try:
        if status == OrderStatus.NEW:
            text = (
                f"✅ Ваш заказ принят!\n"
                f"🆔 Заказ #{order.order_number}\n"
                f"💰 Сумма: {int(order.total):,} сум\n"
                f"📦 Статус: {status_label}"
            )
        elif status == OrderStatus.OUT_FOR_DELIVERY:
            text = f"🚴 Ваш заказ #{order.order_number} передан курьеру!"
        elif status == OrderStatus.DELIVERED:
            text = f"🎉 Ваш заказ #{order.order_number} успешно доставлен!\nСпасибо, что выбрали FIESTA!"
        elif status == OrderStatus.CANCELED:
            text = f"❌ Ваш заказ #{order.order_number} отменён."
        else:
            text = f"📦 Заказ #{order.order_number}: статус изменён на «{status_label}»"
        await bot.send_message(chat_id=user_tg_id, text=text)
    except Exception as e:
        logger.error(f"Failed to notify user {user_tg_id}: {e}")


async def notify_courier(bot: Bot, courier: Courier, order: Order) -> bool:
    items_text = format_order_items(order)
    geo_link = f"https://maps.google.com/?q={order.location_lat},{order.location_lng}" if order.location_lat else "—"
    text = (
        f"🚴 Новый заказ #{order.order_number}\n"
        f"👤 Клиент: {order.customer_name}\n"
        f"📞 Телефон: {order.phone}\n"
        f"💰 Сумма: {int(order.total):,} сум\n"
        f"📍 Локация: {geo_link}\n\n"
        f"🍽️ Список:\n{items_text}"
        + (f"\n\n💬 {order.comment}" if order.comment else "")
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Принять заказ", callback_data=f"courier_accept:{order.id}"),
            InlineKeyboardButton(text="📦 Доставлен", callback_data=f"courier_delivered:{order.id}"),
        ]
    ])
    try:
        await bot.send_message(chat_id=courier.chat_id, text=text, reply_markup=keyboard)
        return True
    except Exception as e:
        logger.error(f"Failed to notify courier {courier.chat_id}: {e}")
        return False
