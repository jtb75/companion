from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document


async def list_documents(
    db: AsyncSession,
    user_id: UUID,
    status: str | None = None,
    classification: str | None = None,
    urgency: str | None = None,
) -> list[Document]:
    stmt = select(Document).where(Document.user_id == user_id)
    if status is not None:
        stmt = stmt.where(Document.status == status)
    if classification is not None:
        stmt = stmt.where(Document.classification == classification)
    if urgency is not None:
        stmt = stmt.where(Document.urgency_level == urgency)
    stmt = stmt.order_by(Document.received_at.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_document(
    db: AsyncSession, user_id: UUID, document_id: UUID
) -> Document | None:
    result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


async def update_document_status(
    db: AsyncSession, user_id: UUID, document_id: UUID, status: str
) -> Document | None:
    document = await get_document(db, user_id, document_id)
    if document is None:
        return None
    document.status = status
    await db.flush()
    return document


async def delete_document(
    db: AsyncSession, user_id: UUID, document_id: UUID
) -> bool:
    document = await get_document(db, user_id, document_id)
    if document is None:
        return False
    await db.delete(document)
    await db.flush()
    return True


async def create_document(
    db: AsyncSession, user_id: UUID, data: dict
) -> Document:
    document = Document(user_id=user_id, **data)
    db.add(document)
    await db.flush()
    return document
