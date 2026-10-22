# Borrador: pull request de `desarrollo` → `main`

> **Borrador para el final.** Por ahora se trabaja solo en local (decisión del 2026-10-21): este PR no se crea
> hasta que la app esté lista. Antes de usarlo, actualizar los cambios, las pruebas y las decisiones pendientes.
> Escrito el 2026-10-22, con `desarrollo` en `150f003`.

**Título sugerido:** Rama desarrollo: obtención automática (lecciones 1–3), tarea programada local y ramas pendientes

---

## Qué trae esta rama

`desarrollo` junta todo el trabajo en local desde el 19/10. **Reemplaza a estas ramas, que no hace falta unir por separado:**
`acta-despliegue`, `leccion-10`, `obtencion-automatica`, `doctor-sin-mail-to`, `regla-camaras-intraorales`,
`panel-aviso-sin-evaluar` y `zip-pliegos`. Si alguna tiene un PR abierto, se puede cerrar.

### Obtención automática de SICOP (aprobada por Oscar el 21/10)
- **Lección 1, lector de Gmail de solo lectura** (`app/sources/gmail_reader.py`): permiso `gmail.readonly` con un
  token aparte del de envío; solo lee correos de `info@sicop.go.cr` con los dos asuntos de SICOP. Comandos
  `obtain gmail-auth` y `obtain check-mail`.
- **Lección 2, solicitud con navegador** (`app/sources/sicop_browser.py`, `obtain request [--ver]`): pide el reporte
  con Playwright y escribe el código del correo. Una sola solicitud por día (migración 0009). Ante un CAPTCHA o un
  bloqueo se detiene y no reintenta.
- **Lección 3, espera, descarga y validación** (`app/sources/obtencion.py`, `obtain poll [--seguir]`,
  `obtain status`): máquina de estados (migración 0010), descarga con SHA-256, validación del ZIP y copia a la
  carpeta de entrada. No importa nada: eso queda para la lección 4.
- Decisión, reglas y revisión de la normativa de SICOP en `docs/DECISION_OBTENCION.md` (§6 y §8).

### Otros cambios
- **Tarea programada de Windows** para el ciclo local (`deploy/windows/`): de lunes a viernes a las 8:00,
  **siempre en dry-run**.
- **ZIP de pliegos** tal como llega de SICOP, en el ciclo y en el panel.
- **Regla de cámaras:** se excluyen las intraorales (falso positivo CCSS `20261001749`).
- **Panel:** aviso si hay datos importados sin evaluar.
- **`doctor`** ya no pide `MAIL_TO`.
- Documentos: acta de despliegue, lección 10, `OPERACION.md` probado en Windows, métricas, bitácora y estado.

## Prueba real del 22/10 (con Oscar)
- `obtain request --ver`: código aceptado a las 08:05.
- El enlace llegó unos 50 min después. **SICOP bloqueó la descarga hecha por el programa** («No fue posible acceder a
  la página solicitada… ID de soporte»). Desde `150f003`, esa página se reporta como FALLO «control no
  automatizable», sin reintento.
- La descarga a mano funcionó; el ciclo #28 (dry-run) importó el ZIP sin rechazos.

## Para revisar / decidir (Oscar)
- [ ] **Descarga bloqueada:** ¿preguntamos a SICOP con el ID de soporte si se permite la descarga con un programa, o
      la dejamos manual (la solicitud y el código siguen automáticos)?
- [ ] Nuevas dependencias: `playwright>=1.45` en `requirements.txt` (`requirements.lock.txt` se rehace al final).
- [ ] Migraciones 0009 y 0010 (tabla `solicitudes_sicop`). Ya aplicadas en la base local.
- [ ] Aceptar `docs/DECISION_OBTENCION.md`.

## Pruebas
- `pytest`: **426 passed** (Windows, 22/10). Las de SICOP y Gmail usan páginas y correos **SIMULADOS**, sin salir a
  internet.

## Importante
- **No instalar en el servidor todavía.** Se decidió trabajar solo en local; el servidor se actualiza una sola vez, al
  final.
- Ningún correo real se envía: avisos en dry-run (`NOTIFICATIONS_ENABLED=false`).
- La guía `Guia_Obtencion_Automatica_SICOP.docx` no se subió a propósito, porque una captura muestra un enlace real
  de descarga.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
