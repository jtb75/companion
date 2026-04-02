"""Pipeline event publisher — writes stage updates to Firestore."""

import asyncio
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def _get_firestore():
    """Get Firestore client, initializing Firebase if needed."""
    try:
        from app.auth.firebase import _ensure_initialized
        _ensure_initialized()
        from firebase_admin import firestore
        return firestore.client()
    except Exception:
        logger.warning("Firestore client unavailable", exc_info=True)
        return None


async def publish_pipeline_event(
    document_id: str,
    stage: str,
    status: str,
    metadata: dict | None = None,
) -> None:
    """Write pipeline stage status to Firestore.

    Updates a single document at pipeline_events/{document_id}
    with the current state of all stages. The frontend listens
    via onSnapshot for real-time updates.
    """
    doc_id = str(document_id)

    try:
        db = _get_firestore()
        if db is None:
            return

        update = {
            stage: status,
            "updated_at": datetime.utcnow().isoformat(),
        }
        if metadata:
            update[f"{stage}_metadata"] = metadata

        # Run synchronous Firestore write in thread
        await asyncio.to_thread(
            db.collection("pipeline_events")
            .document(doc_id)
            .set,
            update,
            merge=True,
        )
    except Exception:
        logger.warning(
            "Failed to write pipeline event to Firestore"
            " for doc %s",
            document_id,
            exc_info=True,
        )
