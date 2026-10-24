"""Prueba de integridad del esquema D1 (sin red ni datos reales)."""
from pathlib import Path
import sqlite3

db = sqlite3.connect(":memory:")
db.execute("PRAGMA foreign_keys=ON")
db.executescript(Path(__file__).with_name("schema.sql").read_text(encoding="utf-8"))
tables = db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchall()
assert len(tables) == 10, tables
for suffix in ("a", "b"):
    b, c, v = "biz-"+suffix, "contact-"+suffix, "conv-"+suffix
    db.execute("INSERT INTO businesses(id,name) VALUES(?,?)", (b,b))
    db.execute("INSERT INTO contacts(id,business_id) VALUES(?,?)", (c,b))
    db.execute("INSERT INTO conversations(id,business_id,contact_id,channel) VALUES(?,?,?,?)", (v,b,c,"web"))
    db.execute("INSERT INTO messages(id,business_id,conversation_id,sender_type,body) VALUES(?,?,?,?,?)", ("msg-"+suffix,b,v,"contact","ficticio"))
assert db.execute("SELECT COUNT(*) FROM messages WHERE business_id='biz-a'").fetchone()[0] == 1
for query, args in [
    ("INSERT INTO messages(id,business_id,conversation_id,sender_type,body) VALUES(?,?,?,?,?)", ("cross","biz-a","conv-b","contact","no")),
    ("INSERT INTO conversations(id,business_id,contact_id,channel) VALUES(?,?,?,?)", ("cross","biz-a","contact-b","web"))
]:
    try:
        db.execute(query, args)
    except sqlite3.IntegrityError:
        pass
    else:
        raise AssertionError("Se aceptó una relación entre negocios distintos")
# La asignación de conversaciones debe respetar la pertenencia al negocio.
for suffix in ("a", "b"):
    db.execute("INSERT INTO users(id,auth_subject) VALUES(?,?)", ("user-"+suffix, "auth-"+suffix))
    db.execute("INSERT INTO business_memberships(business_id,user_id,role) VALUES(?,?,?)", ("biz-"+suffix, "user-"+suffix, "employee"))
db.execute("UPDATE conversations SET assigned_user_id=? WHERE id=?", ("user-a", "conv-a"))
try:
    db.execute("UPDATE conversations SET assigned_user_id=? WHERE id=?", ("user-b", "conv-a"))
except sqlite3.IntegrityError:
    pass
else:
    raise AssertionError("Se permitió asignar un empleado de otro negocio")
# Al salir un empleado, debe desasignarse antes de borrar su membresía.
try:
    db.execute("DELETE FROM business_memberships WHERE business_id=? AND user_id=?", ("biz-a", "user-a"))
except sqlite3.IntegrityError:
    pass
else:
    raise AssertionError("Se borró una membresía con conversaciones asignadas")
db.execute("UPDATE conversations SET assigned_user_id=NULL WHERE id=?", ("conv-a",))
db.execute("DELETE FROM business_memberships WHERE business_id=? AND user_id=?", ("biz-a", "user-a"))
assert db.execute("SELECT assigned_user_id FROM conversations WHERE id='conv-a'").fetchone()[0] is None
# Aislamiento en tablas vinculadas a conversaciones y contactos.
for query, args in [
    ("INSERT INTO alerts(id,business_id,conversation_id,kind) VALUES(?,?,?,?)", ("alert-cross", "biz-a", "conv-b", "lead")),
    ("INSERT INTO appointments(id,business_id,contact_id,service_name,starts_at,ends_at) VALUES(?,?,?,?,?,?)", ("appt-cross-contact", "biz-a", "contact-b", "revision", "2030-01-01T10:00", "2030-01-01T11:00")),
    ("INSERT INTO appointments(id,business_id,contact_id,conversation_id,service_name,starts_at,ends_at) VALUES(?,?,?,?,?,?,?)", ("appt-cross-conv", "biz-a", "contact-a", "conv-b", "revision", "2030-01-01T10:00", "2030-01-01T11:00")),
    ("INSERT INTO calls(id,business_id,conversation_id) VALUES(?,?,?)", ("call-cross", "biz-a", "conv-b")),
]:
    try:
        db.execute(query, args)
    except sqlite3.IntegrityError:
        pass
    else:
        raise AssertionError("Se aceptó una referencia cruzada: " + query)
# Valores de rol no autorizados deben rechazarse.
try:
    db.execute("INSERT INTO business_memberships(business_id,user_id,role) VALUES(?,?,?)", ("biz-a", "user-b", "superadmin"))
except sqlite3.IntegrityError:
    pass
else:
    raise AssertionError("Se aceptó un rol de negocio inválido")
# Casos positivos: empleados de su propio negocio, mensajes y alertas válidos.
db.execute("UPDATE conversations SET assigned_user_id=? WHERE id=?", ("user-b", "conv-b"))
db.execute("INSERT INTO alerts(id,business_id,conversation_id,kind) VALUES(?,?,?,?)", ("alert-ok", "biz-a", "conv-a", "lead"))
db.execute("INSERT INTO appointments(id,business_id,contact_id,conversation_id,service_name,starts_at,ends_at) VALUES(?,?,?,?,?,?,?)", ("appt-ok", "biz-a", "contact-a", "conv-a", "revision", "2030-01-01T10:00", "2030-01-01T11:00"))
db.execute("INSERT INTO calls(id,business_id,conversation_id) VALUES(?,?,?)", ("call-ok", "biz-b", "conv-b"))
# Restricciones de estados y canales.
for query, args in [
    ("INSERT INTO conversations(id,business_id,contact_id,channel) VALUES(?,?,?,?)", ("invalid-channel", "biz-a", "contact-a", "telegram")),
    ("UPDATE conversations SET status=? WHERE id=?", ("inventado", "conv-a")),
    ("INSERT INTO messages(id,business_id,conversation_id,sender_type,body) VALUES(?,?,?,?,?)", ("invalid-sender", "biz-a", "conv-a", "unknown", "x")),
]:
    try:
        db.execute(query, args)
    except sqlite3.IntegrityError:
        pass
    else:
        raise AssertionError("Se aceptó un valor inválido: " + query)
assert db.execute("PRAGMA foreign_key_check").fetchall() == []
# Comprobaciones de permisos basadas en identidad verificada y membresía.
from permissions import resolve_actor, allowed, list_visible_conversations

actor_b = resolve_actor(db, auth_subject="auth-b", business_id="biz-b")
assert actor_b is not None
assert resolve_actor(db, auth_subject="auth-b", business_id="biz-a") is None
assert not allowed(actor_b, "business.settings", resource_business_id="biz-b")
assert allowed(actor_b, "conversations.read", resource_business_id="biz-b", assigned_user_id="user-b")
assert not allowed(actor_b, "conversations.read", resource_business_id="biz-a", assigned_user_id="user-b")
assert not allowed(actor_b, "conversations.read", resource_business_id="biz-b", assigned_user_id="user-a")
assert [r[0] for r in list_visible_conversations(db, actor_b)] == ["conv-b"]
db.execute("INSERT INTO users(id,auth_subject) VALUES(?,?)", ("owner-a", "auth-owner-a"))
db.execute("INSERT INTO business_memberships(business_id,user_id,role) VALUES(?,?,?)", ("biz-a", "owner-a", "owner"))
owner_a = resolve_actor(db, auth_subject="auth-owner-a", business_id="biz-a")
assert allowed(owner_a, "business.settings", resource_business_id="biz-a")
assert not allowed(owner_a, "business.settings", resource_business_id="biz-b")
assert not allowed(owner_a, "undefined.action", resource_business_id="biz-a")
assert [r[0] for r in list_visible_conversations(db, owner_a)] == ["conv-a"]
# Comprobar que los mensajes siguen la misma política de acceso.
from permissions import list_visible_messages
assert [row[0] for row in list_visible_messages(db, actor_b, "conv-b")] == ["msg-b"]
assert list_visible_messages(db, actor_b, "conv-a") == []
assert [row[0] for row in list_visible_messages(db, owner_a, "conv-a")] == ["msg-a"]
assert list_visible_messages(db, owner_a, "conv-b") == []
print("OK: 10 tablas, aislamiento entre negocios, asignaciones y referencias verificadas.")
