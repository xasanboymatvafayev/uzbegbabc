from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.courier import Courier
from typing import List, Optional


async def get_active_couriers(session: AsyncSession) -> List[Courier]:
    result = await session.execute(select(Courier).where(Courier.is_active == True))
    return result.scalars().all()


async def get_courier_by_id(session: AsyncSession, courier_id: int) -> Optional[Courier]:
    result = await session.execute(select(Courier).where(Courier.id == courier_id))
    return result.scalar_one_or_none()


async def get_courier_by_chat_id(session: AsyncSession, chat_id: int) -> Optional[Courier]:
    result = await session.execute(select(Courier).where(Courier.chat_id == chat_id))
    return result.scalar_one_or_none()


async def add_courier(session: AsyncSession, chat_id: int, channel_id: int, name: str) -> Courier:
    courier = Courier(chat_id=chat_id, channel_id=channel_id, name=name)
    session.add(courier)
    await session.commit()
    await session.refresh(courier)
    return courier


async def disable_courier(session: AsyncSession, courier_id: int) -> bool:
    courier = await get_courier_by_id(session, courier_id)
    if not courier:
        return False
    courier.is_active = False
    await session.commit()
    return True


async def remove_courier(session: AsyncSession, courier_id: int) -> bool:
    courier = await get_courier_by_id(session, courier_id)
    if not courier:
        return False
    await session.delete(courier)
    await session.commit()
    return True


async def get_all_couriers(session: AsyncSession) -> List[Courier]:
    result = await session.execute(select(Courier).order_by(Courier.created_at.desc()))
    return result.scalars().all()
