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
print("OK: 10 tablas y relaciones multiempresa verificadas.")
