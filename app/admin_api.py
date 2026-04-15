"""
app/admin_api.py  — Admin REST API
"""

from fastapi import APIRouter, HTTPException, Query, UploadFile, File
from fastapi.responses import JSONResponse
from sqlalchemy import select, func, cast, String, desc
from sqlalchemy.orm import selectinload
from typing import Optional
from datetime import datetime, timedelta, timezone
from pydantic import BaseModel
import os, uuid, shutil

from app.db.session import AsyncSessionFactory
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.food import Food
from app.models.category import Category
from app.models.courier import Courier
from app.models.promo import Promo
from app.services.settings_service import set_setting, get_setting

router = APIRouter(prefix="/api/admin", tags=["admin"])

UPLOAD_DIR = "web_app/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ──────────────────────────────────────────────────
# Pydantic schemas
# ──────────────────────────────────────────────────

class FoodCreate(BaseModel):
    category_id: int
    name: str
    description: Optional[str] = None
    price: float
    rating: float = 5.0
    image_url: Optional[str] = None
    is_new: bool = False
    is_active: bool = True

class FoodUpdate(BaseModel):
    category_id: Optional[int] = None
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    rating: Optional[float] = None
    image_url: Optional[str] = None
    is_new: Optional[bool] = None
    is_active: Optional[bool] = None

class CategoryCreate(BaseModel):
    name: str

class CourierCreate(BaseModel):
    name: str
    chat_id: int
    channel_id: Optional[int] = None

class PromoCreate(BaseModel):
    code: str
    discount_percent: float
    usage_limit: Optional[int] = None
    expires_at: Optional[datetime] = None

class OrderStatusUpdate(BaseModel):
    status: str

class SettingUpdate(BaseModel):
    key: str
    value: str

# ──────────────────────────────────────────────────
# IMAGE UPLOAD
# ──────────────────────────────────────────────────

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}

@router.post("/upload-image")
async def upload_image(file: UploadFile = File(...)):
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail="Faqat jpg, png, webp, gif ruxsat etilgan")
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else "jpg"
    filename = f"{uuid.uuid4().hex}.{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)
    with open(filepath, "wb") as f:
        shutil.copyfileobj(file.file, f)
    base_url = os.environ.get("WEBHOOK_URL", "")
    url = f"{base_url}/uploads/{filename}"
    return {"url": url, "filename": filename}

# ──────────────────────────────────────────────────
# STATS
# ──────────────────────────────────────────────────

@router.get("/stats")
async def admin_stats(period: str = Query(default="today")):
    now = datetime.now(timezone.utc)
    if period == "today":
        since = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "week":
        since = now - timedelta(days=7)
    else:
        since = now - timedelta(days=30)

    async with AsyncSessionFactory() as session:
        orders_r = await session.execute(select(func.count()).where(Order.created_at >= since))
        orders_count = orders_r.scalar() or 0

        delivered_r = await session.execute(
            select(func.count()).where(
                cast(Order.status, String) == "DELIVERED",
                Order.delivered_at >= since
            )
        )
        delivered_count = delivered_r.scalar() or 0

        revenue_r = await session.execute(
            select(func.sum(Order.total)).where(
                cast(Order.status, String) == "DELIVERED",
                Order.delivered_at >= since
            )
        )
        revenue = float(revenue_r.scalar() or 0)

        active_statuses = ["NEW", "CONFIRMED", "COOKING", "COURIER_ASSIGNED", "OUT_FOR_DELIVERY"]
        active_r = await session.execute(
            select(func.count()).where(cast(Order.status, String).in_(active_statuses))
        )
        active_count = active_r.scalar() or 0

        top_foods_r = await session.execute(
            select(OrderItem.name_snapshot, func.sum(OrderItem.qty).label("total_qty"))
            .join(Order, Order.id == OrderItem.order_id)
            .where(Order.created_at >= since)
            .group_by(OrderItem.name_snapshot)
            .order_by(func.sum(OrderItem.qty).desc())
            .limit(5)
        )
        top_foods = [{"name": row[0], "qty": int(row[1])} for row in top_foods_r]

    return {
        "orders_count": orders_count,
        "delivered_count": delivered_count,
        "revenue": revenue,
        "active_count": active_count,
        "top_foods": top_foods,
        "period": period,
    }

# ──────────────────────────────────────────────────
# ORDERS
# ──────────────────────────────────────────────────

@router.get("/orders")
async def admin_orders(
    status: Optional[str] = None,
    limit: int = Query(default=100, le=500)
):
    active_statuses = ["NEW", "CONFIRMED", "COOKING", "COURIER_ASSIGNED", "OUT_FOR_DELIVERY"]
    async with AsyncSessionFactory() as session:
        q = (
            select(Order)
            .options(selectinload(Order.items), selectinload(Order.user), selectinload(Order.courier))
            .order_by(desc(Order.created_at))
            .limit(limit)
        )
        if status == "active":
            q = q.where(cast(Order.status, String).in_(active_statuses))
        elif status:
            q = q.where(cast(Order.status, String) == status)

        result = await session.execute(q)
        orders = result.scalars().all()

    def ser(o):
        return {
            "id": o.id,
            "order_number": o.order_number,
            "customer_name": o.customer_name,
            "phone": o.phone,
            "comment": o.comment,
            "total": float(o.total),
            "status": o.status,
            "promo_code": o.promo_code,
            "created_at": o.created_at.isoformat() if o.created_at else None,
            "delivered_at": o.delivered_at.isoformat() if o.delivered_at else None,
            "courier": {"id": o.courier.id, "name": o.courier.name} if o.courier else None,
            "items": [
                {
                    "id": it.id,
                    "name_snapshot": it.name_snapshot,
                    "qty": it.qty,
                    "price_snapshot": float(it.price_snapshot),
                    "line_total": float(it.line_total),
                }
                for it in (o.items or [])
            ],
        }

    return [ser(o) for o in orders]


@router.patch("/orders/{order_id}/status")
async def admin_change_order_status(order_id: int, body: OrderStatusUpdate):
    async with AsyncSessionFactory() as session:
        result = await session.execute(
            select(Order).options(selectinload(Order.user)).where(Order.id == order_id)
        )
        order = result.scalar_one_or_none()
        if not order:
            raise HTTPException(status_code=404, detail="Buyurtma topilmadi")
        order.status = body.status
        if body.status == "DELIVERED":
            order.delivered_at = datetime.now(timezone.utc)
        await session.commit()
    return {"ok": True, "status": body.status}

# ──────────────────────────────────────────────────
# FOODS
# ──────────────────────────────────────────────────

@router.post("/foods")
async def admin_create_food(body: FoodCreate):
    async with AsyncSessionFactory() as session:
        food = Food(
            category_id=body.category_id,
            name=body.name,
            description=body.description,
            price=body.price,
            rating=body.rating,
            image_url=body.image_url,
            is_new=body.is_new,
            is_active=body.is_active,
        )
        session.add(food)
        await session.commit()
        await session.refresh(food)
    return {"id": food.id, "name": food.name, "price": float(food.price)}


@router.put("/foods/{food_id}")
async def admin_update_food(food_id: int, body: FoodUpdate):
    async with AsyncSessionFactory() as session:
        result = await session.execute(select(Food).where(Food.id == food_id))
        food = result.scalar_one_or_none()
        if not food:
            raise HTTPException(status_code=404, detail="Taom topilmadi")
        for field, val in body.model_dump(exclude_none=True).items():
            setattr(food, field, val)
        await session.commit()
    return {"ok": True}


@router.delete("/foods/{food_id}")
async def admin_delete_food(food_id: int):
    async with AsyncSessionFactory() as session:
        result = await session.execute(select(Food).where(Food.id == food_id))
        food = result.scalar_one_or_none()
        if not food:
            raise HTTPException(status_code=404, detail="Taom topilmadi")
        await session.delete(food)
        await session.commit()
    return {"ok": True}

# ──────────────────────────────────────────────────
# CATEGORIES
# ──────────────────────────────────────────────────

@router.get("/categories")
async def admin_categories():
    async with AsyncSessionFactory() as session:
        result = await session.execute(select(Category))
        cats = result.scalars().all()
    return [{"id": c.id, "name": c.name, "is_active": c.is_active} for c in cats]


@router.post("/categories")
async def admin_create_category(body: CategoryCreate):
    from sqlalchemy import text
    async with AsyncSessionFactory() as session:
        await session.execute(
            text("SELECT setval('categories_id_seq', GREATEST((SELECT COALESCE(MAX(id), 0) FROM categories), 1))")
        )
        cat = Category(name=body.name)
        session.add(cat)
        await session.commit()
        await session.refresh(cat)
    return {"id": cat.id, "name": cat.name}


@router.delete("/categories/{cat_id}")
async def admin_delete_category(cat_id: int):
    async with AsyncSessionFactory() as session:
        result = await session.execute(select(Category).where(Category.id == cat_id))
        cat = result.scalar_one_or_none()
        if not cat:
            raise HTTPException(status_code=404, detail="Kategoriya topilmadi")
        await session.delete(cat)
        await session.commit()
    return {"ok": True}

# ──────────────────────────────────────────────────
# COURIERS
# ──────────────────────────────────────────────────

@router.get("/couriers")
async def admin_couriers_list():
    async with AsyncSessionFactory() as session:
        result = await session.execute(select(Courier))
        couriers = result.scalars().all()
    return [
        {"id": c.id, "name": c.name, "chat_id": c.chat_id, "channel_id": c.channel_id, "is_active": c.is_active}
        for c in couriers
    ]


@router.post("/couriers")
async def admin_create_courier(body: CourierCreate):
    async with AsyncSessionFactory() as session:
        courier = Courier(name=body.name, chat_id=body.chat_id, channel_id=body.channel_id, is_active=True)
        session.add(courier)
        await session.commit()
        await session.refresh(courier)
    return {"id": courier.id, "name": courier.name}


@router.patch("/couriers/{courier_id}/toggle")
async def admin_toggle_courier(courier_id: int):
    async with AsyncSessionFactory() as session:
        result = await session.execute(select(Courier).where(Courier.id == courier_id))
        courier = result.scalar_one_or_none()
        if not courier:
            raise HTTPException(status_code=404, detail="Kuryer topilmadi")
        courier.is_active = not courier.is_active
        is_active = courier.is_active
        await session.commit()
    return {"ok": True, "is_active": is_active}


@router.delete("/couriers/{courier_id}")
async def admin_delete_courier(courier_id: int):
    async with AsyncSessionFactory() as session:
        result = await session.execute(select(Courier).where(Courier.id == courier_id))
        courier = result.scalar_one_or_none()
        if not courier:
            raise HTTPException(status_code=404, detail="Kuryer topilmadi")
        await session.delete(courier)
        await session.commit()
    return {"ok": True}

# ──────────────────────────────────────────────────
# PROMOS
# ──────────────────────────────────────────────────

@router.get("/promos")
async def admin_promos_list():
    async with AsyncSessionFactory() as session:
        result = await session.execute(select(Promo).order_by(desc(Promo.id)))
        promos = result.scalars().all()
    return [
        {
            "id": p.id, "code": p.code, "discount_percent": p.discount_percent,
            "used_count": p.used_count, "usage_limit": p.usage_limit,
            "is_active": p.is_active,
            "expires_at": p.expires_at.isoformat() if p.expires_at else None,
        }
        for p in promos
    ]


@router.post("/promos")
async def admin_create_promo(body: PromoCreate):
    async with AsyncSessionFactory() as session:
        promo = Promo(
            code=body.code.upper(), discount_percent=body.discount_percent,
            usage_limit=body.usage_limit, expires_at=body.expires_at,
            is_active=True, used_count=0,
        )
        session.add(promo)
        await session.commit()
        await session.refresh(promo)
    return {"id": promo.id, "code": promo.code}


@router.delete("/promos/{promo_id}")
async def admin_delete_promo(promo_id: int):
    async with AsyncSessionFactory() as session:
        result = await session.execute(select(Promo).where(Promo.id == promo_id))
        promo = result.scalar_one_or_none()
        if not promo:
            raise HTTPException(status_code=404, detail="Promokod topilmadi")
        await session.delete(promo)
        await session.commit()
    return {"ok": True}

# ──────────────────────────────────────────────────
# SETTINGS
# ──────────────────────────────────────────────────

@router.get("/settings")
async def admin_get_settings():
    async with AsyncSessionFactory() as session:
        shop = await get_setting(session, "shop_channel_id")
        courier = await get_setting(session, "courier_channel_id")
    return {"shop_channel_id": shop, "courier_channel_id": courier}


@router.post("/settings")
async def admin_save_setting(body: SettingUpdate):
    async with AsyncSessionFactory() as session:
        await set_setting(session, body.key, body.value)
    return {"ok": True}
