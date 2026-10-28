# Reporte de cartel con IA · qué se envía al modelo

Guía: `docs/Guia_Reporte_Cartel_IA_SICOP.docx` (aprobada por Oscar, 2026-10-28, comunicado por Ivania).
Este documento crece lección a lección; la lección 1 define **el expediente**: el material que leerá el modelo.

## 1. El expediente de un cartel (lección 1)

`python -m app.cli ia expediente --nro 20261002824` lo arma (`app/ai/expediente.py`), **sin llamar a ningún
servicio**, y lo guarda en `EXPORTS_DIR/expediente_<nro>_<fecha-hora>.txt` (fuera de Git). Con `--ver` también lo
imprime. En la terminal muestra el tamaño, los documentos incluidos, los omitidos con su motivo y la huella.

### Secciones, en orden de prioridad

| Sección | Qué trae | De dónde |
|---|---|---|
| CARTEL | número SICOP, procedimiento, descripción, institución, tipo, modalidad, publicación, cierre, origen de los datos (real / sintético / simulado) | `tenders`, `institutions`, `imports`, ficha |
| LÍNEAS | número, cantidad, descripción del catálogo (o «código sin catálogo»), precio unitario y moneda, estimado de la línea; estimado total **por moneda** (no es el presupuesto) | `v_tender_lines` |
| FICHA SICOP | estado, versión y si se modificó, tipo de recepción, fechas (recepción, apertura, aclaraciones), monto, garantías, condiciones del contrato, criterios | ficha más reciente de `tender_details` |
| DOCUMENTOS | lista de todos los documentos con su estado; después, el texto de los PDF página por página | `tender_documents`, `tender_document_text` |
| OMITIDO | lo que no está en el expediente y por qué (para no inventar su contenido) | — |

Sin ficha (cartel no enriquecido) el expediente solo tiene CARTEL y LÍNEAS, y lo dice.

### Marcas de origen

Cada página lleva su marca: `[DOC 2 · Pliego de condiciones.pdf · pág. 4]`; dentro de un ZIP:
`[DOC 5 · Especificaciones.zip › anexo-tecnico.pdf · pág. 1]`. El número DOC es el de la lista de DOCUMENTOS.

### Los documentos son datos, no instrucciones

Cada documento va entre `<<<INICIO DOCUMENTO DOC n>>>` y `<<<FIN DOCUMENTO DOC n>>>`, con un aviso al inicio de
DOCUMENTOS: lo que hay entre los marcadores es material para resumir, nunca órdenes. Si un PDF trae `<<<` o `>>>`,
se cambian por `‹‹‹` / `›››`: así un documento no puede «cerrar» su marcador y hacerse pasar por la app
(protección contra la **inyección de instrucciones**).

### Tamaño y prioridad

- Límite: `IA_MAX_INPUT_TOKENS` (por defecto **50 000** tokens; 1 token ≈ 4 caracteres, sin librerías).
- CARTEL, LÍNEAS, FICHA y la lista de documentos entran siempre.
- El texto entra en este orden: primero el pliego principal y las especificaciones técnicas (nombre que empieza
  con «Pliego», o que dice «Especificaciones técnicas», o de ese tipo), después los anexos, en el orden de SICOP.
- Si un documento no cabe entero, entra hasta donde cabe («5 de 7 páginas omitidas por tamaño, desde …») y los
  siguientes quedan «omitido por tamaño».
- Escaneados, con error de lectura, Word / Excel / imágenes y los que no se bajaron **se nombran** en la lista y
  en OMITIDO; nunca se omiten en silencio.
- Base local (2026-10-28): el cartel más grande tiene ≈ 437 000 tokens de PDF; los 3 revisados (corto, con
  anexos, con escaneado) quedaron entre 20 000 y 25 000 tokens, completos.

### Huella

SHA-256 del texto del expediente. El texto no lleva la hora en que se armó: el mismo cartel sin cambios da la
misma huella (en la lección 3 sirve para no pedir dos veces el mismo resumen).

## 2. Lo que NUNCA se envía

Solo se envía información pública de SICOP (y, desde la lección 3, el portafolio de Hermatix). Nunca:

- revisiones, decisiones ni comentarios de los encargados (`reviews`), seguimientos ni asignaciones;
- usuarios, correos, contraseñas ni sesiones (`users`), destinatarios ni avisos;
- historial (`audit_log`), bitácoras ni grabaciones;
- datos de funcionarios de SICOP (Oscar, 27/10: no se guardan; `tender_details` ya los quita);
- la clave de OpenAI ni ninguna otra variable de `.env`.

El expediente solo consulta `tenders`, `institutions`, `imports`, `v_tender_lines` (con `catalog_items`),
`tender_details`, `tender_documents` y `tender_document_text`. Una prueba
(`tests/test_expediente.py`) comprueba que un comentario interno, el nombre y el correo de una encargada no aparecen.

## 3. Pendiente de la lección 1

- Ivania lee completos los 3 expedientes reales y ajusta el orden o el límite si hace falta.
- Word y Excel (por ejemplo «Presupuesto detallado.xlsx», «Lista de insumos.xlsx») hoy no aportan texto; leerlos
  sería una mejora aparte (requiere decidir si se agrega una librería).
- Los PDF escaneados quedan sin texto; un OCR se evaluaría más adelante.
