# Fase 2: el enriquecimiento desde la PC hacia el servidor

Diseño del 2026-11-09 (Ivania con Claude). Cumple la decisión del 27/10 (`DECISION_OBTENCION.md` §9: «la dirección
con token hacia el servidor se hace al desplegar»). Contexto: `docs/ACTUALIZACION_SERVIDOR.md`.

## Problema

Con la base en el servidor, la PC de Ivania deja de ser la principal. Pero la consulta de fichas y documentos en
SICOP necesita un navegador con ventana (decisión del 27/10), y el servidor no tiene pantalla. Sin esta fase, los
carteles nuevos quedan sin ficha, documentos ni resumen con IA.

## Decisiones de Ivania (2026-11-09)

1. **La cola de resúmenes con IA corre en el servidor** (no usa navegador: lee los documentos de la base y llama a
   OpenAI). Unidad systemd propia, mismo presupuesto diario.
2. **La PC pide la cola y devuelve resultados.** A las 10:00 la PC pide al servidor qué carteles consultar, abre
   SICOP con la ventana visible y manda, cartel por cartel, la ficha y los documentos. El servidor los guarda.

## Cómo funciona

```
10:00  PC ──POST /api/enriquecimiento/corridas (token)──▶ servidor: borrado al cierre, cola, corrida nueva
       PC ◀── carteles a consultar (número, título, cierre y los documentos que el servidor ya tiene) ──
       PC: navegador con ventana → ficha + documentos de cada cartel (grabación en la PC)
       PC ──POST …/corridas/N/consultas (token), uno por cartel──▶ servidor
             ficha tal cual (respuestas de SICOP) + archivos + bitácora de la consulta
       servidor: guardar_ficha → guardar_documento (lee el texto de los PDF) → bitácora → reevaluar
       PC ──POST …/corridas/N/cierre (token)──▶ servidor: ok, con_fallos o detenida
10:45  servidor: ia cola (sicop-ia-cola.timer) → resúmenes con IA de lo enriquecido
```

- **El servidor repite los mismos guardados** que hoy hace la PC (`guardar_ficha` y `guardar_documento` de
  `app/sources`): la misma revisión de cada archivo, el mismo texto de los PDF, la misma deduplicación por huella.
  No se copian filas de una base a otra, así que no hay que reconciliar números internos.
- **La PC trabaja con una base de trabajo propia** (`data/trabajo.db`, solo para el navegador): recibe los
  carteles de la cola y guarda ahí lo que consulta, como hoy. Lo que vale es lo del servidor.
- **Las grabaciones** (video y capturas) se quedan en la PC, como hoy; al servidor va la ruta en la bitácora.
- **Repetir es seguro:** si un envío se corta, se vuelve a mandar; el servidor reconoce la ficha y los archivos que
  ya tiene y no los duplica.

## Seguridad

- **Token** largo y aleatorio (`ENRICH_TOKEN`), el mismo en `app.env` del servidor y en el `.env` de la PC. Lo
  genera el administrador en el servidor, como `SESSION_SECRET`; nunca va a Git, a un chat ni a Claude.
- Solo por **HTTPS** (`https://sicop.hermatix.com`). Comparación en tiempo constante. Sin token o con uno malo:
  401, y queda en el registro del servidor (`journalctl`), sin escribir en la base. Sin `ENRICH_TOKEN` en el
  servidor, las direcciones no existen (404).
- Las tres direcciones **solo** abren y cierran la corrida y reciben resultados de carteles que estaban en su cola
  (`enrich_runs.cola_json`, migración 0040); no leen revisiones, usuarios, perfil ni nada más.
- El servidor no le cree a la PC: decide él si la ficha es nueva, vuelve a quitar los datos de personas y revisa
  cada archivo como siempre.
- Límites: tamaño máximo por envío (`DOCUMENT_MAX_MB` por archivo, `DOCUMENTS_MAX_MB_PER_TENDER` por cartel) y los
  mismos tipos de archivo que hoy.

## Pasos (cada uno con sus pruebas, datos SIMULADOS)

1. **Cola de IA en el servidor:** `deploy/systemd/sicop-ia-cola.service` y `.timer` (lunes a viernes, 10:45), y la
   guía de actualización al día. Sin código nuevo de la app (`ia cola` ya existe).
2. **Servidor, las tres direcciones** (hecho, 2026-11-09): `app/sources/remoto.py` y `app/web/api_enriquecimiento.py`,
   migración 0040, `ENRICH_TOKEN`. Pedir la cola crea la corrida y borra lo que cerró: por eso es `POST`, no `GET`.
   8 pruebas en `tests/test_api_enriquecimiento.py` (token, corrida completa, repetir sin duplicar, fuera de la
   cola, CAPTCHA, datos de personas, tope).
3. **PC, `enrich remoto`** (hecho, 2026-11-09): `app/sources/enriquecimiento_pc.py` y `python -m app.cli enrich
   remoto [--max N]`. Pide la cola, limpia sus grabaciones viejas (menos las de FALLO sin revisar, que dice el
   servidor), arma `data/trabajo/` nueva, consulta con `consultar_uno` **sin volver a bajar** lo que el servidor
   ya tiene y envía cada cartel al terminarlo. Ante un CAPTCHA, lo mismo que hoy. HTTPS con `urllib` (sin
   dependencias nuevas); reintenta 3 veces si el servidor no responde o da 5xx, no si responde 4xx. Configuración:
   `ENRICH_SERVER_URL` (solo `https://`, o `http://127.0.0.1` para probar) y `ENRICH_TOKEN`; con
   `ENRICH_SERVER_URL`, `enrich run` se niega (no escribe en la base local). 5 pruebas en
   `tests/test_enriquecimiento_pc.py` (dos de punta a punta con el SICOP simulado).
4. **Cierre** (hecho, 2026-11-09): `deploy/windows/sicop-enriquecimiento.ps1 -Remoto` (solo `enrich remoto`;
   `deploy/windows/README.md`, «Fase 2»); la bitácora del servidor dice que el video de una consulta remota está en
   la PC (`enrich_runs.origen`); misión de ayuda 18; `ACTUALIZACION_SERVIDOR.md` §11 (token y activación).
   **Prueba real (9/11):** la app de la PC como servidor de prueba (puerto 8765, copia de la base) y `enrich remoto
   --max 1` con SICOP real: `20261100801` consultado en 108 s, 7 documentos guardados en el «servidor» (92 páginas
   de texto), reevaluado de Baja a Media, el video en la «PC», la base real sin tocar.

## Pendiente

- Probarlo contra el servidor real (`ACTUALIZACION_SERVIDOR.md` §11), con Oscar.
