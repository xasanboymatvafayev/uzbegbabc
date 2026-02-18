from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from app.models.food import Food
from app.models.category import Category
from typing import List, Optional


async def get_all_categories(session: AsyncSession) -> List[Category]:
    result = await session.execute(select(Category).where(Category.is_active == True))
    return result.scalars().all()


async def get_foods_by_category(session: AsyncSession, category_id: Optional[int] = None) -> List[Food]:
    query = select(Food).where(Food.is_active == True)
    if category_id:
        query = query.where(Food.category_id == category_id)
    result = await session.execute(query)
    return result.scalars().all()


async def get_food_by_id(session: AsyncSession, food_id: int) -> Optional[Food]:
    result = await session.execute(select(Food).where(Food.id == food_id))
    return result.scalar_one_or_none()


async def create_food(session: AsyncSession, **kwargs) -> Food:
    food = Food(**kwargs)
    session.add(food)
    await session.commit()
    await session.refresh(food)
    return food


async def update_food(session: AsyncSession, food_id: int, **kwargs) -> Optional[Food]:
    food = await get_food_by_id(session, food_id)
    if not food:
        return None
    for k, v in kwargs.items():
        setattr(food, k, v)
    await session.commit()
    await session.refresh(food)
    return food


async def delete_food(session: AsyncSession, food_id: int) -> bool:
    food = await get_food_by_id(session, food_id)
    if not food:
        return False
    await session.delete(food)
    await session.commit()
    return True


async def create_category(session: AsyncSession, name: str) -> Category:
    # Fix sequence before insert to avoid duplicate key errors
    await session.execute(
        text("SELECT setval('categories_id_seq', (SELECT COALESCE(MAX(id), 0) FROM categories))")
    )
    cat = Category(name=name)
    session.add(cat)
    await session.commit()
    await session.refresh(cat)
    return cat


async def delete_category(session: AsyncSession, cat_id: int) -> bool:
    result = await session.execute(select(Category).where(Category.id == cat_id))
    cat = result.scalar_one_or_none()
    if not cat:
        return False
    await session.delete(cat)
    await session.commit()
    return True
