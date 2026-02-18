from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from app.models.courier import Courier
from typing import List


def get_admin_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🍔 Taomlar", callback_data="admin:foods"),
         InlineKeyboardButton(text="📂 Kategoriyalar", callback_data="admin:categories")],
        [InlineKeyboardButton(text="🎁 Promokodlar", callback_data="admin:promos"),
         InlineKeyboardButton(text="📊 Statistika", callback_data="admin:stats")],
        [InlineKeyboardButton(text="🚴 Kuryerlar", callback_data="admin:couriers"),
         InlineKeyboardButton(text="📦 Aktiv buyurtmalar", callback_data="admin:active_orders")],
        [InlineKeyboardButton(text="⚙️ Sozlamalar", callback_data="admin:settings")],
    ])


def get_stats_period_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📅 Bugun", callback_data="stats:today"),
            InlineKeyboardButton(text="📆 Hafta", callback_data="stats:week"),
            InlineKeyboardButton(text="🗓 Oy", callback_data="stats:month"),
        ],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin:back")],
    ])


def get_courier_assign_keyboard(couriers: List[Courier], order_id: int) -> InlineKeyboardMarkup:
    buttons = []
    for courier in couriers:
        buttons.append([
            InlineKeyboardButton(
                text=f"🚴 {courier.name}",
                callback_data=f"assign_courier:{order_id}:{courier.id}",
            )
        ])
    buttons.append([InlineKeyboardButton(text="❌ Bekor qilish", callback_data="assign_cancel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_foods_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Qo'shish", callback_data="food:add")],
        [InlineKeyboardButton(text="📋 Ro'yxat", callback_data="food:list")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin:back")],
    ])


def get_couriers_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Kuryer qo'shish", callback_data="courier:add")],
        [InlineKeyboardButton(text="📋 Ro'yxat", callback_data="courier:list")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin:back")],
    ])


def get_promos_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Promokod yaratish", callback_data="promo:create")],
        [InlineKeyboardButton(text="📋 Ro'yxat", callback_data="promo:list")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin:back")],
    ])


def get_categories_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Kategoriya qo'shish", callback_data="cat:add")],
        [InlineKeyboardButton(text="📋 Ro'yxat", callback_data="cat:list")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin:back")],
    ])


def get_back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin:back")]
    ])
