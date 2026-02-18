import hashlib
import hmac
import json
import urllib.parse
from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import settings
from app.db.session import AsyncSessionFactory, init_db
from app.services.foods import get_all_categories, get_foods_by_category
from app.services.promo import validate_promo
from app.models.food import Food
from app.models.category import Category
from contextlib import asynccontextmanager
from typing import Optional, List
import logging

logger = logging.getLogger(__name__)

app = FastAPI(title="Fiesta API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@asynccontextmanager
async def lifespan(app):
    await init_db()
    yield


app.router.lifespan_context = lifespan


def verify_telegram_init_data(init_data: str) -> Optional[dict]:
    """Verify Telegram WebApp initData hash."""
    try:
        parsed = dict(urllib.parse.parse_qsl(init_data, keep_blank_values=True))
        received_hash = parsed.pop("hash", None)
        if not received_hash:
            return None

        data_check_string = "\n".join(
            f"{k}={v}" for k, v in sorted(parsed.items())
        )
        secret_key = hmac.new(
            b"WebAppData", settings.BOT_TOKEN.encode(), hashlib.sha256
        ).digest()
        calculated_hash = hmac.new(
            secret_key, data_check_string.encode(), hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(calculated_hash, received_hash):
            return None

        user_data = parsed.get("user")
        if user_data:
            return json.loads(user_data)
        return parsed
    except Exception as e:
        logger.error(f"InitData verify error: {e}")
        return None


async def get_db():
    async with AsyncSessionFactory() as session:
        yield session


@app.get("/api/categories")
async def api_categories(
    init_data: str = Query(default=""),
    session: AsyncSession = Depends(get_db),
):
    if init_data and not verify_telegram_init_data(init_data):
        raise HTTPException(status_code=403, detail="Invalid initData")

    cats = await get_all_categories(session)
    return [{"id": c.id, "name": c.name} for c in cats]


@app.get("/api/foods")
async def api_foods(
    category_id: Optional[int] = Query(default=None),
    sort: Optional[str] = Query(default=None),
    init_data: str = Query(default=""),
    session: AsyncSession = Depends(get_db),
):
    if init_data and not verify_telegram_init_data(init_data):
        raise HTTPException(status_code=403, detail="Invalid initData")

    from sqlalchemy import select
    from app.models.food import Food as FoodModel

    query = select(FoodModel).where(FoodModel.is_active == True)
    if category_id:
        query = query.where(FoodModel.category_id == category_id)

    if sort == "rating":
        query = query.order_by(FoodModel.rating.desc())
    elif sort == "new":
        query = query.order_by(FoodModel.created_at.desc())
    elif sort == "price_asc":
        query = query.order_by(FoodModel.price.asc())
    elif sort == "price_desc":
        query = query.order_by(FoodModel.price.desc())

    result = await session.execute(query)
    foods = result.scalars().all()

    return [
        {
            "id": f.id,
            "name": f.name,
            "description": f.description,
            "price": f.price,
            "rating": f.rating,
            "is_new": f.is_new,
            "image_url": f.image_url,
            "category_id": f.category_id,
        }
        for f in foods
    ]


@app.get("/api/promo/validate")
async def api_promo_validate(
    code: str = Query(...),
    init_data: str = Query(default=""),
    session: AsyncSession = Depends(get_db),
):
    if init_data and not verify_telegram_init_data(init_data):
        raise HTTPException(status_code=403, detail="Invalid initData")

    result = await validate_promo(session, code)
    if not result:
        raise HTTPException(status_code=404, detail="Промо-код не найден или истёк")
    return result


@app.get("/")
async def serve_webapp():
    return FileResponse("web_app/index.html")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.API_HOST, port=settings.API_PORT)
