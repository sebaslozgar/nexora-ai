"""Reglas iniciales de los asistentes Salvaje VIP.

Módulo puro: no llama a Shopify, no publica ni modifica precios.
Las autorizaciones deben comprobarse de nuevo en el servidor al ejecutar.
"""
from dataclasses import dataclass

ASSISTANTS = {
    "ventas": ("consultar_catalogo", "responder_consultas", "proponer_enlace"),
    "productos": ("preparar_ficha", "proponer_precio"),
    "marketing": ("preparar_publicacion", "proponer_campana"),
    "proveedores": ("consultar_stock", "consultar_coste", "alertar_margen"),
}
REQUIRES_CORAL_APPROVAL = frozenset({
    "publicar_producto", "cambiar_precio", "publicar_contenido",
    "activar_descuento", "contratar_servicio", "gastar_dinero",
})
FORBIDDEN_AUTOMATIC = frozenset({"inventar_stock", "inventar_precio", "inventar_descuento"})


@dataclass(frozen=True)
class Proposal:
    business_id: str
    assistant: str
    action: str
    payload: dict


def validate_proposal(proposal: Proposal, *, verified_stock=False, verified_price=False):
    """Devuelve estado y motivo; nunca ejecuta una acción."""
    if not proposal.business_id or proposal.assistant not in ASSISTANTS:
        return "rejected", "Empresa o asistente no válido"
    if proposal.action in FORBIDDEN_AUTOMATIC:
        return "rejected", "Prohibido inventar datos comerciales"
    if proposal.action in REQUIRES_CORAL_APPROVAL:
        return "pending_approval", "Requiere aprobación explícita de Coral"
    if proposal.action not in ASSISTANTS[proposal.assistant]:
        return "rejected", "Acción fuera del ámbito del asistente"
    if proposal.action == "proponer_enlace" and not verified_stock:
        return "blocked", "Comprobar existencias antes de ofrecer compra"
    if proposal.action == "proponer_precio" and not verified_price:
        return "blocked", "Comprobar coste, impuestos y envío"
    return "proposal_only", "Propuesta permitida; ninguna acción ejecutada"
