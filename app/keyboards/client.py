from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    WebAppInfo,
)
from app.config import settings


def get_main_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🛍 Заказать", web_app=WebAppInfo(url=settings.WEBAPP_URL))],
            [KeyboardButton(text="📦 Мои заказы"), KeyboardButton(text="ℹ️ Информация о нас")],
            [KeyboardButton(text="👥 Пригласить друга")],
        ],
        resize_keyboard=True,
    )


def get_shop_inline(webapp_url: str = None) -> InlineKeyboardMarkup:
    url = webapp_url or settings.WEBAPP_URL
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛍 Заказать", web_app=WebAppInfo(url=url))]
    ])
