# NEXORA AI v0.4 — plan de API segura (sin despliegue)

Estado: documento de diseño. El esquema SQLite y sus pruebas existen, pero no constituyen una API autenticada. No hay conexión con clientes reales.

## Principio central
Toda operación debe validar la identidad en servidor, seleccionar el negocio autorizado y comprobar su rol. Nunca confiar en business_id, user_id, permisos o instrucciones suministradas por el navegador.

## Secuencia mínima de una petición
1. Verificar sesión/token del proveedor de autenticación (firma, audiencia, expiración, emisor).
2. Resolver usuario interno desde auth_subject; denegar si no existe.
3. Resolver business_id solicitado y membresía activa en business_memberships.
4. Comprobar acción y rol con una política central de denegación por defecto.
5. Ejecutar la consulta SQL con business_id como filtro explícito, parámetros enlazados y transacción cuando proceda.
6. Auditar cambios de permisos, traspasos humanos y operaciones sensibles; no registrar contenido innecesario.
7. Limitar peticiones por usuario, negocio y canal; no exponer secretos al cliente.

## Política inicial (propuesta, requiere revisión)
- owner: configuración de su negocio, usuarios y conversaciones; no puede modificar negocios ajenos.
- manager: atender conversaciones, asignar empleados y revisar oportunidades; sin gestionar propietarios ni facturación.
- employee: ver y atender únicamente conversaciones asignadas, según reglas del negocio.
- superadmin: soporte técnico restringido; nunca acceso indiscriminado a conversaciones. Acceso excepcional autorizado y auditado.

## Rutas iniciales previstas
- GET /api/me: identidad y negocios accesibles.
- GET /api/businesses/:businessId/conversations: paginado y filtrado por negocio y permisos.
- GET /api/businesses/:businessId/conversations/:id/messages: validar pertenencia y acceso.
- POST /api/businesses/:businessId/conversations/:id/handoff: transferencia humana atómica, desactivar respuesta automática.
- POST /api/businesses/:businessId/conversations/:id/assign: comprobar membresía del asignado y rol del solicitante.
- GET /api/businesses/:businessId/alerts: urgencias y bandeja.

## Invariantes que debe probar la API
- Usuario de negocio A recibe 403 al solicitar cualquier recurso de negocio B.
- Empleado no asignado no puede consultar conversaciones restringidas.
- No se puede asignar a un empleado que no pertenezca al negocio.
- Después del traspaso humano no se emiten nuevas respuestas IA para esa conversación.
- Reintentos de mensajes y webhooks son idempotentes; no duplican fichas ni alertas.
- Nunca inventar precios, stock, citas ni disponibilidad.
- No guardar claves de IA, WhatsApp o Cloudflare en el repositorio público.

## Advertencias del esquema actual
- Las claves foráneas separan referencias entre negocios, pero NO son autorización de lectura.
- appointments puede asociar un contacto y una conversación distintos del mismo negocio: la API debe validarlo o reforzar el esquema.
- assigned_user_id exige membresía en la empresa; antes de eliminarla hay que desasignar conversaciones en una transacción.
- No hay todavía políticas de retención, borrado RGPD, registro de auditoría ni autenticación.
- La base D1 nueva, migraciones, despliegues, WhatsApp y gastos requieren aprobación previa.

## Próximo hito
Ejecutar `python backend/v04/test_schema.py` en un entorno de pruebas. Solo después implementar una API local de demostración con identidad ficticia, tests de permisos y sin conexiones reales.
