import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage
from app.config import settings
from app.db.session import init_db
from app.handlers.client import start as client_start
from app.handlers.client import webapp as client_webapp
from app.handlers.admin import main as admin_main
from app.handlers.admin import crud as admin_crud
from app.handlers.admin import orders as admin_orders
from app.handlers.courier import main as courier_main

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def main():
    logger.info("Starting Fiesta Bot...")
    await init_db()

    storage = RedisStorage.from_url(settings.REDIS_URL)
    bot = Bot(token=settings.BOT_TOKEN)
    dp = Dispatcher(storage=storage)

    # Register routers
    dp.include_router(client_start.router)
    dp.include_router(client_webapp.router)
    dp.include_router(admin_main.router)
    dp.include_router(admin_crud.router)
    dp.include_router(admin_orders.router)
    dp.include_router(courier_main.router)

    logger.info("Bot started. Polling...")
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
