import os
import logging
from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher
from aiogram.types import Update
from aiogram.fsm.storage.redis import RedisStorage

from app.config import settings
from app.db.session import init_db
from app.handlers.client import start as client_start
from app.handlers.client import webapp as client_webapp
from app.handlers.admin import main as admin_main
from app.handlers.admin import crud as admin_crud
from app.handlers.admin import orders as admin_orders
from app.handlers.courier import main as courier_main

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Bot va Dispatcher
bot = Bot(token=settings.BOT_TOKEN)
storage = RedisStorage.from_url(settings.REDIS_URL)
dp = Dispatcher(storage=storage)

# Routerlarni ulash
dp.include_router(client_start.router)
dp.include_router(client_webapp.router)
dp.include_router(admin_main.router)
dp.include_router(admin_crud.router)
dp.include_router(admin_orders.router)
dp.include_router(courier_main.router)


# 🚀 Startup
@app.on_event("startup")
async def on_startup():
    logger.info("Starting Fiesta Bot (Webhook mode)...")
    await init_db()

    webhook_url = f"{settings.WEBHOOK_URL}/webhook"
    await bot.set_webhook(webhook_url)
    logger.info(f"Webhook set to {webhook_url}")


# 📩 Telegram webhook endpoint
@app.post("/webhook")
async def telegram_webhook(request: Request):
    data = await request.json()
    update = Update.model_validate(data)
    await dp.feed_update(bot, update)
    return {"ok": True}


# 🟢 Healthcheck (Railway uchun kerak)
@app.get("/")
async def root():
    return {"status": "running"}
