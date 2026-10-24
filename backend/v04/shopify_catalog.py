"""Lectura segura de productos Shopify para Salvaje VIP.

Solo construye consultas GraphQL y normaliza resultados. El transporte HTTP y
la autenticación deben implementarse en el servidor, nunca en el navegador.
No contiene claves, no escribe en Shopify y no ejecuta acciones externas.
"""

PRODUCTS_QUERY = """
query SalvajeVipProducts($first: Int!, $after: String) {
  products(first: $first, after: $after) {
    pageInfo { hasNextPage endCursor }
    edges {
      node {
        id title handle status
        onlineStoreUrl
        variants(first: 100) {
          edges {
            node {
              id title price
              inventoryQuantity
              inventoryPolicy
              availableForSale
            }
          }
        }
      }
    }
  }
}
"""


def query_variables(first=25, after=None):
    if not isinstance(first, int) or isinstance(first, bool) or not 1 <= first <= 100:
        raise ValueError("first debe estar entre 1 y 100")
    if after is not None and not isinstance(after, str):
        raise ValueError("Cursor inválido")
    return {"first": first, "after": after}


def normalise_products(response):
    """Extrae datos verificados; no infiere stock ausente ni inventa precios."""
    if response.get("errors"):
        raise ValueError("Shopify devolvió errores")
    products = response.get("data", {}).get("products")
    if not isinstance(products, dict):
        raise ValueError("Respuesta de Shopify incompleta")
    result = []
    for edge in products.get("edges", []):
        item = edge["node"]
        variants = []
        for variant_edge in item.get("variants", {}).get("edges", []):
            v = variant_edge["node"]
            variants.append({
                "id": v["id"],
                "title": v["title"],
                "price": v.get("price"),
                "inventory_quantity": v.get("inventoryQuantity"),
                "inventory_policy": v.get("inventoryPolicy"),
                "available_for_sale": v.get("availableForSale"),
            })
        result.append({
            "id": item["id"],
            "title": item["title"],
            "handle": item.get("handle"),
            "status": item.get("status"),
            "url": item.get("onlineStoreUrl"),
            "variants": variants,
        })
    return {
        "products": result,
        "has_next_page": products.get("pageInfo", {}).get("hasNextPage", False),
        "end_cursor": products.get("pageInfo", {}).get("endCursor"),
    }
