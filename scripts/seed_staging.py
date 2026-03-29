"""Seed staging database with test users and data."""
import asyncio
import os
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy import pool


DATABASE_URL = os.environ.get(
    "COMPANION_DATABASE_URL",
    "postgresql+asyncpg://companion:companion_dev@localhost:5432/companion",
)


async def seed():
    engine = create_async_engine(DATABASE_URL, poolclass=pool.NullPool)
    factory = async_sessionmaker(engine, expire_on_commit=False)

    # Import models
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
    from app.models.user import User
    from app.models.trusted_contact import TrustedContact
    from app.models.medication import Medication
    from app.models.bill import Bill
    from app.models.appointment import Appointment
    from app.models.todo import Todo
    from app.models.enums import (
        AccessTier,
        PaymentStatus,
        RelationshipType,
        TodoCategory,
        TodoSource,
    )

    async with factory() as db:
        result = await db.execute(
            select(User).where(User.email == "jtb75.dev@gmail.com")
        )
        if result.scalar_one_or_none():
            print("Already seeded.")
            await engine.dispose()
            return

        # Users
        sam = User(
            email="jtb75.prod@gmail.com",
            preferred_name="Sam",
            display_name="Sam",
            primary_language="en",
            voice_id="warm",
            pace_setting="normal",
            warmth_level="warm",
        )
        alex = User(
            email="jtb75.dev@gmail.com",
            preferred_name="Alex",
            display_name="Alex",
            primary_language="en",
            voice_id="calm",
            pace_setting="normal",
            warmth_level="warm",
            quiet_start=time(21, 0),
            quiet_end=time(8, 0),
            checkin_time=time(9, 0),
        )
        db.add_all([sam, alex])
        await db.flush()

        # Trusted contacts for Alex
        db.add_all([
            TrustedContact(
                user_id=alex.id,
                contact_name="Joe",
                contact_email="joe.buhr@gmail.com",
                relationship_type=RelationshipType.CASE_WORKER,
                access_tier=AccessTier.TIER_2,
            ),
            TrustedContact(
                user_id=alex.id,
                contact_name="Sam",
                contact_email="jtb75.prod@gmail.com",
                relationship_type=RelationshipType.FAMILY,
                access_tier=AccessTier.TIER_2,
            ),
        ])

        # Alex's medications
        db.add_all([
            Medication(
                user_id=alex.id,
                name="Metformin",
                dosage="500mg",
                frequency="twice daily",
                schedule=["08:00", "20:00"],
                pharmacy="CVS Pharmacy",
                prescriber="Dr. Patel",
                refill_due_at=date.today() + timedelta(days=8),
            ),
            Medication(
                user_id=alex.id,
                name="Lisinopril",
                dosage="10mg",
                frequency="once daily",
                schedule=["08:00"],
                prescriber="Dr. Patel",
            ),
        ])

        # Alex's bills
        db.add_all([
            Bill(
                user_id=alex.id,
                sender="Electric Company",
                description="Monthly electric bill",
                amount=Decimal("74.00"),
                due_date=date.today() + timedelta(days=11),
            ),
            Bill(
                user_id=alex.id,
                sender="Landlord",
                description="Monthly rent",
                amount=Decimal("850.00"),
                due_date=date.today() + timedelta(days=18),
            ),
            Bill(
                user_id=alex.id,
                sender="Phone Company",
                description="Phone bill",
                amount=Decimal("45.00"),
                due_date=date.today() - timedelta(days=2),
                payment_status=PaymentStatus.PAID,
            ),
        ])

        # Alex's appointment
        db.add(Appointment(
            user_id=alex.id,
            provider_name="Dr. Johnson",
            location={"name": "Primary Care", "address": "123 Main St"},
            appointment_at=datetime.combine(
                date.today() + timedelta(days=3), time(14, 0),
            ),
            preparation_notes="Bring insurance card",
        ))

        # Alex's todos
        db.add_all([
            Todo(
                user_id=alex.id,
                title="Call the pharmacy",
                category=TodoCategory.ERRAND,
                source=TodoSource.USER,
            ),
            Todo(
                user_id=alex.id,
                title="Grocery trip",
                description="Paper towels, milk, bread",
                category=TodoCategory.SHOPPING,
                source=TodoSource.USER,
            ),
        ])

        await db.commit()
        print(f"Seeded Sam ({sam.id}) and Alex ({alex.id})")
        print("Alex: 2 meds, 3 bills, 1 appt, 2 todos")
        print("Caregivers: joe.buhr@gmail.com, jtb75.prod@gmail.com")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
