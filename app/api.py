import hashlib
import hmac
import json
import urllib.parse
from fastapi import HTTPException, Query, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import settings
from app.db.session import AsyncSessionFactory
from app.services.foods import get_all_categories
from app.services.promo import validate_promo
from typing import Optional
import logging

logger = logging.getLogger(__name__)


def verify_telegram_init_data(init_data: str) -> Optional[dict]:
    try:
        parsed = dict(urllib.parse.parse_qsl(init_data, keep_blank_values=True))
        received_hash = parsed.pop("hash", None)
        if not received_hash:
            return None
        data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed.items()))
        secret_key = hmac.new(b"WebAppData", settings.BOT_TOKEN.encode(), hashlib.sha256).digest()
        calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
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


async def api_categories(
    init_data: str = Query(default=""),
    session: AsyncSession = Depends(get_db),
):
    if init_data and not verify_telegram_init_data(init_data):
        raise HTTPException(status_code=403, detail="Invalid initData")
    cats = await get_all_categories(session)
    return [{"id": c.id, "name": c.name} for c in cats]


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


async def api_promo_validate(
    code: str = Query(...),
    init_data: str = Query(default=""),
    session: AsyncSession = Depends(get_db),
):
    if init_data and not verify_telegram_init_data(init_data):
        raise HTTPException(status_code=403, detail="Invalid initData")
    result = await validate_promo(session, code)
    if not result:
        raise HTTPException(status_code=404, detail="Promo-kod topilmadi yoki muddati o'tgan")
    return result
