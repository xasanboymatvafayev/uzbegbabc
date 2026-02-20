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
            InlineKeyboardButton(text="✅ Tasdiqlandi", callback_data=f"admin_status:{order.id}:CONFIRMED"),
            InlineKeyboardButton(text="🍳 Tayyorlanmoqda", callback_data=f"admin_status:{order.id}:COOKING"),
        ],
        [
            InlineKeyboardButton(text="🚴 Kuryer tayinlash", callback_data=f"assign_courier_start:{order.id}"),
            InlineKeyboardButton(text="❌ Bekor", callback_data=f"admin_status:{order.id}:CANCELED"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_closed_order_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[])


def format_admin_channel_message(order: Order) -> str:
    status_label = STATUS_LABELS.get(order.status, order.status)
    geo_link = ""
    if order.location_lat and order.location_lng:
        geo_link = f"\n📍 <a href='https://maps.google.com/?q={order.location_lat},{order.location_lng}'>Lokatsiya #{order.order_number}</a>"

    items_text = format_order_items(order)
    user = order.user
    username_str = f"(@{user.username})" if user.username else ""

    courier_info = ""
    if order.courier:
        courier_info = f"\n🚴 Kuryer: {order.courier.name}"

    return (
        f"{'🆕' if order.status == OrderStatus.NEW else '📦'} Zakaz #{order.order_number}\n"
        f"👤 {user.full_name} {username_str}\n"
        f"📞 {order.phone}\n"
        f"💰 {int(order.total):,} сум\n"
        f"🕒 {order.created_at.strftime('%d.%m.%Y %H:%M')}\n"
        f"📦 Status: {status_label}{courier_info}{geo_link}\n\n"
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
                f"✅ Buyurtmangiz qabul qilindi!\n"
                f"🆔 Buyurtma #{order.order_number}\n"
                f"💰 Summa: {int(order.total):,} сум\n"
                f"📦 Status: {status_label}"
            )
        elif status == OrderStatus.OUT_FOR_DELIVERY:
            text = f"🚴 Buyurtmangiz #{order.order_number} kuryerga topshirildi! Tez orada yetkaziladi."
        elif status == OrderStatus.DELIVERED:
            text = f"🎉 Buyurtmangiz #{order.order_number} yetkazildi!\nRahmat, FIESTA ni tanlaganingiz uchun!"
        elif status == OrderStatus.CANCELED:
            text = f"❌ Buyurtmangiz #{order.order_number} bekor qilindi."
        else:
            text = f"📦 Buyurtma #{order.order_number}: status «{status_label}» ga o'zgardi"
        await bot.send_message(chat_id=user_tg_id, text=text)
    except Exception as e:
        logger.error(f"Failed to notify user {user_tg_id}: {e}")


async def notify_courier(bot: Bot, courier: Courier, order: Order) -> bool:
    """
    Buyurtma haqida xabarni kuryer KANALIGA yuboradi.
    Tugmalarni faqat courier.chat_id ga mos odam bosa oladi
    (courier_main.py da tekshiriladi).
    """
    # Kuryer kanalini aniqlash: courier.channel_id bor bo'lsa — u yerga,
    # yo'q bo'lsa — shaxsiy chat_id ga yuborish
    target = courier.channel_id if courier.channel_id else courier.chat_id

    if not target:
        logger.error(f"Courier {courier.id} has no channel_id or chat_id")
        return False

    items_text = format_order_items(order)
    geo_link = f"https://maps.google.com/?q={order.location_lat},{order.location_lng}" if order.location_lat else "—"

    text = (
        f"🚴 Yangi buyurtma #{order.order_number}\n"
        f"👤 Mijoz: {order.customer_name}\n"
        f"📞 Telefon: {order.phone}\n"
        f"💰 Summa: {int(order.total):,} сум\n"
        f"📍 Manzil: {geo_link}\n\n"
        f"🍽️ Tarkib:\n{items_text}"
        + (f"\n\n💬 {order.comment}" if order.comment else "")
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="✅ Qabul qildim",
                callback_data=f"courier_accept:{order.id}"
            ),
        ]
    ])

    try:
        await bot.send_message(
            chat_id=target,
            text=text,
            reply_markup=keyboard,
        )
        return True
    except Exception as e:
        logger.error(f"Failed to notify courier channel {target}: {e}")
        # Agar kanal ishlamasa, shaxsiy chat ga urinish
        if courier.channel_id and courier.chat_id != target:
            try:
                await bot.send_message(
                    chat_id=courier.chat_id,
                    text=text,
                    reply_markup=keyboard,
                )
                return True
            except Exception as e2:
                logger.error(f"Failed to notify courier direct {courier.chat_id}: {e2}")
        return False
