from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from app.config import settings
from app.keyboards.admin import (
    get_admin_menu, get_stats_period_keyboard, get_foods_menu,
    get_couriers_menu, get_promos_menu, get_categories_menu, get_back_keyboard
)
from app.db.session import AsyncSessionFactory
from app.services.stats import get_stats
from app.services.orders import get_active_orders
from app.services.foods import get_all_categories, get_foods_by_category
from app.services.courier import get_all_couriers
from app.services.promo import get_all_promos
from app.models.order import STATUS_LABELS
import logging

router = Router()
logger = logging.getLogger(__name__)


def is_admin(user_id: int) -> bool:
    return user_id in settings.admin_ids


@router.message(Command("admin"))
async def cmd_admin(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ Sizda ruxsat yo'q.")
        return
    await message.answer("🔧 Admin panel:", reply_markup=get_admin_menu())


@router.callback_query(F.data == "admin:back")
async def admin_back(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text("🔧 Admin panel:", reply_markup=get_admin_menu())


@router.callback_query(F.data == "admin:stats")
async def admin_stats(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return
    await call.message.edit_text("📊 Statistika davri:", reply_markup=get_stats_period_keyboard())


@router.callback_query(F.data.startswith("stats:"))
async def show_stats(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return
    period = call.data.split(":")[1]
    async with AsyncSessionFactory() as session:
        data = await get_stats(session, period)

    period_label = {"today": "Bugun", "week": "Hafta", "month": "Oy"}.get(period, period)
    top_text = "\n".join(f"  {i+1}. {f['name']} — {f['qty']} dona" for i, f in enumerate(data["top_foods"])) or "  —"

    text = (
        f"📊 Statistika — {period_label}\n\n"
        f"📦 Jami buyurtmalar: {data['orders_count']}\n"
        f"✅ Yetkazildi: {data['delivered_count']}\n"
        f"💰 Tushum: {int(data['revenue']):,} сум\n"
        f"🔥 Aktiv buyurtmalar: {data['active_count']}\n\n"
        f"🏆 Top taomlar:\n{top_text}"
    )
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin:stats")]
    ])
    await call.message.edit_text(text, reply_markup=kb)


@router.callback_query(F.data == "admin:active_orders")
async def active_orders(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return
    async with AsyncSessionFactory() as session:
        orders = await get_active_orders(session)

    if not orders:
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin:back")]])
        await call.message.edit_text("📦 Hozirda aktiv buyurtmalar yo'q.", reply_markup=kb)
        return

    text = "📦 Aktiv buyurtmalar:\n\n"
    for order in orders:
        status_label = STATUS_LABELS.get(order.status, order.status)
        text += (
            f"#{order.order_number} | {order.customer_name} | "
            f"{int(order.total):,} сум | {status_label}\n"
        )
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin:back")]])
    await call.message.edit_text(text, reply_markup=kb)


@router.callback_query(F.data == "admin:foods")
async def admin_foods(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return
    await call.message.edit_text("🍔 Taomlar:", reply_markup=get_foods_menu())


@router.callback_query(F.data == "admin:categories")
async def admin_categories(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return
    await call.message.edit_text("📂 Kategoriyalar:", reply_markup=get_categories_menu())


@router.callback_query(F.data == "admin:promos")
async def admin_promos(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return
    await call.message.edit_text("🎁 Promokodlar:", reply_markup=get_promos_menu())


@router.callback_query(F.data == "admin:couriers")
async def admin_couriers(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return
    await call.message.edit_text("🚴 Kuryerlar:", reply_markup=get_couriers_menu())


@router.callback_query(F.data == "admin:settings")
async def admin_settings(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    from app.services.settings_service import get_shop_channel_id, get_courier_channel_id
    async with AsyncSessionFactory() as session:
        shop_id = await get_shop_channel_id(session)
        courier_id = await get_courier_channel_id(session)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Shop channel o'rnatish", callback_data="settings:shop_channel")],
        [InlineKeyboardButton(text="🚴 Courier channel o'rnatish", callback_data="settings:courier_channel")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin:back")],
    ])
    await call.message.edit_text(
        f"⚙️ Sozlamalar\n\n"
        f"📢 Shop channel: {shop_id or 'Sozlanmagan'}\n"
        f"🚴 Courier channel: {courier_id or 'Sozlanmagan'}",
        reply_markup=kb
    )
