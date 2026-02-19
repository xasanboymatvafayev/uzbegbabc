from aiogram import Bot
from app.models.order import Order, STATUS_LABELS
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import logging

logger = logging.getLogger(__name__)


def format_order_items(order: Order) -> str:
    lines = []
    for item in order.items:
        lines.append(f"  • {item.name_snapshot} x{item.qty} = {int(item.line_total):,} сум")
    return "\n".join(lines)


def get_admin_channel_keyboard(order: Order) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Подтвержден", callback_data=f"admin_status:{order.id}:CONFIRMED"),
            InlineKeyboardButton(text="🍳 Готовится", callback_data=f"admin_status:{order.id}:COOKING"),
        ],
        [
            InlineKeyboardButton(text="🚴 Назначить курьера", callback_data=f"assign_courier_start:{order.id}"),
            InlineKeyboardButton(text="❌ Отменить", callback_data=f"admin_status:{order.id}:CANCELED"),
        ],
    ])


def get_closed_order_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[])


def get_courier_channel_keyboard(order: Order) -> InlineKeyboardMarkup:
    """Kuryer kanaliga yuboriladigan dastlabki tugmalar"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Qabul qildim", callback_data=f"courier_accept:{order.id}"),
        ]
    ])


def format_admin_channel_message(order: Order) -> str:
    status = order.status if isinstance(order.status, str) else order.status.value
    status_label = STATUS_LABELS.get(status, status)
    geo_link = ""
    if order.location_lat and order.location_lng:
        geo_link = f"\n📍 <a href='https://maps.google.com/?q={order.location_lat},{order.location_lng}'>Lokatsiya</a>"
    items_text = format_order_items(order)
    user = order.user
    username_str = f"(@{user.username})" if user and user.username else ""
    full_name = user.full_name if user else order.customer_name
    emoji = "🆕" if status == "NEW" else "📦"
    return (
        f"{emoji} Заказ #{order.order_number}\n"
        f"👤 {full_name} {username_str}\n"
        f"📞 {order.phone}\n"
        f"💰 {int(order.total):,} сум\n"
        f"🕒 {order.created_at.strftime('%d.%m.%Y %H:%M')}\n"
        f"📦 Статус: {status_label}{geo_link}\n\n"
        f"🍽️ Состав:\n{items_text}"
        + (f"\n\n💬 {order.comment}" if order.comment else "")
    )


def format_courier_message(order: Order) -> str:
    items_text = format_order_items(order)
    geo_url = (
        f"https://maps.google.com/?q={order.location_lat},{order.location_lng}"
        if order.location_lat else None
    )
    geo_line = f"📍 <a href='{geo_url}'>Lokatsiya</a>" if geo_url else "📍 Lokatsiya yo'q"
    return (
        f"🚴 Yangi buyurtma #{order.order_number}\n"
        f"👤 Mijoz: {order.customer_name}\n"
        f"📞 Telefon: {order.phone}\n"
        f"💰 Summa: {int(order.total):,} сум\n"
        f"{geo_line}\n\n"
        f"🍽️ Tarkib:\n{items_text}"
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
        logger.error(f"Failed to send to admin channel {channel_id}: {e}")
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
    status = order.status if isinstance(order.status, str) else order.status.value
    status_label = STATUS_LABELS.get(status, status)
    try:
        if status == "NEW":
            text = (
                f"✅ Buyurtmangiz qabul qilindi!\n"
                f"🆔 #{order.order_number}\n"
                f"💰 {int(order.total):,} сум\n"
                f"📦 Holat: {status_label}"
            )
        elif status == "OUT_FOR_DELIVERY":
            text = f"🚴 Buyurtmangiz #{order.order_number} kuryerga topshirildi!"
        elif status == "DELIVERED":
            text = f"🎉 Buyurtmangiz #{order.order_number} yetkazildi!\nFIESTA ni tanlaganingiz uchun rahmat! 🙏"
        elif status == "CANCELED":
            text = f"❌ Buyurtmangiz #{order.order_number} bekor qilindi."
        else:
            text = f"📦 Buyurtma #{order.order_number}: «{status_label}»"
        await bot.send_message(chat_id=user_tg_id, text=text)
    except Exception as e:
        logger.error(f"Failed to notify user {user_tg_id}: {e}")


async def notify_courier_channel(bot: Bot, courier, order: Order) -> bool:
    """Kuryerning kanaliga buyurtma yuborish - faqat 'Qabul qildim' tugmasi"""
    if not courier.channel_id:
        logger.error(f"Courier {courier.name} has no channel_id!")
        return False
    try:
        await bot.send_message(
            chat_id=courier.channel_id,
            text=format_courier_message(order),
            reply_markup=get_courier_channel_keyboard(order),
            parse_mode="HTML",
        )
        return True
    except Exception as e:
        logger.error(f"Failed to send to courier channel {courier.channel_id}: {e}")
        return False
