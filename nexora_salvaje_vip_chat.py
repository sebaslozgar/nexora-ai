"""NEXORA AI - Chat de pruebas de Salvaje VIP conectado a Shopify.
Solo lectura: no envía mensajes a clientes ni modifica la tienda.
Requiere Python 3; sin dependencias externas.
"""
import json
import threading
import urllib.error
import urllib.parse
import urllib.request
import tkinter as tk
from tkinter import ttk

SHOP = "0jssv4-iv.myshopify.com"
API_VERSION = "2026-10"
QUERY = """
query {
  products(first: 100) {
    pageInfo { hasNextPage }
    nodes {
      title status
      variants(first: 100) {
        pageInfo { hasNextPage }
        nodes { title price inventoryQuantity availableForSale }
      }
    }
  }
}
"""


def post(url, data, headers):
    request = urllib.request.Request(url, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(request, timeout=25) as response:
        return json.load(response)


def fetch_catalog(client_id, client_secret):
    auth = post(
        f"https://{SHOP}/admin/oauth/access_token",
        urllib.parse.urlencode({
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
        }).encode(),
        {"Content-Type": "application/x-www-form-urlencoded"},
    )
    token = auth["access_token"]
    result = post(
        f"https://{SHOP}/admin/api/{API_VERSION}/graphql.json",
        json.dumps({"query": QUERY}).encode(),
        {"Content-Type": "application/json", "X-Shopify-Access-Token": token},
    )
    if result.get("errors"):
        raise ValueError("Shopify ha devuelto errores de consulta")
    catalog = result["data"]["products"]
    if catalog["pageInfo"]["hasNextPage"]:
        raise ValueError("El catálogo supera los 100 productos: paginación pendiente")
    for product in catalog["nodes"]:
        if product["variants"]["pageInfo"]["hasNextPage"]:
            raise ValueError("Una prenda tiene más de 100 variantes: consulta incompleta")
    return [p for p in catalog["nodes"] if p["status"] == "ACTIVE"]


def price(value):
    try:
        return f"{float(value):.2f}".replace(".", ",") + " €"
    except (ValueError, TypeError):
        return "precio no confirmado"


def product_text(product):
    lines = [product["title"]]
    for variant in product["variants"]["nodes"]:
        name = variant["title"]
        suffix = "" if name == "Default Title" else f" · {name}"
        available = variant.get("availableForSale")
        status = "disponible" if available is True else "disponibilidad sin confirmar"
        qty = variant.get("inventoryQuantity")
        stock = f" · {qty} unidades registradas" if isinstance(qty, int) else ""
        lines.append(f"  {price(variant.get('price'))}{suffix} · {status}{stock}")
    return "\n".join(lines)


def reply(question, products):
    q = question.casefold().strip()
    matches = [p for p in products if p["title"].casefold() in q]
    if matches:
        return "¡Claro! 💖 Esto aparece en nuestro catálogo:\n" + "\n\n".join(map(product_text, matches))
    if any(term in q for term in ("precio", "talla", "stock", "tenéis", "teneis", "disponib", "catálogo", "catalogo", "producto", "ropa", "vestido", "conjunto", "qué ten", "que ten")):
        return "¡Te cuento lo que tenemos confirmado! 💖\n" + ("\n\n".join(map(product_text, products)) or "No hay prendas activas verificadas.")
    if any(term in q for term in ("envío", "envio", "devoluci", "pago", "descuento", "reserva")):
        return "Para no darte información equivocada, el equipo de Salvaje VIP tiene que confirmar esas condiciones. 💖"
    return "¡Hola! 💖 Soy el asistente de pruebas de Salvaje VIP. Pregúntame por las prendas y precios de nuestro catálogo."


root = tk.Tk()
root.title("NEXORA AI | SALVAJE VIP · Chat de pruebas")
root.geometry("780x650")
root.configure(bg="#141724")
products = []
credentials = None

top = tk.Frame(root, bg="#141724", padx=18, pady=12)
top.pack(fill="x")
tk.Label(top, text="NEXORA AI · SALVAJE VIP", font=("Segoe UI", 17, "bold"), bg="#141724", fg="#ffffff").pack(anchor="w")
tk.Label(top, text="Chat de pruebas · Solo lectura · No envía mensajes a clientes", bg="#141724", fg="#b9bdd0").pack(anchor="w")

authframe = tk.Frame(root, bg="#202436", padx=16, pady=10)
authframe.pack(fill="x", padx=16)
tk.Label(authframe, text="ID de cliente", bg="#202436", fg="white").grid(row=0, column=0, sticky="w")
id_entry = ttk.Entry(authframe, width=37)
id_entry.grid(row=1, column=0, padx=(0, 10), pady=(4, 0))
tk.Label(authframe, text="Secreto del cliente", bg="#202436", fg="white").grid(row=0, column=1, sticky="w")
secret_entry = ttk.Entry(authframe, width=37, show="●")
secret_entry.grid(row=1, column=1, padx=(0, 10), pady=(4, 0))
status = tk.StringVar(value="Introduce tus credenciales solo en esta ventana y pulsa Conectar.")
tk.Label(root, textvariable=status, bg="#141724", fg="#f3d4a1", anchor="w", padx=18).pack(fill="x", pady=6)

chat = tk.Text(root, wrap="word", state="disabled", font=("Segoe UI", 11), bg="#202436", fg="#f8f8fc", padx=14, pady=14)
chat.pack(fill="both", expand=True, padx=16, pady=8)
chat.tag_config("bot", foreground="#f3b8d7")
chat.tag_config("user", foreground="#b7d9ff")


def say(author, message, tag):
    chat.configure(state="normal")
    chat.insert("end", author + ": " + message + "\n\n", tag)
    chat.configure(state="disabled")
    chat.see("end")


def connected(result, error):
    connect_btn.configure(state="normal")
    if error:
        status.set("No se pudo conectar: " + error + ". Comprueba las credenciales y el dominio.")
        return
    products.clear()
    products.extend(result)
    status.set(f"Conectado con Shopify · {len(products)} productos activos · Solo lectura")
    id_entry.delete(0, "end")
    secret_entry.delete(0, "end")
    say("NEXORA", "¡Conexión correcta! 💖 Ya puedo responder con los datos actuales de Shopify. Pregúntame por las prendas.", "bot")


def connect():
    client_id = id_entry.get().strip()
    client_secret = secret_entry.get().strip()
    if not client_id or not client_secret:
        status.set("Introduce el ID y el secreto del cliente.")
        return
    connect_btn.configure(state="disabled")
    status.set("Conectando con Shopify…")
    def worker():
        try:
            result = fetch_catalog(client_id, client_secret)
            root.after(0, connected, result, None)
        except urllib.error.HTTPError as exc:
            root.after(0, connected, None, f"HTTP {exc.code}")
        except Exception as exc:
            root.after(0, connected, None, type(exc).__name__)
    threading.Thread(target=worker, daemon=True).start()


connect_btn = ttk.Button(authframe, text="Conectar Shopify", command=connect)
connect_btn.grid(row=1, column=2, pady=(4, 0))

bottom = tk.Frame(root, bg="#141724", padx=16, pady=12)
bottom.pack(fill="x")
entry = ttk.Entry(bottom, font=("Segoe UI", 11))
entry.pack(side="left", fill="x", expand=True, padx=(0, 8))


def send(event=None):
    message = entry.get().strip()
    if not message:
        return
    entry.delete(0, "end")
    say("TÚ", message, "user")
    if not products:
        say("NEXORA", "Primero conecta Shopify para consultar información verificada.", "bot")
        return
    say("NEXORA", reply(message, products), "bot")


ttk.Button(bottom, text="Enviar", command=send).pack(side="right")
entry.bind("<Return>", send)
say("NEXORA", "¡Hola! 💖 Conecta Shopify arriba y empezamos a probar el chat.", "bot")
root.mainloop()
