"""Seed the development database with a sample user 'Sam' and related data."""
import asyncio
import sys
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.db.session import async_session_factory, engine
from app.models.enums import (
    MemoryCategory,
    MemorySource,
    PaymentStatus,
    TodoCategory,
    TodoSource,
)
from app.models.user import User
from app.models.medication import Medication
from app.models.appointment import Appointment
from app.models.bill import Bill
from app.models.todo import Todo
from app.models.functional_memory import FunctionalMemory


async def seed():
    async with async_session_factory() as session:
        # Check if already seeded
        from sqlalchemy import select
        result = await session.execute(select(User).limit(1))
        if result.scalar_one_or_none():
            print("Database already seeded. Skipping.")
            return

        # Create Sam
        sam = User(
            email="sam@example.com",
            phone="555-0100",
            preferred_name="Sam",
            display_name="Sam Johnson",
            date_of_birth=date(1998, 3, 15),
            primary_language="en",
            voice_id="warm",
            pace_setting="normal",
            warmth_level="warm",
            nickname="Sam",
            quiet_start=time(21, 0),
            quiet_end=time(8, 0),
            checkin_time=time(9, 0),
        )
        session.add(sam)
        await session.flush()

        # Medications
        session.add_all([
            Medication(
                user_id=sam.id,
                name="Metformin",
                dosage="500mg",
                frequency="twice daily",
                schedule=["08:00", "20:00"],
                pharmacy="CVS Pharmacy",
                prescriber="Dr. Patel",
                refill_due_at=date.today() + timedelta(days=8),
            ),
            Medication(
                user_id=sam.id,
                name="Lisinopril",
                dosage="10mg",
                frequency="once daily",
                schedule=["08:00"],
                prescriber="Dr. Patel",
            ),
        ])

        # Appointments
        session.add(Appointment(
            user_id=sam.id,
            provider_name="Dr. Johnson",
            location={"name": "Primary Care Clinic", "address": "123 Main St"},
            appointment_at=datetime.combine(
                date.today() + timedelta(days=3),
                time(14, 0),
            ),
            preparation_notes="Bring insurance card",
        ))

        # Bills
        session.add_all([
            Bill(
                user_id=sam.id,
                sender="Electric Company",
                description="Monthly electric bill",
                amount=Decimal("74.00"),
                due_date=date.today() + timedelta(days=11),
            ),
            Bill(
                user_id=sam.id,
                sender="Landlord",
                description="Monthly rent",
                amount=Decimal("850.00"),
                due_date=date.today() + timedelta(days=18),
            ),
            Bill(
                user_id=sam.id,
                sender="Phone Company",
                description="Phone bill",
                amount=Decimal("45.00"),
                due_date=date.today() - timedelta(days=2),
                payment_status=PaymentStatus.PAID,
            ),
        ])

        # Todos
        session.add_all([
            Todo(
                user_id=sam.id,
                title="Call the pharmacy",
                category=TodoCategory.ERRAND,
                source=TodoSource.USER,
            ),
            Todo(
                user_id=sam.id,
                title="Grocery trip",
                description="Paper towels, milk, bread",
                category=TodoCategory.SHOPPING,
                source=TodoSource.USER,
                due_date=date.today() + timedelta(days=2),
            ),
        ])

        # Functional memories
        session.add_all([
            FunctionalMemory(
                user_id=sam.id,
                category=MemoryCategory.PROVIDER,
                key="primary_care_doctor",
                value={"name": "Dr. Johnson", "phone": "555-0142"},
                source=MemorySource.ONBOARDING,
            ),
            FunctionalMemory(
                user_id=sam.id,
                category=MemoryCategory.PREFERENCE,
                key="preferred_grocery_store",
                value={"name": "Safeway", "location": "Main St"},
                source=MemorySource.USER_INPUT,
            ),
        ])

        await session.commit()
        print(f"Seeded user: {sam.preferred_name} (id: {sam.id})")
        print("  2 medications, 1 appointment, 3 bills, 2 todos, 2 memories")


async def main():
    try:
        await seed()
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
