"""Conector Shopify de solo lectura para SALVAJEVIP.

Ejecución local:
  set SHOPIFY_SHOP=tu-tienda.myshopify.com
  py backend/v04/shopify_connect.py

Solicita las credenciales de forma interactiva, sin guardarlas en disco.
No enviar secretos al chat ni subirlos al repositorio.
"""
import getpass
import json
import os
import urllib.error
import urllib.parse
import urllib.request

try:
    from .shopify_catalog import PRODUCTS_QUERY, normalise_products, query_variables
except ImportError:
    from shopify_catalog import PRODUCTS_QUERY, normalise_products, query_variables

API_VERSION = "2026-10"


def request_json(url, *, form=None, token=None):
    headers = {"Accept": "application/json"}
    if form is not None:
        body = urllib.parse.urlencode(form).encode("utf-8")
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    else:
        body = json.dumps({"query": PRODUCTS_QUERY, "variables": query_variables()}).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if token:
        headers["X-Shopify-Access-Token"] = token
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=25) as response:
        return json.load(response)


def main():
    print("NEXORA AI - Conexión Shopify de solo lectura")
    shop = os.getenv("SHOPIFY_SHOP", "").strip().lower()
    if not shop:
        shop = input("Dominio .myshopify.com: ").strip().lower()
    if not shop.endswith(".myshopify.com") or "/" in shop or " " in shop:
        raise ValueError("Usa solo el dominio de Shopify, sin https://")
    client_id = getpass.getpass("ID de cliente: ").strip()
    client_secret = getpass.getpass("Secreto del cliente (oculto): ").strip()
    if not client_id or not client_secret:
        raise ValueError("Faltan credenciales")
    try:
        auth = request_json(
            f"https://{shop}/admin/oauth/access_token",
            form={"grant_type": "client_credentials", "client_id": client_id, "client_secret": client_secret},
        )
        token = auth.get("access_token")
        if not token:
            raise ValueError("Shopify no devolvió token de acceso")
        data = request_json(
            f"https://{shop}/admin/api/{API_VERSION}/graphql.json",
            token=token,
        )
        products = normalise_products(data)
    except urllib.error.HTTPError as error:
        print(f"Shopify devolvió HTTP {error.code}. Revisa dominio, instalación y método de autenticación.")
        return
    except (urllib.error.URLError, ValueError, KeyError, TypeError) as error:
        print(f"No se pudo completar la lectura: {type(error).__name__}")
        return
    finally:
        client_secret = ""
        client_id = ""
    print(f"Productos recibidos: {len(products['products'])}")
    for product in products["products"]:
        print(f"\n{product['title']} ({product['status']})")
        for variant in product["variants"]:
            print(f"  {variant['title']}: {variant['price']} | unidades: {variant['inventory_quantity']} | disponible: {variant['available_for_sale']}")
    if products["has_next_page"]:
        print("Hay más productos. Se necesita paginación para leer el catálogo completo.")


if __name__ == "__main__":
    main()
