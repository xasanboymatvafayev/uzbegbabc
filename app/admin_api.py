"""
app/admin_api.py  —  Admin REST API (web panel uchun)
"""
from fastapi import APIRouter, HTTPException, Query, UploadFile, File
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

# ── Schemas ──────────────────────────────────────

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

# ── Image Upload ─────────────────────────────────

ALLOWED = {"image/jpeg", "image/png", "image/webp", "image/gif"}

@router.post("/upload-image")
async def upload_image(file: UploadFile = File(...)):
    if file.content_type not in ALLOWED:
        raise HTTPException(400, "Faqat jpg, png, webp, gif ruxsat")
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in (file.filename or "") else "jpg"
    name = f"{uuid.uuid4().hex}.{ext}"
    with open(os.path.join(UPLOAD_DIR, name), "wb") as f:
        shutil.copyfileobj(file.file, f)
    base = os.environ.get("WEBHOOK_URL", "")
    return {"url": f"{base}/uploads/{name}"}

# ── Stats ─────────────────────────────────────────

@router.get("/stats")
async def admin_stats(period: str = Query("today")):
    now = datetime.now(timezone.utc)
    since = now.replace(hour=0,minute=0,second=0,microsecond=0) if period=="today" else now - timedelta(days=7 if period=="week" else 30)
    async with AsyncSessionFactory() as s:
        cnt   = (await s.execute(select(func.count()).where(Order.created_at>=since))).scalar() or 0
        dlvd  = (await s.execute(select(func.count()).where(cast(Order.status,String)=="DELIVERED", Order.delivered_at>=since))).scalar() or 0
        rev   = float((await s.execute(select(func.sum(Order.total)).where(cast(Order.status,String)=="DELIVERED", Order.delivered_at>=since))).scalar() or 0)
        act   = (await s.execute(select(func.count()).where(cast(Order.status,String).in_(["NEW","CONFIRMED","COOKING","COURIER_ASSIGNED","OUT_FOR_DELIVERY"])))).scalar() or 0
        tops  = (await s.execute(
            select(OrderItem.name_snapshot, func.sum(OrderItem.qty).label("q"))
            .join(Order).where(Order.created_at>=since)
            .group_by(OrderItem.name_snapshot).order_by(func.sum(OrderItem.qty).desc()).limit(5)
        )).all()
    return {"orders_count":cnt,"delivered_count":dlvd,"revenue":rev,"active_count":act,
            "top_foods":[{"name":r[0],"qty":int(r[1])} for r in tops]}

# ── Orders ────────────────────────────────────────

def _ser_order(o):
    return {
        "id": o.id, "order_number": o.order_number,
        "customer_name": o.customer_name, "phone": o.phone,
        "comment": o.comment, "total": float(o.total),
        "status": o.status, "promo_code": o.promo_code,
        "created_at": o.created_at.isoformat() if o.created_at else None,
        "delivered_at": o.delivered_at.isoformat() if o.delivered_at else None,
        "courier": {"id": o.courier.id, "name": o.courier.name} if o.courier else None,
        "items": [{"id":i.id,"name_snapshot":i.name_snapshot,"qty":i.qty,
                   "price_snapshot":float(i.price_snapshot),"line_total":float(i.line_total)}
                  for i in (o.items or [])],
    }

@router.get("/orders")
async def admin_orders(status: Optional[str]=None, limit: int=Query(100,le=500)):
    active = ["NEW","CONFIRMED","COOKING","COURIER_ASSIGNED","OUT_FOR_DELIVERY"]
    async with AsyncSessionFactory() as s:
        q = select(Order).options(selectinload(Order.items),selectinload(Order.user),selectinload(Order.courier)).order_by(desc(Order.created_at)).limit(limit)
        if status=="active": q=q.where(cast(Order.status,String).in_(active))
        elif status: q=q.where(cast(Order.status,String)==status)
        return [_ser_order(o) for o in (await s.execute(q)).scalars().all()]

@router.patch("/orders/{oid}/status")
async def admin_order_status(oid: int, body: OrderStatusUpdate):
    async with AsyncSessionFactory() as s:
        res = await s.execute(select(Order).where(Order.id==oid))
        o = res.scalar_one_or_none()
        if not o: raise HTTPException(404,"Buyurtma topilmadi")
        o.status = body.status
        if body.status=="DELIVERED": o.delivered_at=datetime.now(timezone.utc)
        await s.commit()
    return {"ok": True}

# ── Foods ─────────────────────────────────────────

@router.post("/foods")
async def admin_create_food(body: FoodCreate):
    async with AsyncSessionFactory() as s:
        f = Food(**body.model_dump())
        s.add(f); await s.commit(); await s.refresh(f)
    return {"id": f.id, "name": f.name}

@router.put("/foods/{fid}")
async def admin_update_food(fid: int, body: FoodUpdate):
    async with AsyncSessionFactory() as s:
        res = await s.execute(select(Food).where(Food.id==fid))
        f = res.scalar_one_or_none()
        if not f: raise HTTPException(404,"Taom topilmadi")
        for k,v in body.model_dump(exclude_none=True).items():
            setattr(f,k,v)
        await s.commit()
    return {"ok": True}

@router.delete("/foods/{fid}")
async def admin_delete_food(fid: int):
    async with AsyncSessionFactory() as s:
        res = await s.execute(select(Food).where(Food.id==fid))
        f = res.scalar_one_or_none()
        if not f: raise HTTPException(404,"Taom topilmadi")
        await s.delete(f); await s.commit()
    return {"ok": True}

# ── Categories ────────────────────────────────────

@router.get("/categories")
async def admin_cats():
    async with AsyncSessionFactory() as s:
        cats = (await s.execute(select(Category))).scalars().all()
    return [{"id":c.id,"name":c.name,"is_active":c.is_active} for c in cats]

@router.post("/categories")
async def admin_create_cat(body: CategoryCreate):
    from sqlalchemy import text
    async with AsyncSessionFactory() as s:
        await s.execute(text("SELECT setval('categories_id_seq', GREATEST((SELECT COALESCE(MAX(id),0) FROM categories),1))"))
        c = Category(name=body.name); s.add(c); await s.commit(); await s.refresh(c)
    return {"id":c.id,"name":c.name}

@router.delete("/categories/{cid}")
async def admin_delete_cat(cid: int):
    async with AsyncSessionFactory() as s:
        res = await s.execute(select(Category).where(Category.id==cid))
        c = res.scalar_one_or_none()
        if not c: raise HTTPException(404,"Kategoriya topilmadi")
        await s.delete(c); await s.commit()
    return {"ok": True}

# ── Couriers ──────────────────────────────────────

@router.get("/couriers")
async def admin_couriers():
    async with AsyncSessionFactory() as s:
        rows = (await s.execute(select(Courier))).scalars().all()
    return [{"id":c.id,"name":c.name,"chat_id":c.chat_id,"channel_id":c.channel_id,"is_active":c.is_active} for c in rows]

@router.post("/couriers")
async def admin_create_courier(body: CourierCreate):
    async with AsyncSessionFactory() as s:
        c = Courier(name=body.name,chat_id=body.chat_id,channel_id=body.channel_id,is_active=True)
        s.add(c); await s.commit(); await s.refresh(c)
    return {"id":c.id,"name":c.name}

@router.patch("/couriers/{cid}/toggle")
async def admin_toggle_courier(cid: int):
    async with AsyncSessionFactory() as s:
        res = await s.execute(select(Courier).where(Courier.id==cid))
        c = res.scalar_one_or_none()
        if not c: raise HTTPException(404,"Kuryer topilmadi")
        c.is_active = not c.is_active
        val = c.is_active; await s.commit()
    return {"ok":True,"is_active":val}

@router.delete("/couriers/{cid}")
async def admin_delete_courier(cid: int):
    async with AsyncSessionFactory() as s:
        res = await s.execute(select(Courier).where(Courier.id==cid))
        c = res.scalar_one_or_none()
        if not c: raise HTTPException(404,"Kuryer topilmadi")
        await s.delete(c); await s.commit()
    return {"ok": True}

# ── Promos ────────────────────────────────────────

@router.get("/promos")
async def admin_promos():
    async with AsyncSessionFactory() as s:
        rows = (await s.execute(select(Promo).order_by(desc(Promo.id)))).scalars().all()
    return [{"id":p.id,"code":p.code,"discount_percent":p.discount_percent,
             "used_count":p.used_count,"usage_limit":p.usage_limit,"is_active":p.is_active,
             "expires_at":p.expires_at.isoformat() if p.expires_at else None} for p in rows]

@router.post("/promos")
async def admin_create_promo(body: PromoCreate):
    async with AsyncSessionFactory() as s:
        p = Promo(code=body.code.upper(),discount_percent=body.discount_percent,
                  usage_limit=body.usage_limit,expires_at=body.expires_at,is_active=True,used_count=0)
        s.add(p); await s.commit(); await s.refresh(p)
    return {"id":p.id,"code":p.code}

@router.delete("/promos/{pid}")
async def admin_delete_promo(pid: int):
    async with AsyncSessionFactory() as s:
        res = await s.execute(select(Promo).where(Promo.id==pid))
        p = res.scalar_one_or_none()
        if not p: raise HTTPException(404,"Promokod topilmadi")
        await s.delete(p); await s.commit()
    return {"ok": True}

# ── Settings ──────────────────────────────────────

@router.get("/settings")
async def admin_get_settings():
    async with AsyncSessionFactory() as s:
        shop = await get_setting(s,"shop_channel_id")
        courier = await get_setting(s,"courier_channel_id")
    return {"shop_channel_id":shop,"courier_channel_id":courier}

@router.post("/settings")
async def admin_save_setting(body: SettingUpdate):
    async with AsyncSessionFactory() as s:
        await set_setting(s,body.key,body.value)
    return {"ok": True}

# ── Database Management ──────────────────────────────────────────────────────

from app.models.user import User as UserModel
from app.models.order_item import OrderItem as OrderItemModel
from sqlalchemy import text, inspect as sa_inspect

CLEARABLE_TABLES = {
    "orders": {
        "label": "Buyurtmalar",
        "description": "Barcha buyurtmalar (order_items ham o'chadi)",
        "depends": ["order_items"],
    },
    "order_items": {
        "label": "Buyurtma elementlari",
        "description": "Barcha buyurtma qatorlari",
        "depends": [],
    },
    "users": {
        "label": "Foydalanuvchilar",
        "description": "Barcha botdan ro'yxatdan o'tgan userlar",
        "depends": ["orders", "order_items"],
    },
    "promos": {
        "label": "Promokodlar",
        "description": "Barcha promokodlar",
        "depends": [],
    },
    "couriers": {
        "label": "Kuryerlar",
        "description": "Barcha kuryerlar (buyurtmalardan bog'liq)",
        "depends": [],
    },
    "foods": {
        "label": "Taomlar",
        "description": "Barcha menu taomlar",
        "depends": ["order_items"],
    },
    "categories": {
        "label": "Kategoriyalar",
        "description": "Barcha kategoriyalar",
        "depends": ["foods", "order_items"],
    },
    "app_settings": {
        "label": "Sozlamalar",
        "description": "Ilova sozlamalari (kanal IDlar va h.k.)",
        "depends": [],
    },
}


@router.get("/db/tables")
async def admin_db_tables():
    """Jadvallar haqida ma'lumot (qator soni bilan)"""
    async with AsyncSessionFactory() as s:
        result = []
        for table_name, info in CLEARABLE_TABLES.items():
            try:
                cnt = (await s.execute(text(f"SELECT COUNT(*) FROM {table_name}"))).scalar() or 0
            except Exception:
                cnt = -1
            result.append({
                "table": table_name,
                "label": info["label"],
                "description": info["description"],
                "row_count": cnt,
                "depends": info["depends"],
            })
        return result


class ClearTableRequest(BaseModel):
    table: str
    cascade: bool = True


@router.post("/db/clear")
async def admin_clear_table(body: ClearTableRequest):
    """Tanlangan jadvalni tozalash"""
    if body.table not in CLEARABLE_TABLES:
        raise HTTPException(400, f"'{body.table}' jadvali ruxsat etilmagan")

    async with AsyncSessionFactory() as s:
        try:
            if body.cascade:
                # Avval bog'liq jadvallarni tozalaymiz
                for dep in CLEARABLE_TABLES[body.table]["depends"]:
                    await s.execute(text(f"DELETE FROM {dep}"))
            await s.execute(text(f"DELETE FROM {body.table}"))
            await s.commit()
            # Qator sonini qaytaramiz
            remaining = (await s.execute(text(f"SELECT COUNT(*) FROM {body.table}"))).scalar() or 0
        except Exception as e:
            await s.rollback()
            raise HTTPException(500, f"Tozalashda xatolik: {str(e)}")

    return {"ok": True, "table": body.table, "remaining_rows": remaining}


@router.get("/db/stats")
async def admin_db_stats():
    """Barcha jadvallarning umumiy statistikasi"""
    async with AsyncSessionFactory() as s:
        stats = {}
        for table_name in CLEARABLE_TABLES:
            try:
                cnt = (await s.execute(text(f"SELECT COUNT(*) FROM {table_name}"))).scalar() or 0
                stats[table_name] = cnt
            except Exception:
                stats[table_name] = -1
        return stats
