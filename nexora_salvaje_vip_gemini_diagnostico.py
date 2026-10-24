"""NEXORA AI | Salvaje VIP: Gemini + Shopify. Solo lectura. Python 3 sin paquetes externos."""
import json
import threading
import urllib.request
import urllib.error
import urllib.parse
import tkinter as tk
from tkinter import ttk

SHOP = "0jssv4-iv.myshopify.com"
VERSION = "2026-10"
PREFERRED_MODELS = ("gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-2.0-flash")
QUERY = """query { products(first:100) { pageInfo { hasNextPage } nodes { title status variants(first:100) { pageInfo { hasNextPage } nodes { title price inventoryQuantity availableForSale } } } } }"""
products = []
history = []
shopify_token = None
gemini_key = None
busy = False

def post_json(url, data, headers):
    request = urllib.request.Request(url, data=json.dumps(data).encode("utf-8"),
                                     headers=headers, method="POST")
    with urllib.request.urlopen(request, timeout=35) as response:
        return json.load(response)

def connect_shopify(client_id, client_secret):
    data = urllib.parse.urlencode({"grant_type": "client_credentials",
                                   "client_id": client_id, "client_secret": client_secret}).encode()
    req = urllib.request.Request("https://" + SHOP + "/admin/oauth/access_token",
                                 data=data, headers={"Content-Type": "application/x-www-form-urlencoded"},
                                 method="POST")
    with urllib.request.urlopen(req, timeout=35) as response:
        token = json.load(response)["access_token"]
    return token, get_catalog(token)

def get_catalog(token):
    result = post_json("https://" + SHOP + "/admin/api/" + VERSION + "/graphql.json",
                       {"query": QUERY}, {"Content-Type": "application/json",
                                          "X-Shopify-Access-Token": token})
    if result.get("errors"):
        raise ValueError("Shopify ha rechazado la consulta.")
    catalog = result["data"]["products"]
    if catalog["pageInfo"]["hasNextPage"] or any(p["variants"]["pageInfo"]["hasNextPage"] for p in catalog["nodes"]):
        raise ValueError("Catálogo incompleto: hace falta paginación.")
    return [p for p in catalog["nodes"] if p["status"] == "ACTIVE"]

def catalog_context(catalog):
    entries = []
    for p in catalog:
        variants = []
        for v in p["variants"]["nodes"]:
            variants.append({"variante": v["title"], "precio_eur": v["price"],
                             "disponible_shopify": v["availableForSale"],
                             "unidades_registradas": v["inventoryQuantity"]})
        entries.append({"producto": p["title"], "variantes": variants})
    return json.dumps(entries, ensure_ascii=False)

SYSTEM = """Eres la asistente virtual de pruebas de la boutique Salvaje VIP.
Hablas español de España, de manera cálida, breve, simpática y natural, como una buena dependienta.
Ayudas a descubrir prendas y respondes preguntas de seguimiento usando el historial.
El catálogo proporcionado es la ÚNICA fuente de verdad para productos, precios, variantes y existencias.
No inventes artículos, tallas, precios, promociones, fotos, enlaces, disponibilidad ni cantidades.
Si Shopify marca disponible=false, nunca ofrezcas esa variante como disponible.
Si el inventario no es un número fiable o es 0 o negativo, no prometas unidades.
No asegures que una talla existe si la variante no la especifica.
Si te preguntan por pagos, devoluciones, entregas, horarios o descuentos y no hay datos verificados,
indica que el equipo debe confirmarlo. No afirmes que has reservado, comprado o enviado nada.
No pidas datos personales. No prometas acciones ni acceso a herramientas que no tienes.
Este chat es una simulación: NO está conectado a WhatsApp ni envía mensajes a clientes.
Responde solo con información de catálogo y consejos de estilo generales."""

def choose_model(key):
    request = urllib.request.Request(
        "https://generativelanguage.googleapis.com/v1beta/models",
        headers={"x-goog-api-key": key})
    with urllib.request.urlopen(request, timeout=30) as response:
        listing = json.load(response)
    supported = [m["name"].split("/")[-1] for m in listing.get("models", [])
                 if "generateContent" in m.get("supportedGenerationMethods", [])]
    for model in PREFERRED_MODELS:
        if model in supported:
            return model
    for model in supported:
        if "flash" in model and "preview" not in model:
            return model
    if supported:
        return supported[0]
    raise ValueError("Tu clave no muestra modelos disponibles para generateContent.")


def ask_gemini(key, question, catalog, previous):
    contents = []
    for role, text in previous[-12:]:
        contents.append({"role": role, "parts": [{"text": text}]})
    contents.append({"role": "user", "parts": [{"text": question}]})
    model = choose_model(key)
    url = "https://generativelanguage.googleapis.com/v1beta/models/" + model + ":generateContent"
    payload = {
        "systemInstruction": {"parts": [{"text": SYSTEM + "\nCATÁLOGO ACTUAL VERIFICADO EN SHOPIFY:\n" + catalog_context(catalog)}]},
        "contents": contents,
        "generationConfig": {"temperature": 0.3, "maxOutputTokens": 700}
    }
    response = post_json(url, payload, {"Content-Type": "application/json", "x-goog-api-key": key})
    candidates = response.get("candidates") or []
    if not candidates:
        raise ValueError("Gemini no devolvió una respuesta.")
    parts = candidates[0].get("content", {}).get("parts", [])
    answer = "".join(p.get("text", "") for p in parts).strip()
    if not answer:
        raise ValueError("Gemini no devolvió texto.")
    return answer

root = tk.Tk()
root.title("NEXORA AI | SALVAJE VIP · Gemini + Shopify")
root.geometry("900x690")
root.minsize(760, 500)
root.configure(bg="#141724")
header = tk.Frame(root, bg="#141724", padx=16, pady=10)
header.pack(side="top", fill="x")
tk.Label(header, text="NEXORA AI · SALVAJE VIP", font=("Segoe UI", 17, "bold"),
         fg="white", bg="#141724").pack(anchor="w")
tk.Label(header, text="Gemini + Shopify · Solo lectura · Pruebas locales · No envía mensajes a clientes",
         fg="#b9bdd0", bg="#141724").pack(anchor="w")
auth = tk.Frame(root, bg="#202436", padx=12, pady=10)
auth.pack(side="top", fill="x", padx=14)
for col, label in enumerate(("ID cliente Shopify", "Secreto Shopify", "Clave API Gemini")):
    tk.Label(auth, text=label, fg="white", bg="#202436").grid(row=0, column=col, sticky="w", padx=3)
id_input = ttk.Entry(auth, width=25)
secret_input = ttk.Entry(auth, width=25, show="●")
gemini_input = ttk.Entry(auth, width=30, show="●")
for col, widget in enumerate((id_input, secret_input, gemini_input)):
    widget.grid(row=1, column=col, padx=3, pady=5, sticky="ew")
    auth.columnconfigure(col, weight=1)
status = tk.StringVar(value="Introduce las tres credenciales y pulsa Conectar.")
tk.Label(root, textvariable=status, bg="#141724", fg="#f3d4a1",
         anchor="w", padx=16).pack(side="top", fill="x", pady=6)
bottom = tk.Frame(root, bg="#141724", padx=14, pady=12)
bottom.pack(side="bottom", fill="x")
message_input = ttk.Entry(bottom, font=("Segoe UI", 11))
message_input.pack(side="left", fill="x", expand=True, padx=(0, 8))
chat = tk.Text(root, wrap="word", state="disabled", font=("Segoe UI", 11),
               bg="#202436", fg="#f8f8fc", padx=12, pady=12)
chat.pack(side="top", fill="both", expand=True, padx=14, pady=6)
chat.tag_config("bot", foreground="#f3b8d7")
chat.tag_config("user", foreground="#b7d9ff")

def say(who, text, tag):
    chat.configure(state="normal")
    chat.insert("end", who + ": " + text + "\n\n", tag)
    chat.configure(state="disabled")
    chat.see("end")

def friendly_error(exc):
    if isinstance(exc, urllib.error.HTTPError):
        try:
            info = json.loads(exc.read().decode("utf-8")).get("error", {})
            message = str(info.get("message", ""))
            if gemini_key:
                message = message.replace(gemini_key, "[CLAVE OCULTA]")
            return "HTTP " + str(exc.code) + ": " + message[:400]
        except Exception:
            return "HTTP " + str(exc.code)

def finish_connection(result, error):
    global shopify_token, gemini_key, busy
    busy = False
    connect_button.configure(state="normal")
    if error:
        status.set("No se pudo conectar: " + friendly_error(error))
        return
    token, catalog, key = result
    shopify_token = token
    gemini_key = key
    products.clear()
    products.extend(catalog)
    history.clear()
    id_input.delete(0, "end")
    secret_input.delete(0, "end")
    gemini_input.delete(0, "end")
    status.set("Shopify conectado · " + str(len(products)) + " productos activos · Gemini configurado · Solo lectura")
    say("NEXORA", "¡Conectada a Shopify! 💖 Pregúntame por nuestras prendas. Gemini responderá cuando envíes tu mensaje.", "bot")

def connect():
    global busy
    if busy:
        return
    cid = id_input.get().strip()
    secret = secret_input.get().strip()
    key = gemini_input.get().strip()
    if not (cid and secret and key):
        status.set("Falta el ID, secreto de Shopify o clave de Gemini.")
        return
    busy = True
    connect_button.configure(state="disabled")
    status.set("Conectando con Shopify…")
    def worker():
        try:
            token, catalog = connect_shopify(cid, secret)
            root.after(0, finish_connection, (token, catalog, key), None)
        except Exception as exc:
            root.after(0, finish_connection, None, exc)
    threading.Thread(target=worker, daemon=True).start()

connect_button = ttk.Button(auth, text="Conectar", command=connect)
connect_button.grid(row=1, column=3, padx=5)

def finish_reply(question, answer, error):
    global busy
    busy = False
    send_button.configure(state="normal")
    if error:
        say("NEXORA", "No he podido consultar Gemini: " + friendly_error(error), "bot")
    else:
        history.extend([("user", question), ("model", answer)])
        say("NEXORA", answer, "bot")
    status.set("Shopify conectado · Gemini configurado (sin verificar) · Solo lectura")

def send(event=None):
    global busy
    question = message_input.get().strip()
    if not question or busy:
        return
    if not shopify_token or not gemini_key:
        status.set("Primero conecta Shopify y configura Gemini.")
        return
    message_input.delete(0, "end")
    say("TÚ", question, "user")
    busy = True
    send_button.configure(state="disabled")
    status.set("Consultando Shopify y preguntando a Gemini…")
    def worker():
        try:
            fresh = get_catalog(shopify_token)
            answer = ask_gemini(gemini_key, question, fresh, history)
            products.clear()
            products.extend(fresh)
            root.after(0, finish_reply, question, answer, None)
        except Exception as exc:
            root.after(0, finish_reply, question, None, exc)
    threading.Thread(target=worker, daemon=True).start()

send_button = ttk.Button(bottom, text="Enviar", command=send)
send_button.pack(side="right")
message_input.bind("<Return>", send)
say("NEXORA", "¡Hola! 💖 Soy la versión de pruebas de NEXORA con Gemini y Shopify.", "bot")
root.mainloop()
