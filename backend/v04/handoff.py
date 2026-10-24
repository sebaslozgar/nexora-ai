"""Transición a atención humana; solo datos locales de SQLite/D1.

El servidor debe verificar la identidad y resolver Actor antes de llamar.
No envía mensajes, notificaciones ni activa servicios externos.
"""
from permissions import allowed


def handoff_to_human(db, actor, conversation_id: str) -> bool:
    """Solicita atención humana sin sobrescribir conversaciones cerradas."""
    if not conversation_id or actor is None:
        return False
    row = db.execute(
        """SELECT business_id, status, assigned_user_id FROM conversations
           WHERE business_id=? AND id=?""",
        (actor.business_id, conversation_id),
    ).fetchone()
    if row is None or row[1] == "closed":
        return False
    if not allowed(actor, "conversations.handoff",
                   resource_business_id=row[0], assigned_user_id=row[2]):
        return False
    result = db.execute(
        """UPDATE conversations SET status='needs_human',
           updated_at=CURRENT_TIMESTAMP
           WHERE business_id=? AND id=? AND status='ai'""",
        (actor.business_id, conversation_id),
    )
    return result.rowcount == 1


def accept_handoff(db, actor, conversation_id: str) -> bool:
    """Un miembro autorizado toma una conversación pendiente de atención."""
    if actor is None or not conversation_id:
        return False
    row = db.execute(
        """SELECT assigned_user_id FROM conversations
           WHERE business_id=? AND id=? AND status='needs_human'""",
        (actor.business_id, conversation_id),
    ).fetchone()
    if row is None:
        return False
    if not allowed(actor, "conversations.handoff",
                   resource_business_id=actor.business_id,
                   assigned_user_id=row[0]):
        return False
    result = db.execute(
        """UPDATE conversations SET status='human',
           updated_at=CURRENT_TIMESTAMP
           WHERE business_id=? AND id=? AND status='needs_human'""",
        (actor.business_id, conversation_id),
    )
    return result.rowcount == 1


def ai_can_reply(db, business_id: str, conversation_id: str) -> bool:
    """Consulta defensiva; no sustituye el bloqueo transaccional al enviar."""
    row = db.execute(
        """SELECT c.status, b.ai_enabled FROM conversations AS c
           JOIN businesses AS b ON b.id=c.business_id
           WHERE c.business_id=? AND c.id=?""",
        (business_id, conversation_id),
    ).fetchone()
    return bool(row and row[0] == "ai" and row[1] == 1)
