"""Política de autorización para la futura API NEXORA.

No autentica tokens ni concede acceso por sí sola. La identidad debe estar
verificada por el servidor antes de llamar a estas funciones.
"""
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Actor:
    user_id: str
    business_id: str
    role: str


# Denegación por defecto. No se confía en roles enviados por el navegador.
PERMISSIONS = {
    "owner": frozenset({
        "conversations.read", "conversations.reply", "conversations.assign",
        "conversations.handoff", "alerts.read", "business.settings",
        "members.manage",
    }),
    "manager": frozenset({
        "conversations.read", "conversations.reply", "conversations.assign",
        "conversations.handoff", "alerts.read",
    }),
    "employee": frozenset({
        "conversations.read", "conversations.reply",
        "conversations.handoff",
    }),
}


def resolve_actor(db, *, auth_subject: str, business_id: str) -> Optional[Actor]:
    """Busca membresía real en BD; no acepta role ni user_id del cliente."""
    if not auth_subject or not business_id:
        return None
    row = db.execute(
        """SELECT u.id, m.role FROM users AS u
           JOIN business_memberships AS m ON m.user_id = u.id
           WHERE u.auth_subject = ? AND m.business_id = ?""",
        (auth_subject, business_id),
    ).fetchone()
    return Actor(row[0], business_id, row[1]) if row else None


def allowed(actor: Optional[Actor], action: str, *,
            resource_business_id: str,
            assigned_user_id: Optional[str] = None) -> bool:
    if actor is None or actor.business_id != resource_business_id:
        return False
    if action not in PERMISSIONS.get(actor.role, ()):
        return False
    if actor.role == "employee" and action.startswith("conversations."):
        return assigned_user_id == actor.user_id
    return True


def list_visible_conversations(db, actor: Actor):
    """Consulta siempre filtrada por negocio y, para empleados, asignación."""
    if not allowed(actor, "conversations.read",
                   resource_business_id=actor.business_id,
                   assigned_user_id=actor.user_id):
        return []
    if actor.role == "employee":
        return db.execute(
            """SELECT id, status, assigned_user_id FROM conversations
               WHERE business_id=? AND assigned_user_id=?
               ORDER BY updated_at DESC""",
            (actor.business_id, actor.user_id),
        ).fetchall()
    return db.execute(
        """SELECT id, status, assigned_user_id FROM conversations
           WHERE business_id=? ORDER BY updated_at DESC""",
        (actor.business_id,),
    ).fetchall()
