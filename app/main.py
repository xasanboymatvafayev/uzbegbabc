import os
import logging
import traceback
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from aiogram import Bot, Dispatcher
from aiogram.types import Update
from aiogram.fsm.storage.memory import MemoryStorage
from app.config import settings
from app.db.session import init_db

# ---------------- LOGGING ---------------- #
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------- BOT INIT ---------------- #
bot = Bot(token=settings.BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

def setup_routers():
    from app.handlers.client import start as client_start
    from app.handlers.client import webapp as client_webapp
    from app.handlers.admin import main as admin_main
    from app.handlers.admin import crud as admin_crud
    from app.handlers.admin import orders as admin_orders
    from app.handlers.courier import main as courier_main

    dp.include_router(client_start.router)
    dp.include_router(client_webapp.router)
    dp.include_router(admin_main.router)
    dp.include_router(admin_crud.router)
    dp.include_router(admin_orders.router)
    dp.include_router(courier_main.router)

setup_routers()

# ---------------- FASTAPI LIFESPAN ---------------- #
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Starting Bot in Webhook mode")
    await init_db()
    webhook_url = f"{os.environ.get('WEBHOOK_URL', '')}/webhook"
    await bot.set_webhook(webhook_url)
    logger.info(f"✅ Webhook set to: {webhook_url}")
    yield
    logger.info("🛑 Shutting down...")
    await bot.session.close()

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- API ROUTES ---------------- #
from app.api import (
    api_categories,
    api_foods,
    api_promo_validate,
    verify_telegram_init_data,
    get_db,
)
from fastapi import Query, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

app.add_api_route("/api/categories", api_categories, methods=["GET"])
app.add_api_route("/api/foods", api_foods, methods=["GET"])
app.add_api_route("/api/promo/validate", api_promo_validate, methods=["GET"])
# ADMIN ROUTER — shu qatorni qo'shing:
from app.admin_api import router as admin_router
app.include_router(admin_router)

# ---------------- TELEGRAM WEBHOOK ---------------- #
@app.post("/webhook")
async def telegram_webhook(request: Request):
    try:
        data = await request.json()
        update = Update.model_validate(data)
        await dp.feed_update(bot, update)
        return {"ok": True}
    except Exception as e:
        logger.error(f"❌ Webhook error: {e}")
        logger.error(traceback.format_exc())
        return JSONResponse(status_code=500, content={"error": str(e)})

# ---------------- WEBAPP ---------------- #
@app.get("/")
async def serve_webapp():
    index = "web_app/index.html"
    if os.path.exists(index):
        return FileResponse(index)
    return {"status": "running"}

# ---------------- RUN ---------------- #
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
