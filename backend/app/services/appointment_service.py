from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.appointment import Appointment


async def list_appointments(
    db: AsyncSession, user_id: UUID
) -> list[Appointment]:
    result = await db.execute(
        select(Appointment)
        .where(Appointment.user_id == user_id)
        .order_by(Appointment.appointment_at)
    )
    return list(result.scalars().all())


async def get_appointment(
    db: AsyncSession, user_id: UUID, appointment_id: UUID
) -> Appointment | None:
    result = await db.execute(
        select(Appointment).where(
            Appointment.id == appointment_id,
            Appointment.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


async def create_appointment(
    db: AsyncSession, user_id: UUID, data: dict
) -> Appointment:
    appointment = Appointment(user_id=user_id, **data)
    db.add(appointment)
    await db.flush()
    return appointment


async def update_appointment(
    db: AsyncSession, user_id: UUID, appointment_id: UUID, data: dict
) -> Appointment | None:
    appointment = await get_appointment(db, user_id, appointment_id)
    if appointment is None:
        return None
    for key, value in data.items():
        setattr(appointment, key, value)
    await db.flush()
    return appointment


async def delete_appointment(
    db: AsyncSession, user_id: UUID, appointment_id: UUID
) -> bool:
    appointment = await get_appointment(db, user_id, appointment_id)
    if appointment is None:
        return False
    await db.delete(appointment)
    await db.flush()
    return True
