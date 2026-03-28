from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.functional_memory import FunctionalMemory


async def list_memories(
    db: AsyncSession, user_id: UUID
) -> list[FunctionalMemory]:
    result = await db.execute(
        select(FunctionalMemory)
        .where(FunctionalMemory.user_id == user_id)
        .order_by(FunctionalMemory.category, FunctionalMemory.key)
    )
    return list(result.scalars().all())


async def delete_memory(
    db: AsyncSession, user_id: UUID, memory_id: UUID
) -> bool:
    result = await db.execute(
        select(FunctionalMemory).where(
            FunctionalMemory.id == memory_id,
            FunctionalMemory.user_id == user_id,
        )
    )
    memory = result.scalar_one_or_none()
    if memory is None:
        return False
    await db.delete(memory)
    await db.flush()
    return True


async def delete_all_memories(db: AsyncSession, user_id: UUID) -> int:
    # Get count first
    count_result = await db.execute(
        select(func.count())
        .select_from(FunctionalMemory)
        .where(FunctionalMemory.user_id == user_id)
    )
    count = count_result.scalar_one()

    await db.execute(
        delete(FunctionalMemory).where(FunctionalMemory.user_id == user_id)
    )
    await db.flush()
    return count
