from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from app.db.session import AsyncSessionFactory
from app.services.referral import get_or_create_user, get_referral_stats
from app.services.orders import get_user_orders
from app.services.promo import create_promo, generate_promo_code
from app.keyboards.client import get_main_keyboard, get_shop_inline
from app.models.order import STATUS_LABELS
from app.config import settings
from sqlalchemy import select
from app.models.user import User
import logging

router = Router()
logger = logging.getLogger(__name__)


@router.message(CommandStart())
async def cmd_start(message: Message):
    args = message.text.split()
    ref_tg_id = None
    if len(args) > 1:
        try:
            ref_tg_id = int(args[1])
        except ValueError:
            pass

    async with AsyncSessionFactory() as session:
        user, is_new = await get_or_create_user(
            session=session,
            tg_id=message.from_user.id,
            username=message.from_user.username,
            full_name=message.from_user.full_name,
            ref_tg_id=ref_tg_id,
        )

    await message.answer(
        f"Добро пожаловать в FIESTA! {message.from_user.full_name} 🎉\n"
        f"Для заказа перейдите по кнопке ➡️",
        reply_markup=get_main_keyboard(),
    )


@router.message(F.text == "📦 Мои заказы")
async def my_orders(message: Message):
    async with AsyncSessionFactory() as session:
        result = await session.execute(
            select(User).where(User.tg_id == message.from_user.id)
        )
        user = result.scalar_one_or_none()
        if not user:
            await message.answer("Вы не зарегистрированы. Используйте /start")
            return

        orders = await get_user_orders(session, user.id)

    if not orders:
        await message.answer(
            "В данный момент у вас нет активных заказов в нашем магазине.\n"
            "Чтобы открыть магазин, введите команду — /shop"
        )
        return

    text = "📦 Ваши последние заказы:\n\n"
    for order in orders:
        status_label = STATUS_LABELS.get(order.status, order.status)
        text += (
            f"🆔 Заказ #{order.order_number} | "
            f"{order.created_at.strftime('%d.%m %H:%M')} | "
            f"💰 {int(order.total):,} сум | "
            f"📦 {status_label}\n"
        )
        for item in order.items:
            text += f"  • {item.name_snapshot} x{item.qty} — {int(item.line_total):,} сум\n"
        text += "\n"

    await message.answer(text)


@router.message(Command("shop"))
@router.message(F.text == "🛍 Заказать")
async def shop_cmd(message: Message):
    await message.answer(
        "Чтобы открыть наш магазин, нажмите кнопку ниже 👇",
        reply_markup=get_shop_inline(),
    )


@router.message(F.text == "ℹ️ Информация о нас")
async def about_us(message: Message):
    text = (
        "🌟 Добро Пожаловать в FIESTA !\n\n"
        "📍 Наш адрес: Хорезмская область, г.Хива, махаллинский сход граждан Гиламчи\n"
        "🏢 Ориентир: Школа №12 Оруджева\n"
        "📞 Контактный номер: +998 91 420 15 15\n"
        "🕙 Рабочие часы: 24/7\n"
        "📷 Мы в Instagram: <a href='https://www.instagram.com/fiesta.khiva?igsh=Z3VoMzE0eGx0ZTVo'>fiesta.khiva</a>\n"
        "🔗 <a href='https://maps.app.goo.gl/dpBVHBWX1K7NTYVR7'>Найти нас на карте</a>"
    )
    await message.answer(text, parse_mode="HTML", disable_web_page_preview=True)


@router.message(F.text == "👥 Пригласить друга")
async def invite_friend(message: Message):
    async with AsyncSessionFactory() as session:
        result = await session.execute(select(User).where(User.tg_id == message.from_user.id))
        user = result.scalar_one_or_none()
        if not user:
            await message.answer("Используйте /start для регистрации")
            return

        stats = await get_referral_stats(session, user.id)
        ref_link = f"https://t.me/{settings.BOT_USERNAME}?start={message.from_user.id}"

        text = (
            f"За приглашение друга, вы можете получить промо-код от нас 🎁\n\n"
            f"👥 Вы пригласили: {stats['ref_count']} человек\n"
            f"🛒 Оформили заказов: {stats['orders_count']}\n"
            f"💰 Оплатили заказов: {stats['paid_or_delivered_count']}\n\n"
            f"👤 Ваша реферальная ссылка:\n{ref_link}\n\n"
            f"Пригласите трех человек и вы получите от нас промо-код со скидкой 15%"
        )

        # Give promo if eligible
        if stats["ref_count"] >= 3 and not user.promo_given:
            code = generate_promo_code()
            promo = await create_promo(session, code=code, discount_percent=15)
            user.promo_given = True
            await session.commit()
            text += f"\n\n🎉 Поздравляем! Ваш промо-код: <b>{promo.code}</b> (скидка 15%)"

    await message.answer(text, parse_mode="HTML")
