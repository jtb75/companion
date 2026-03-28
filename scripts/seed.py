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
    AccessTier,
    ConfigCategory,
    DocumentStatus,
    MemoryCategory,
    MemorySource,
    PaymentStatus,
    RelationshipType,
    SourceChannel,
    TodoCategory,
    TodoSource,
)
from app.models.user import User
from app.models.medication import Medication
from app.models.appointment import Appointment
from app.models.bill import Bill
from app.models.todo import Todo
from app.models.functional_memory import FunctionalMemory
from app.models.document import Document
from app.models.trusted_contact import TrustedContact
from app.models.system_config import SystemConfig


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

        # ── Trusted contact ───────────────────────────────────────
        session.add(TrustedContact(
            user_id=sam.id,
            contact_name="Maria Johnson",
            contact_phone="555-0101",
            contact_email="maria@example.com",
            relationship_type=RelationshipType.FAMILY,
            access_tier=AccessTier.TIER_1,
        ))

        # ── System config (Arlo persona prompt) ───────────────────
        session.add(SystemConfig(
            category=ConfigCategory.ARLO_PERSONA,
            key="default_system_prompt",
            value={
                "prompt": (
                    "You are Arlo, a calm and supportive companion. "
                    "You help the user manage their daily life — bills, "
                    "medications, appointments, and mail. Speak simply "
                    "and warmly. Never rush. If the user seems confused, "
                    "gently re-explain. Always confirm before taking "
                    "action on their behalf."
                ),
                "version": "1.0",
            },
            description="Default Arlo persona system prompt",
            is_active=True,
            updated_by="seed_script",
        ))

        await session.flush()

        # ── Documents for pipeline processing ─────────────────────
        # These documents simulate incoming mail that the pipeline
        # will classify, extract, summarize, route, and track.

        electric_bill_doc = Document(
            user_id=sam.id,
            source_channel=SourceChannel.CAMERA_SCAN,
            raw_text_ref="seed:electric_bill",
            status=DocumentStatus.RECEIVED,
            source_metadata={
                "raw_text": (
                    "RIVERSIDE POWER & LIGHT\n"
                    "Account Number: ****4821\n"
                    "Statement Date: 03/15/2026\n\n"
                    "Amount Due: $87.43\n"
                    "Due Date: April 5, 2026\n\n"
                    "Usage this period: 612 kWh\n"
                    "Previous balance: $0.00\n"
                    "Current charges: $87.43\n\n"
                    "Pay online at riversidepower.com or mail check to:\n"
                    "Riverside Power & Light, PO Box 9100, Riverside CA 92502\n\n"
                    "PLEASE PAY BY APRIL 5 TO AVOID LATE FEE."
                ),
            },
        )

        medical_letter_doc = Document(
            user_id=sam.id,
            source_channel=SourceChannel.EMAIL,
            raw_text_ref="seed:medical_letter",
            status=DocumentStatus.RECEIVED,
            source_metadata={
                "raw_text": (
                    "Dear Sam Johnson,\n\n"
                    "This letter confirms your appointment with "
                    "Dr. Rebecca Torres at Valley Health Center.\n\n"
                    "Date: April 10, 2026\n"
                    "Time: 2:30 PM\n"
                    "Location: 456 Oak Avenue, Suite 200\n\n"
                    "Please arrive 15 minutes early to complete "
                    "intake paperwork. Bring your insurance card "
                    "and a list of current medications.\n\n"
                    "If you need to reschedule, call 555-0199 at "
                    "least 24 hours in advance.\n\n"
                    "Sincerely,\n"
                    "Valley Health Center Scheduling Team"
                ),
            },
        )

        legal_notice_doc = Document(
            user_id=sam.id,
            source_channel=SourceChannel.MAIL_STATION,
            raw_text_ref="seed:legal_notice",
            status=DocumentStatus.RECEIVED,
            source_metadata={
                "raw_text": (
                    "NOTICE OF DEBT — IMPORTANT\n\n"
                    "RE: Account #COL-29481\n"
                    "Original Creditor: City Medical Group\n"
                    "Balance Due: $342.00\n\n"
                    "Dear Sam Johnson,\n\n"
                    "Our records indicate an outstanding balance "
                    "of $342.00 for services rendered on 11/02/2025. "
                    "This amount is now 120 days past due.\n\n"
                    "You have 30 days from receipt of this notice "
                    "to dispute this debt in writing. If you do not "
                    "dispute this debt within 30 days, it will be "
                    "assumed valid.\n\n"
                    "To arrange payment or dispute this debt, "
                    "contact us at 1-800-555-0177 or write to:\n"
                    "National Collections Agency\n"
                    "PO Box 5500, Dallas TX 75201\n\n"
                    "Response deadline: April 20, 2026"
                ),
            },
        )

        junk_mail_doc = Document(
            user_id=sam.id,
            source_channel=SourceChannel.CAMERA_SCAN,
            raw_text_ref="seed:junk_mail",
            status=DocumentStatus.RECEIVED,
            source_metadata={
                "raw_text": (
                    "CONGRATULATIONS! You've been selected!\n\n"
                    "Dear Valued Customer,\n\n"
                    "Act NOW and receive a FREE vacation package "
                    "worth $5,000! This exclusive offer is available "
                    "for a LIMITED TIME ONLY.\n\n"
                    "Call 1-800-555-0000 in the next 48 hours to "
                    "claim your prize! No purchase necessary.\n\n"
                    "This offer includes:\n"
                    "- 3 nights at a luxury resort\n"
                    "- Round-trip airfare for 2\n"
                    "- $500 spending money\n\n"
                    "Don't miss out! Operators are standing by!\n"
                    "Visit www.totally-real-vacations.com"
                ),
            },
        )

        session.add_all([
            electric_bill_doc,
            medical_letter_doc,
            legal_notice_doc,
            junk_mail_doc,
        ])
        await session.flush()

        # Run each document through the full pipeline
        from app.pipeline.orchestrator import process_document

        doc_labels = [
            (electric_bill_doc, "electric bill"),
            (medical_letter_doc, "medical appointment letter"),
            (legal_notice_doc, "legal/collections notice"),
            (junk_mail_doc, "junk mail"),
        ]

        for doc, label in doc_labels:
            try:
                result = await process_document(session, doc.id, sam.id)
                print(
                    f"  Pipeline: {label} -> "
                    f"{result.classification.classification} "
                    f"(conf={result.classification.confidence_score:.2f}, "
                    f"route={result.routing.routing_destination}, "
                    f"time={result.processing_time_ms}ms)"
                )
            except Exception as e:
                print(f"  Pipeline: {label} -> FAILED ({e})")

        await session.commit()
        print(f"\nSeeded user: {sam.preferred_name} (id: {sam.id})")
        print("  2 medications, 1 appointment, 3 bills, 2 todos, 2 memories")
        print("  1 trusted contact (Maria, family, Tier 1)")
        print("  1 system config (Arlo persona prompt)")
        print("  4 documents processed through pipeline")


async def main():
    try:
        await seed()
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
