# NEXORA AI — backend v0.4 (preparación)

Esta carpeta incorpora la primera base de datos multiempresa en **Cloudflare D1 / SQLite**. La demo de `main` y el Worker publicado **no se han modificado ni desplegado**.

## Contenido
- `schema.sql`: 10 tablas para negocios, usuarios, membresías (propietario, encargado, empleado), módulos, contactos, conversaciones, mensajes, alertas, citas y llamadas.
- `test_schema.py`: verifica que SQLite crea las tablas y rechaza enlaces entre negocios distintos.

## Prueba local
Desde la raíz del repositorio con Python 3:

```bash
python backend/v04/test_schema.py
```

## Aplicación futura a Cloudflare D1
Crear **una base nueva** llamada `nexora-db` y configurar Wrangler para la cuenta correcta. Cuando se haya revisado el entorno y se autorice la ejecución:

```bash
npx wrangler d1 execute nexora-db --remote --file=backend/v04/schema.sql
```

No ejecutar en una base con datos sin plan de migración y copia.

## Seguridad: pendiente antes de producción
Las claves foráneas previenen relaciones cruzadas, pero **NO autorizan usuarios ni aíslan consultas automáticamente**. La API deberá validar la sesión y comprobar en servidor la membresía de cada negocio en **todas** las operaciones. Falta autenticación, 2FA privilegiados, auditoría, retención y borrado RGPD, control de acceso y límites de uso.

No almacenar secretos, datos de clientes ni números reales en este repositorio público. WhatsApp, llamadas, panel privado, avisos y agenda todavía **no están conectados**.

**Siguiente hito:** API autenticada sobre D1, pruebas de aislamiento por negocio y después integración controlada con el chat existente.
