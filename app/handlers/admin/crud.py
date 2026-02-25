from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from app.handlers.admin.states import (
    FoodAddStates, PromoCreateStates, CourierAddStates, CategoryAddStates, SettingsStates
)
from app.db.session import AsyncSessionFactory
from app.services.foods import (
    get_all_categories, create_food, get_foods_by_category, delete_food, create_category, delete_category
)
from app.services.promo import create_promo, get_all_promos
from app.services.courier import add_courier, get_all_couriers, disable_courier, remove_courier
from app.services.settings_service import set_setting
from app.config import settings
from app.keyboards.admin import get_admin_menu, get_back_keyboard
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime, timezone
import logging

router = Router()
logger = logging.getLogger(__name__)


def is_admin(uid: int): return uid in settings.admin_ids


# ===== FOOD HANDLERS =====

@router.callback_query(F.data == "food:add")
async def food_add_start(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id): return
    async with AsyncSessionFactory() as session:
        cats = await get_all_categories(session)
    if not cats:
        await call.answer("Avval kategoriya qo'shing!", show_alert=True)
        return
    await state.set_state(FoodAddStates.waiting_category)
    await state.update_data(categories={cat.id: cat.name for cat in cats})
    buttons = [[InlineKeyboardButton(text=cat.name, callback_data=f"food_cat:{cat.id}")] for cat in cats]
    buttons.append([InlineKeyboardButton(text="❌ Bekor", callback_data="admin:foods")])
    await call.message.edit_text("📂 Kategoriyani tanlang:", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


@router.callback_query(F.data.startswith("food_cat:"), FoodAddStates.waiting_category)
async def food_cat_selected(call: CallbackQuery, state: FSMContext):
    cat_id = int(call.data.split(":")[1])
    await state.update_data(category_id=cat_id)
    await state.set_state(FoodAddStates.waiting_name)
    await call.message.edit_text("🍔 Taom nomini kiriting:")


@router.message(FoodAddStates.waiting_name)
async def food_name_entered(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(FoodAddStates.waiting_description)
    await message.answer("📝 Qisqa tavsif kiriting (yoki - bosing):")


@router.message(FoodAddStates.waiting_description)
async def food_desc_entered(message: Message, state: FSMContext):
    desc = message.text if message.text != "-" else None
    await state.update_data(description=desc)
    await state.set_state(FoodAddStates.waiting_price)
    await message.answer("💰 Narxni kiriting (so'm):")


@router.message(FoodAddStates.waiting_price)
async def food_price_entered(message: Message, state: FSMContext):
    try:
        price = float(message.text.replace(",", "").replace(" ", ""))
    except ValueError:
        await message.answer("❌ Noto'g'ri narx. Qaytadan kiriting:")
        return
    await state.update_data(price=price)
    await state.set_state(FoodAddStates.waiting_rating)
    await message.answer("⭐ Reyting (1-5, yoki - = 5):")


@router.message(FoodAddStates.waiting_rating)
async def food_rating_entered(message: Message, state: FSMContext):
    if message.text == "-":
        rating = 5.0
    else:
        try:
            rating = float(message.text)
        except ValueError:
            await message.answer("❌ Noto'g'ri reyting:")
            return
    await state.update_data(rating=rating)
    await state.set_state(FoodAddStates.waiting_image)
    await message.answer(
        "🖼 Rasm yuboring (galereyadan yoki fayldan)\n"
        "Yoki o'tkazib yuborish uchun - yozing:"
    )


@router.message(FoodAddStates.waiting_image)
async def food_image_entered(message: Message, state: FSMContext):
    # Rasm yuborilgan bo'lsa — file_id olamiz
    if message.photo:
        # Eng yuqori sifatli rasmni olamiz (oxirgi element)
        photo = message.photo[-1]
        file = await message.bot.get_file(photo.file_id)
        token = message.bot.token
        file_url = f"https://api.telegram.org/file/bot{token}/{file.file_path}"
        await state.update_data(image_url=file_url)
    elif message.document and message.document.mime_type and message.document.mime_type.startswith("image/"):
        # Fayl sifatida yuborilgan rasm
        file = await message.bot.get_file(message.document.file_id)
        token = message.bot.token
        file_url = f"https://api.telegram.org/file/bot{token}/{file.file_path}"
        await state.update_data(image_url=file_url)
    elif message.text == "-":
        await state.update_data(image_url=None)
    else:
        await message.answer(
            "❌ Rasm yuboring (foto yoki fayl shaklida)\n"
            "Yoki o'tkazib yuborish uchun - yozing:"
        )
        return
    await state.set_state(FoodAddStates.waiting_is_new)
    await message.answer("🆕 Yangi taommi? (ha/yo'q):")


@router.message(FoodAddStates.waiting_is_new)
async def food_is_new_entered(message: Message, state: FSMContext):
    is_new = message.text.lower() in ("ha", "yes", "1", "+")
    data = await state.get_data()
    await state.clear()
    async with AsyncSessionFactory() as session:
        food = await create_food(
            session,
            category_id=data["category_id"],
            name=data["name"],
            description=data.get("description"),
            price=data["price"],
            rating=data.get("rating", 5.0),
            image_url=data.get("image_url"),
            is_new=is_new,
            is_active=True,
        )
    await message.answer(
        f"✅ Taom qo'shildi:\n{food.name} — {int(food.price):,} сум",
        reply_markup=get_admin_menu()
    )


@router.callback_query(F.data == "food:list")
async def food_list(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    async with AsyncSessionFactory() as session:
        foods = await get_foods_by_category(session)
    if not foods:
        await call.message.edit_text("Taomlar yo'q.", reply_markup=get_back_keyboard())
        return
    buttons = []
    for food in foods[:20]:
        buttons.append([
            InlineKeyboardButton(text=f"{food.name} — {int(food.price):,}", callback_data=f"food_del:{food.id}")
        ])
    buttons.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin:foods")])
    await call.message.edit_text(
        "🍔 Taomlar (o'chirish uchun bosing):",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )


@router.callback_query(F.data.startswith("food_del:"))
async def food_delete(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    food_id = int(call.data.split(":")[1])
    async with AsyncSessionFactory() as session:
        ok = await delete_food(session, food_id)
    if ok:
        await call.answer("✅ O'chirildi")
    else:
        await call.answer("❌ Topilmadi")
    await food_list(call)


# ===== CATEGORY HANDLERS =====

@router.callback_query(F.data == "cat:add")
async def cat_add_start(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id): return
    await state.set_state(CategoryAddStates.waiting_name)
    await call.message.edit_text("📂 Yangi kategoriya nomini kiriting:")


@router.message(CategoryAddStates.waiting_name)
async def cat_name_entered(message: Message, state: FSMContext):
    await state.clear()
    async with AsyncSessionFactory() as session:
        cat = await create_category(session, message.text)
    await message.answer(f"✅ Kategoriya qo'shildi: {cat.name}", reply_markup=get_admin_menu())


@router.callback_query(F.data == "cat:list")
async def cat_list(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    async with AsyncSessionFactory() as session:
        cats = await get_all_categories(session)
    if not cats:
        await call.message.edit_text("Kategoriyalar yo'q.", reply_markup=get_back_keyboard())
        return
    buttons = [[InlineKeyboardButton(text=f"{c.name}", callback_data=f"cat_del:{c.id}")] for c in cats]
    buttons.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin:categories")])
    await call.message.edit_text("📂 Kategoriyalar (o'chirish):", reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


@router.callback_query(F.data.startswith("cat_del:"))
async def cat_delete(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    cat_id = int(call.data.split(":")[1])
    async with AsyncSessionFactory() as session:
        ok = await delete_category(session, cat_id)
    await call.answer("✅ O'chirildi" if ok else "❌ Topilmadi")
    await cat_list(call)


# ===== PROMO HANDLERS =====

@router.callback_query(F.data == "promo:create")
async def promo_create_start(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id): return
    await state.set_state(PromoCreateStates.waiting_code)
    await call.message.edit_text("🎁 Promokod kodini kiriting (masalan: FIESTA20):")


@router.message(PromoCreateStates.waiting_code)
async def promo_code_entered(message: Message, state: FSMContext):
    await state.update_data(code=message.text.upper())
    await state.set_state(PromoCreateStates.waiting_discount)
    await message.answer("💸 Chegirma foizini kiriting (1-90):")


@router.message(PromoCreateStates.waiting_discount)
async def promo_discount_entered(message: Message, state: FSMContext):
    try:
        d = float(message.text)
        if not 1 <= d <= 90:
            raise ValueError
    except ValueError:
        await message.answer("❌ 1 dan 90 gacha son kiriting:")
        return
    await state.update_data(discount=d)
    await state.set_state(PromoCreateStates.waiting_expires)
    await message.answer("📅 Muddati kiriting (DD.MM.YYYY) yoki - (muddatsiz):")


@router.message(PromoCreateStates.waiting_expires)
async def promo_expires_entered(message: Message, state: FSMContext):
    expires_at = None
    if message.text != "-":
        try:
            expires_at = datetime.strptime(message.text, "%d.%m.%Y").replace(tzinfo=timezone.utc)
        except ValueError:
            await message.answer("❌ Format: DD.MM.YYYY yoki -:")
            return
    await state.update_data(expires_at=expires_at)
    await state.set_state(PromoCreateStates.waiting_limit)
    await message.answer("🔢 Foydalanish limiti (sonni kiriting yoki - cheksiz):")


@router.message(PromoCreateStates.waiting_limit)
async def promo_limit_entered(message: Message, state: FSMContext):
    usage_limit = None
    if message.text != "-":
        try:
            usage_limit = int(message.text)
        except ValueError:
            await message.answer("❌ Butun son yoki -:")
            return
    data = await state.get_data()
    await state.clear()
    async with AsyncSessionFactory() as session:
        promo = await create_promo(
            session,
            code=data["code"],
            discount_percent=data["discount"],
            expires_at=data.get("expires_at"),
            usage_limit=usage_limit,
        )
    await message.answer(
        f"✅ Promokod yaratildi:\nKod: {promo.code}\nChegirma: {promo.discount_percent}%",
        reply_markup=get_admin_menu()
    )


@router.callback_query(F.data == "promo:list")
async def promo_list(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    async with AsyncSessionFactory() as session:
        promos = await get_all_promos(session)
    if not promos:
        await call.message.edit_text("Promokodlar yo'q.", reply_markup=get_back_keyboard())
        return
    text = "🎁 Promokodlar:\n\n"
    for p in promos:
        status = "✅" if p.is_active else "❌"
        text += f"{status} {p.code} — {p.discount_percent}% | Ishlatildi: {p.used_count}/{p.usage_limit or '∞'}\n"
    await call.message.edit_text(text, reply_markup=get_back_keyboard())


# ===== COURIER HANDLERS =====

@router.callback_query(F.data == "courier:add")
async def courier_add_start(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id): return
    await state.set_state(CourierAddStates.waiting_name)
    await call.message.edit_text(
        "🚴 Yangi kuryer qo'shish\n\n"
        "1️⃣ Kuryer ismini kiriting:"
    )


@router.message(CourierAddStates.waiting_name)
async def courier_name_entered(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(CourierAddStates.waiting_chat_id)
    await message.answer(
        "2️⃣ Kuryerning shaxsiy Telegram chat ID sini kiriting:\n\n"
        "📌 Kuryer @userinfobot ga /start yuborsab, o'z ID sini oladi"
    )


@router.message(CourierAddStates.waiting_chat_id)
async def courier_chat_id_entered(message: Message, state: FSMContext):
    try:
        chat_id = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Faqat raqam kiriting (masalan: 123456789):")
        return
    await state.update_data(chat_id=chat_id)
    await state.set_state(CourierAddStates.waiting_channel_id)
    await message.answer(
        "3️⃣ Kuryerning kanal/guruh chat ID sini kiriting:\n\n"
        "📌 Kanal/guruhga @userinfobot qo'shib, u yuborgan ID ni kiriting\n"
        "⚠️ Bot o'sha kanalga admin bo'lishi kerak!\n"
        "Misol: -1001234567890"
    )


@router.message(CourierAddStates.waiting_channel_id)
async def courier_channel_id_entered(message: Message, state: FSMContext):
    try:
        channel_id = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Noto'g'ri format. Misol: -1001234567890")
        return
    data = await state.get_data()
    await state.clear()
    async with AsyncSessionFactory() as session:
        courier = await add_courier(
            session,
            chat_id=data["chat_id"],
            name=data["name"],
            channel_id=channel_id,
        )
    await message.answer(
        f"✅ Kuryer qo'shildi!\n\n"
        f"👤 Ism: {courier.name}\n"
        f"🆔 Chat ID: {courier.chat_id}\n"
        f"📢 Kanal ID: {courier.channel_id}",
        reply_markup=get_admin_menu()
    )


@router.callback_query(F.data == "courier:list")
async def courier_list(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    async with AsyncSessionFactory() as session:
        couriers = await get_all_couriers(session)
    if not couriers:
        await call.message.edit_text("Kuryerlar yo'q.", reply_markup=get_back_keyboard())
        return
    buttons = []
    for c in couriers:
        status = "🟢" if c.is_active else "🔴"
        channel_info = f" | 📢{c.channel_id}" if c.channel_id else " | 📢—"
        buttons.append([
            InlineKeyboardButton(
                text=f"{status} {c.name}{channel_info}",
                callback_data=f"courier_toggle:{c.id}"
            ),
            InlineKeyboardButton(
                text="🗑️",
                callback_data=f"courier_delete:{c.id}"
            ),
        ])
    buttons.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin:couriers")])
    await call.message.edit_text(
        "🚴 Kuryerlar:\n(Nomga bosing — holat o'zgartirish | 🗑️ — o'chirish)",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )


@router.callback_query(F.data.startswith("courier_toggle:"))
async def courier_toggle(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    courier_id = int(call.data.split(":")[1])
    async with AsyncSessionFactory() as session:
        from app.services.courier import get_courier_by_id
        courier = await get_courier_by_id(session, courier_id)
        if courier:
            courier.is_active = not courier.is_active
            await session.commit()
    await call.answer("Holat o'zgartirildi")
    await courier_list(call)


@router.callback_query(F.data.startswith("courier_delete:"))
async def courier_delete_confirm(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    courier_id = int(call.data.split(":")[1])
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Ha, o'chir", callback_data=f"courier_delete_yes:{courier_id}"),
            InlineKeyboardButton(text="❌ Yo'q", callback_data="courier:list"),
        ]
    ])
    await call.message.edit_text(
        "⚠️ Kuryerni o'chirishni tasdiqlaysizmi?\n\n"
        "Diqqat: Kuryerga biriktirilgan buyurtmalar saqlanib qoladi.",
        reply_markup=kb
    )


@router.callback_query(F.data.startswith("courier_delete_yes:"))
async def courier_delete_yes(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    courier_id = int(call.data.split(":")[1])
    async with AsyncSessionFactory() as session:
        ok = await remove_courier(session, courier_id)
    if ok:
        await call.answer("✅ Kuryer o'chirildi", show_alert=True)
    else:
        await call.answer("❌ Kuryer topilmadi", show_alert=True)
    await courier_list(call)


# ===== SETTINGS HANDLERS =====

@router.callback_query(F.data == "settings:shop_channel")
async def settings_shop_channel(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id): return
    await state.set_state(SettingsStates.waiting_shop_channel)
    await call.message.edit_text(
        "📢 Shop channel ID kiriting (masalan: -1001234567890):\n"
        "Bot kanalga admin bo'lishi kerak!"
    )


@router.message(SettingsStates.waiting_shop_channel)
async def settings_shop_channel_entered(message: Message, state: FSMContext):
    try:
        channel_id = int(message.text)
    except ValueError:
        await message.answer("❌ To'g'ri ID kiriting:")
        return
    await state.clear()
    async with AsyncSessionFactory() as session:
        await set_setting(session, "shop_channel_id", str(channel_id))
    await message.answer(f"✅ Shop channel sozlandi: {channel_id}", reply_markup=get_admin_menu())


@router.callback_query(F.data == "settings:courier_channel")
async def settings_courier_channel(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id): return
    await state.set_state(SettingsStates.waiting_courier_channel)
    await call.message.edit_text("🚴 Courier channel ID kiriting:")


@router.message(SettingsStates.waiting_courier_channel)
async def settings_courier_channel_entered(message: Message, state: FSMContext):
    try:
        channel_id = int(message.text)
    except ValueError:
        await message.answer("❌ To'g'ri ID kiriting:")
        return
    await state.clear()
    async with AsyncSessionFactory() as session:
        await set_setting(session, "courier_channel_id", str(channel_id))
    await message.answer(f"✅ Courier channel sozlandi: {channel_id}", reply_markup=get_admin_menu())
