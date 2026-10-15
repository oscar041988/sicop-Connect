# Acceso a SICOP — registro de observaciones

Registro manual de lo observado en el módulo de datos abiertos de SICOP (guía, sección 16.2).

**Estado del acceso: SIN VERIFICAR.**
No se ha verificado ninguna API pública documentada. Este documento no declara ninguna API,
dirección interna ni llamada del navegador; solo registra lo que una persona observa al usar el
portal en un navegador normal.

## Reglas al registrar

- **No** anotar aquí códigos de confirmación, enlaces de descarga ni datos del buzón (este archivo va a Git).
- Guardar el archivo descargado **sin abrirlo ni volverlo a guardar en Excel** (Excel puede convertir
  identificadores de 24 dígitos a notación científica y destruirlos).
- Los archivos originales se guardan en `data/raw/` (fuera de Git); aquí solo se anota su nombre y hash.
- Una sola descarga no demuestra estabilidad: repetir la solicitud otro día.
- Solicitar carteles y sus líneas (oportunidades nuevas), no solo contratos adjudicados.
- Usar una ventana de fechas pequeña (p. ej. últimos 30 días) **sin filtrar por institución**
  (el filtro de la guía del ICD es un ejemplo propio de esa entidad).
- Distinguir siempre: dato **observado** / **supuesto** / **pendiente de verificar**.

## Referencias disponibles (`docs/referencias/`)

| Archivo | Qué es | Fuente | Fecha de obtención |
|---|---|---|---|
| `Diccionario_de_datos_reporte_de_contratos_de_Datos_abiertos.pdf` | «Diccionario de datos módulo descarga de datos SICOP»: columnas de los reportes 1 a 11 (describe datos, no una API). No indica formatos de fecha, zona horaria ni significado de los códigos de tipo de procedimiento | Oficial de SICOP, entregado por Oscar | 2026-10-07 |
| `Diagrama_ERD_SICOP.pdf` | Diagrama entidad-relación de SICOP: tablas y claves (`NRO_SICOP`, `NRO_SEQ_SICOP`, etc.) (describe datos, no una API) | Oficial de SICOP, entregado por Oscar | 2026-10-07 |
| _(falta, opcional)_ guía del ICD | Procedimiento de descarga descrito por el ICD | — | — |

Los CSV reales del ZIP (2026-10-07) se movieron a `data/raw/` (fuera de Git) el mismo día;
aquí queda solo su nombre y hash (ver «Registro de descargas»). Hash verificado igual tras moverlos.

Reportes del diccionario que interesan (guía 16.3), pendientes de confirmar en el portal:

| N.º en diccionario | Reporte | Uso | ¿Visto en el portal? |
|---|---|---|---|
| 2 | Detalle carteles | Identificar la compra y su plazo | Sí: «Detalle pliego de condiciones». Descargado (CSV de carteles del ZIP) |
| 2.1 | Detalle líneas de carteles | Qué se compra y estimación por línea | No aparece como reporte aparte; las líneas vinieron en el mismo ZIP de «Detalle pliego de condiciones» |
| 10.2 | Códigos de identificación | Nombre del bien o servicio | Probable: «Catálogo de bienes y servicios» (por confirmar). No descargado; por ahora no se descargará |
| 11 | Instituciones compradoras | Mostrar el comprador | Sí: «Instituciones compradoras». No descargado; por ahora no se descargará |
| 1 | Solicitud de contratación (complementario) | Complementar cuando la relación se compruebe | Sí: «Solicitud de contratación». No descargado; por ahora no se descargará |
| — | Adjudicaciones / contratos (si existe) | Para A2 | Sí: «Adjudicaciones en firme» y «Contratos». No descargados; por ahora no se descargarán |

## Procedimiento observado en el portal

Registrado por Ivania el 2026-10-07.

- Fecha de la visita: 2026-10-06 (Ivania) y 2026-10-07 (Oscar, Anabelle e Ivania).
- Personas presentes: ver fecha de la visita.
- Navegador usado: Google Chrome.
- Reportes disponibles (nombres tal como aparecen): Solicitud de contratación · Detalle pliego de
  condiciones · Aclaraciones · Recursos · Ofertas · Adjudicaciones en firme · Contratos ·
  Ordenes de pedido · Instituciones compradoras · Proveedores · Catálogo de bienes y servicios.
- Filtros disponibles por reporte: Búsqueda de institución · Fecha de trámite · Tipo de procedimiento
  (anotados en general; falta confirmar si todos los reportes ofrecen los mismos).
- Formatos de descarga ofrecidos: Excel · CSV · JSON. (Se eligió CSV; el portal lo entregó dentro de un ZIP.)
- Pasos para solicitar una descarga (en palabras propias, sin enlaces privados):
  1. Entrar al apartado del reporte deseado.
  2. En la sección «Formato de descarga», hacer clic en el icono del tipo de archivo.
  3. Una ventana modal pide un correo electrónico; se ingresa el buzón empresarial.
  4. Llega al correo, en ≈ 1 minuto, un código de 6 caracteres (números y letras).
  5. Se digita el código en la ventana; el sistema avisa que el reporte se está generando.
  6. Llega al correo el enlace de descarga en ≈ 1 minuto más.

## Comportamiento de la solicitud

| Pregunta | 2026-10-06 (Ivania) | 2026-10-07 (Oscar, Anabelle, Ivania) |
|---|---|---|
| ¿Qué se pidió? | 4 descargas: Ofertas, Solicitud de contratación y Detalle pliego de condiciones, en JSON y CSV | 5 descargas: Solicitud de contratación y Detalle pliego de condiciones |
| ¿Cada solicitud exige un código nuevo? | Sí | Sí |
| ¿Cuánto demora el correo con el código? | ≈ 1 minuto | ≈ 1 minuto |
| ¿Cuánto demora el correo con el enlace? | ≈ 1 minuto después de digitar el código | ≈ 1 minuto después de digitar el código |
| ¿El enlace funcionó al abrirlo? | Sí | Sí |
| ¿Vence el enlace? ¿Tras cuánto tiempo? | Enlace pedido 15:58 → **vencido** al probarlo el 2026-10-07 08:30 (≈ 16,5 h) | Enlace pedido 08:43 → **funcionó** a las 11:43 (3 h) |
| ¿Hay límite de filas o de periodo? | No se observó | No se observó |
| ¿Mensajes de error observados? | Ninguno | Ninguno |

Conclusión provisional: el enlace dura **al menos 3 h** y **menos de ≈ 16,5 h**. El plazo exacto no
se conoce; para acotarlo, probar un enlace a distintas horas (p. ej. 6 h, 9 h, 12 h).
El comportamiento fue igual los dos días.

## Registro de descargas

Una fila por archivo obtenido.

| Fecha y hora de obtención (CR) | Reporte | Filtros (fechas, institución, otros) | Periodo cubierto | Formato | Nombre del archivo en `data/raw/` | SHA-256 | Filas | Observaciones |
|---|---|---|---|---|---|---|---|---|
| 2026-10-07 — solicitud de las 08:55; descarga antes de las 10:00 (hora de los archivos en disco) | 2 · «Detalle pliego de condiciones» | Ninguno, a propósito | Publicación 2026-07-07 06:14 → 2026-10-07 08:51 (≈ 3 meses) | CSV dentro de ZIP | `Detalle de pliegos de condiciones.csv` | `5d850ce0d9dfc31c3f4765a146b8f3c7ea9a453d9986a4ddd346c5521b52afcc` | 10 339 | Sin notación científica ni filas rotas |
| 2026-10-07 — mismo enlace | 2.1 · mismo ZIP | Ninguno, a propósito | Mismos carteles | CSV dentro de ZIP | `Detalles lineas.csv` | `99a5b8f8bd1e15fa3a668be388e61ec4e5b15e2033f1e95c8c118b230f83a731` | 73 991 | Códigos de 16 dígitos intactos |
| 2026-10-06 15:51 (hora en disco) | Ofertas | Ninguno | — | JSON | `Reporte de ofertas.json` | `3da516a25f9f9acf5e82426bede4b77bb4d22a34c80ba2512b5e0853b2e33b00` | 0 | Listas `Ofertas` y `Lineas de Ofertas` vacías |
| 2026-10-06 15:53 (hora en disco) | Ofertas | Ninguno | — | CSV dentro de ZIP (generado 15:12) | `Reporte de ofertas.zip` | `d3bece89e4dc073654ac905fd330e6d8afd2f7880bc462180975cec9285d5d4b` | 0 | Solo encabezados (2 CSV) |
| 2026-10-06 15:59 (hora en disco) | 1 · Solicitud de contratación | Ninguno | Trámite hasta 2026-10-06 | CSV dentro de ZIP (generado 15:57) | `Reporte de solicitud de contratación.zip` | `f4a4899786fc574cbfcd785c73b1ccff881bec7c454633cb502bc330b4a24401` | 8 930 + 51 405 líneas | |
| 2026-10-07 08:43 (hora en disco) | 1 · Solicitud de contratación | Ninguno | Trámite 2026-07-07 06:38 → 2026-10-06 15:48 | CSV dentro de ZIP (generado 08:42) | `Reporte de solicitud de contratación (1).zip` | `a7ae793cfbd4559f11c96b1dcf5abcad4e9f15369217f11d75357419209217d0` | 8 856 + 51 518 líneas | Usado para el mapeo |
| 2026-10-07 08:48 (hora en disco) | 1 · Solicitud de contratación | Ninguno | Igual que (1) | CSV dentro de ZIP (generado 08:46) | `Reporte de solicitud de contratación (2).zip` | `8cd268595a8fb9a244f27c3aa2e9b8e51c7a2b7a15aee3fd478ba764cbf4a3b4` | 8 856 + 51 518 líneas | ZIP distinto, **CSV idénticos** a (1) |
| 2026-10-07 10:49 (hora en disco) | 1 · Solicitud de contratación | Ninguno | Igual que (1) | CSV dentro de ZIP (generado 08:42) | `Reporte de solicitud de contratación (3).zip` | `a7ae…17d0` (= (1)) | igual que (1) | **ZIP idéntico** a (1) |
| 2026-10-07 11:21 (hora en disco) | 1 · Solicitud de contratación | Ninguno | Igual que (1) | CSV dentro de ZIP (generado 08:42) | `Reporte de solicitud de contratación (4).zip` | `a7ae…17d0` (= (1)) | igual que (1) | **ZIP idéntico** a (1) |
| 2026-10-08 08:41 (hora en disco) | 11 · Instituciones compradoras | Ninguno | Catálogo vigente (no es por periodo) | CSV | `Reporte de instituciones compradoras.csv` | `c0c7c86abe020bd36249f8f90cf8a4df11208ce790644f3518b93992605de88a` | 691 | Cédula de 10 dígitos como texto |
| 2026-10-08 08:59 (hora en disco) | 10.2 · Catálogo de bienes y servicios | Código de clasificación `83111602` (GPS/flotas) | — | 3 CSV dentro de ZIP (generados 08:58) | `Reporte de catálogo de bienes y servicios.zip` | `9cc4b81c4a8a42d061308e5bd84b983831a7dfd47cfb724118decdb947cd8c25` | 1 clasificación + 31 identificación + 57 productos | «Servicios de sistemas de comunicación por satélite o terrestre» |
| 2026-10-08 09:03 (hora en disco) | 10.2 · Catálogo de bienes y servicios | Código de clasificación `41112301` (IoT/frío) | — | 3 CSV dentro de ZIP (generados 09:01) | `Reporte de catálogo de bienes y servicios (1).zip` | `50578babd30cbb6961b4029c75232cae544d2c76ab95d726d98ac22ba4958f1a` | 1 + 39 + 219 | «Higrómetros» |
| 2026-10-08 09:16 (hora en disco) | 10.2 · Catálogo de bienes y servicios | Código de clasificación `45121515` (BodyCams) | — | 3 CSV dentro de ZIP (generados 09:06) | `Reporte de catálogo de bienes y servicios (2).zip` | `b85302a233e2888f011f2b59a348bed330302175109ebdb0e3bd9773985c8d1e` | 1 + 30 + 132 | «Videocámaras portátiles» |
| 2026-10-09 13:49 (hora en disco) | 2 · «Detalle pliego de condiciones» | Ninguno | Publicación 2026-07-09 07:51 → 2026-10-09 13:44 (≈ 3 meses) | CSV dentro de ZIP (generados 13:48) | `Reporte de detalle pliego de condiciones (1).zip` → `Detalle de pliegos de condiciones.csv` | ZIP `ce5ae36626bf233a4dad0addfa1d1fa52ac3c5f81679365c9e6d361c02b90716` · CSV `6a5399715cc0c603d3891534ef6807422e7b624fb153ea3faaab1aa4a7c69445` | 10 587 | Mismas 15 columnas. Importación #7: 460 nuevos, 119 actualizados, 0 rechazados. 2 casos de inicio de recepción > 1 h antes de la publicación |
| 2026-10-09 — mismo ZIP | 2.1 · mismo ZIP | Ninguno | Mismos carteles | CSV dentro de ZIP | `Detalles lineas.csv` | `f3b233cdf9ffb718a7af55aa2f3785c9e1161dcb88b357c2c58af660b14721b8` | 74 824 | Importación #8: 2 608 nuevas, 4 actualizadas, 0 huérfanas. Primera descarga con oportunidades abiertas |

Reporte 10.2: el portal exige un código de clasificación completo de 8 dígitos y no acepta
códigos parciales (Ivania, 2026-10-08). Cada ZIP trae `Codigos Clasificacion.csv`,
`Codigos Identificacion.csv` y `Codigos Productos.csv`. Las filas se contaron como registros CSV;
`Codigos Productos.csv` tiene más líneas físicas que registros, posiblemente por saltos de línea
dentro de campos (sin verificar).

Hash de los dos primeros: calculado sobre los CSV descomprimidos. Resto: sobre el archivo tal como
se descargó. «Hora en disco» = fecha de modificación conservada al copiar desde Descargas; se toma
como hora aproximada de descarga (*supuesto*). ZIP original de pliegos: «Reporte de detalle pliego
de condiciones» (no está en `data/raw/`).

Lo que muestran estos archivos (observado):

- **El reporte se genera al pedirlo, no al abrir el enlace.** (3) y (4) se bajaron a las 10:49 y 11:21
  pero son idénticos byte a byte a (1), generado a las 08:42. Un enlace reabierto entrega el mismo archivo.
- Dos solicitudes distintas (08:42 y 08:46) dieron los mismos datos: el portal no se actualizó en esos minutos.
- La descarga del 7/10 08:42 no trae trámites del 7/10 (el último es del 6/10 15:48). *Supuesto*:
  los datos de Solicitud de contratación se actualizan con algún desfase. Sin confirmar.
- Entre el 6/10 y el 7/10 el reporte pasó de 8 930 a 8 856 solicitudes: el periodo se desplaza (≈ 3 meses).
- **Ofertas llegó vacío** en JSON y CSV. No se usaron filtros, así que no es por eso. Causa desconocida (¿falla del portal?, ¿reporte sin
  datos públicos en ese periodo?). Repetir la descarga otro día; si sigue vacío, candidata a pregunta para soporte.

Observaciones a verificar:

- **Revisión en el portal, 2026-10-08 (Ivania)**, de dos carteles del archivo de pliegos del 2026-10-07:
  - `20260903574` (`2026LD-000270-0006300001`, Tecnológico de Costa Rica, implementos deportivos): aparece.
    Publicación 01/10/2026 14:45 y apertura 08/10/2026 13:01: **coinciden con el CSV**. El portal no mostró
    la fecha de inicio de recepción (CSV: 14:32), así que esa fecha no se pudo contrastar.
  - `20260802713` (`2026LE-000014-0020600005`, Banco Popular): el portal responde que **los datos consultados
    no existen**, buscando por Número SICOP y por número de procedimiento. Sí está en el archivo de datos abiertos
    (línea 5099, con inicio de recepción 21/08/2025). Causa desconocida (no se supone ninguna). Candidata a
    pregunta para soporte, si Hermatix lo decide.
- **Revisión en el portal de los 31 candidatos del golden set, 2026-10-08 (Ivania):** solo aparece `20260903574`
  (TEC). Ese es el único de los 31 cuya recepción no había cerrado (cierre 08/10/2026 13:00); los otros 30
  cerraron entre julio y el 07/10/2026. *Hipótesis* (sin confirmar): la búsqueda del portal solo muestra
  carteles con la recepción abierta.
- **Prueba de la hipótesis, 2026-10-08 10:54 (Ivania):** `20260903650` (INDER) y `20261000334` (UCR), con cierre
  12/10/2026, **aparecen**. En total, 3 de 3 carteles abiertos aparecen y 0 de 30 cerrados (más el del Banco
  Popular, también cerrado). Hipótesis muy respaldada, pero falta una prueba: buscar el del TEC
  (`20260903574`) **después de las 13:00** del 08/10/2026, cuando cierra. Si ya no aparece, queda confirmada.
- **Confirmación, 2026-10-08 después de las 13:00 (Ivania):** el cartel del TEC (`20260903574`), que a las 10:54
  sí aparecía, **ya no aparece** tras el cierre de su recepción (13:00). **Conclusión (observada):** la búsqueda
  del portal muestra un cartel solo mientras su recepción está abierta. Consecuencias:
  - Los carteles cerrados solo se pueden consultar en los archivos de datos abiertos, por eso cada descarga se conserva.
  - Para Hermatix, una oportunidad es visible en el portal solo hasta el cierre: los avisos deben llegar antes.
  - El golden set no se puede revisar en el portal una vez cerrados sus carteles (5 provisionales sin pliego).
  No se probó si alguna otra sección del portal sí muestra carteles cerrados.

- Observado: sin filtros (decisión de Ivania), el portal entregó ≈ 3 meses de publicaciones.
  Solicitud de contratación, también sin filtros, cubre 2026-07-07 → 2026-10-06: mismo patrón.
  *Supuesto* (más respaldado): sin filtros, el portal entrega ≈ 3 meses. Confirmar con otro reporte.
- Resuelto: el ZIP salió de la solicitud de las 08:55 y el último cartel publicado es de las 08:51.
  Es coherente con que las fechas del archivo estén en hora de Costa Rica (no está demostrado).
  En las próximas descargas: anotar hora de solicitud, hora de apertura del enlace y nombre del ZIP.
- Las otras descargas del 6 y 7/10 se copiaron a `data/raw/` y están registradas arriba.
  No aparece la descarga de «Detalle pliego de condiciones» del 6/10 (de las 4 de ese día solo hay 3).

Formato observado en ambos archivos: UTF-8 con BOM, separador `;`, fin de línea CRLF, fechas
`dd/mm/aaaa hh:mm:ss` (sin zona horaria indicada), decimales con punto y sin separador de miles.

Para cada archivo, copiar los encabezados **exactamente** como vienen (orden, mayúsculas, tildes)
y pasarlos a `docs/MAPEO_DATOS.md`.

```text
Reporte: 2 («Detalle pliego de condiciones») — Detalle de pliegos de condiciones.csv
Encabezados (en orden):
Número SICOP;Cédula;Fecha Publicación;Numero de procedimiento;Cod Unidad Compra;Nombre Unidad Compra;Tipo de procedimiento;Modalidad Procedimiento;Excepción CD;Descripción;Pago Adelantado Pymes;Fecha Invitación;Fecha Inicio Recepción;Fecha Cierre Recepción;Fecha Apertura
```

```text
Reporte: 2.1 (mismo ZIP) — Detalles lineas.csv
Encabezados (en orden):
Número SICOP;Numero de linea;Numero partida;Cantidad;Precio Unitario Estimado;Moneda;Tipo Cambio USD;Código identificación
```

Cálculo del hash en PowerShell (no modifica el archivo):

```powershell
Get-FileHash data\raw\NOMBRE_DEL_ARCHIVO -Algorithm SHA256
```

## Preguntas para soporte de SICOP

Se registran aquí; **Hermatix decide si las envía**. Claude no envía mensajes.

| Fecha | Pregunta | ¿Enviada? (quién, cuándo) | Respuesta |
|---|---|---|---|
| | | | |

Decisión 2026-10-07 (Ivania): ninguna pregunta por ahora. Las dudas abiertas (Ofertas vacío,
duración del enlace, zona horaria, periodo sin filtros, frecuencia de actualización, códigos de
tipo de procedimiento) quedan en «Observaciones a verificar» y en `MAPEO_DATOS.md`; revisar
primero el diccionario de datos antes de convertir alguna en pregunta.

## Conclusión sobre el modo de obtención

- Modo actual: manual (`SOURCE_MODE=manual`).
- ¿Hay evidencia para algo más que manual/asistido? (solo si A1 lo valida):
- Decisión, responsable y fecha:
