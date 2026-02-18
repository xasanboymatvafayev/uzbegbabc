from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.setting import AppSetting
from app.config import settings


async def get_setting(session: AsyncSession, key: str) -> str | None:
    result = await session.execute(select(AppSetting).where(AppSetting.key == key))
    row = result.scalar_one_or_none()
    return row.value if row else None


async def set_setting(session: AsyncSession, key: str, value: str):
    result = await session.execute(select(AppSetting).where(AppSetting.key == key))
    row = result.scalar_one_or_none()
    if row:
        row.value = value
    else:
        row = AppSetting(key=key, value=value)
        session.add(row)
    await session.commit()


async def get_shop_channel_id(session: AsyncSession) -> int:
    val = await get_setting(session, "shop_channel_id")
    if val:
        return int(val)
    return settings.SHOP_CHANNEL_ID


async def get_courier_channel_id(session: AsyncSession) -> int:
    val = await get_setting(session, "courier_channel_id")
    if val:
        return int(val)
    return settings.COURIER_CHANNEL_ID
