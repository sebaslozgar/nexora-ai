"""Respuestas de ventas fundamentadas en catálogo Shopify verificado.

Este módulo no llama a Shopify ni escribe en la tienda. Recibe el resultado
normalizado de shopify_catalog.normalise_products y devuelve texto.
"""
from decimal import Decimal, InvalidOperation


def _money(value):
    if value is None:
        return None
    try:
        return f"{Decimal(str(value)):.2f}".replace(".", ",") + " €"
    except (InvalidOperation, ValueError):
        return None


def _variant_label(variant):
    title = variant.get("title")
    return "" if not title or title == "Default Title" else f" ({title})"


def _available(variant):
    # available_for_sale es la señal de Shopify; inventario por sí solo
    # no demuestra disponibilidad comercial.
    return variant.get("available_for_sale") is True


def catalog_summary(catalog):
    """Lista productos activos y variantes, sin afirmar stock no confirmado."""
    lines = []
    for product in catalog.get("products", []):
        if product.get("status") != "ACTIVE":
            continue
        lines.append(product.get("title") or "Producto sin título")
        for variant in product.get("variants", []):
            price = _money(variant.get("price")) or "precio sin confirmar"
            quantity = variant.get("inventory_quantity")
            availability = (
                "disponible" if _available(variant)
                else "disponibilidad no confirmada"
            )
            stock = f", {quantity} unidades registradas" if isinstance(quantity, int) else ""
            lines.append(f"  {_variant_label(variant).strip() or 'Variante estándar'}: {price}, {availability}{stock}")
    return "\n".join(lines) if lines else "No hay productos activos confirmados en el catálogo consultado."


def answer_customer(message, catalog):
    """Responde sin inventar productos, precios, tallas ni políticas."""
    q = (message or "").casefold().strip()
    if not q:
        return "¡Hola! 💖 ¿En qué puedo ayudarte con Salvaje VIP?"
    products = [
        p for p in catalog.get("products", [])
        if p.get("status") == "ACTIVE" and (p.get("title") or "").casefold() in q
    ]
    if products:
        return "¡Claro! 💖 Esto es lo que figura en nuestro catálogo:\n" + catalog_summary({"products": products})
    if any(w in q for w in ("precio", "cuánto", "cuanto", "stock", "talla", "disponib", "tenéis", "teneis", "producto", "catálogo", "catalogo")):
        return "¡Te cuento lo que tenemos confirmado! 💖\n" + catalog_summary(catalog)
    if any(w in q for w in ("envío", "envio", "devolución", "devolucion", "cambio", "pago")):
        return "Para darte las condiciones correctas, te las tiene que confirmar el equipo de Salvaje VIP. 💖"
    return "¡Hola! 💖 Cuéntame qué prenda buscas y te ayudo con la información que tenemos confirmada en el catálogo."
