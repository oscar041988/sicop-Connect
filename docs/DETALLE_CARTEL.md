# Ficha del concurso en SICOP (enriquecimiento, lección 1)

Fuente: consulta pública de concursos, `https://www.sicop.go.cr/app/module/bid/public/tenders`, sin iniciar sesión.
Explorado el 2026-10-27 por Ivania: primero a mano y luego con `scripts/explorar_concursos.py` (ventana visible,
una consulta, sin descargar nada) para el cartel REAL `20261002859` (`2026LD-000031-0018000001`, monitoreo GPS,
Alta, abierto). Informe en `data/exports/exploracion-concursos-20261027-082316/` (fuera de Git).

**Resultado: SICOP no mostró CAPTCHA ni bloqueo.** Todas las peticiones respondieron 200.

Los 3 carteles explorados (2026-10-27, 08:23, 08:29 y 08:32; carpetas `…-082316`, `…-082906`, `…-083226`):

| Cartel | Para qué | Estado en SICOP | Líneas | Documentos |
|---|---|---|---|---|
| `20261002859` GPS | Alta, abierto | En recepción de ofertas | 1 | 5 (3 PDF, 2 xlsx) |
| `20261001258` abarrotes, convenio marco | muchas líneas | **Objetado** | 432, de 100 en 100 (5 páginas) | **49** (28 zip, 17 PDF, 2 docx, 1 xlsm, …) |
| `20261001587` cámaras corporales, Santa Ana | «cerrado» | **En recepción de ofertas**: modificado (`cartelModYn` = Y, versión del 26/10 08:46), cierre **30/10 23:59** | 1 | 7 (5 PDF, 2 xlsx) |

**Hallazgo importante:** `20261001587` está en nuestra base con cierre 23/10 23:59 (dato de los archivos de datos
abiertos, vistos por última vez hoy 27/10 a las 08:00) y por eso el panel lo oculta como vencido. En la ficha,
SICOP dice que se modificó el 26/10 y que el cierre es el **30/10 a las 23:59**. Es un cartel revisado
«Interesa» (13/10). Los datos abiertos no reflejaron la modificación: justo lo que el enriquecimiento corrige.

## 1. Cómo se llega a la ficha

| Paso | Elemento | Selector observado |
|---|---|---|
| Abrir la consulta | página `…/bid/public/tenders` | — |
| Búsqueda avanzada | encabezado plegable | rol `button`, texto «Búsqueda avanzada» |
| Número SICOP | casilla de texto | **etiqueta flotante**, no unida a su casilla (`get_by_label` no la halla): en el HTML va DESPUÉS de su casilla, en el mismo contenedor, y se ve como texto gris dentro de la casilla vacía. La app usa «la casilla del mismo contenedor que la etiqueta». (La primera versión tomaba la casilla siguiente y escribió en «Código de clasificación»: prueba real del 2026-10-27, 09:26) |
| Número de procedimiento | casilla de texto | placeholder «Número de procedimiento» |
| Consultar | botón | rol `button`, texto «Consultar» |
| Abrir el resultado | fila del resultado | el resultado **no muestra el Número SICOP**, sí el número de procedimiento. La app busca la fila con el `instCartelNo` que trajo la búsqueda y su enlace «[LD] …» / «[LY] …» (por confirmar en la prueba real) |

- **Filtro «Estado de concurso»:** viene puesto en «En recepción de ofertas», pero el convenio de abarrotes
  («Objetado») salió igual. La app no lo toca; si un cartel no sale, es FALLO «no encontrado» y se revisa a mano.

- La búsqueda trae por defecto **publicados en los últimos 6 meses** (`regDtFrom`/`pubHasta`) y apertura hasta
  2 meses adelante (`apDesde`/`apHasta`). Un cartel más viejo podría no salir.
- **La ficha no tiene URL propia:** siempre es `…/bid/public/cartel-specification-published`, sin el número.
  Pegarla abre la búsqueda. Hay que repetir la búsqueda por cartel.
- **Los valores de la ficha están dentro de casillas de solo lectura**, no como texto: leer el texto de la
  pantalla da solo las etiquetas (por eso el número buscado «no aparecía»).

## 2. De dónde salen los datos (peticiones que hace la propia página)

Servidor `prod-api.sicop.go.cr`, rutas `…/public/…`, respuestas JSON:

| Petición | Qué trae |
|---|---|
| `POST bid/api/v1/public/epCartel/searchEpCartelsSp` | resultado de la búsqueda; trae el **estado del concurso** (`cartelStatStr`, p. ej. «En recepción de ofertas») |
| `POST bid/api/v1/public/epCartel/findPublishedById` | la ficha (sección 3) |
| `POST bid/api/v1/public/epCartelProd/findByEpCartelId` | líneas (paginadas: `totalElements`) |
| `GET bid/api/v1/public/epCartelFile/getCartelFilesById` | lista de documentos (sección 4) |
| `GET bid/api/v1/public/epCartelSustCriteria…/findAllByCartelId` | criterios de compra pública estratégica |
| `POST bid/api/v1/public/epCartelRoleStaff/findByEpCartelId` y `GET epum/…/umUser/findUserInfoByUserId` | funcionarios: **nombres, correos, teléfonos (datos personales)** |
| `POST epum/…/umInst/findById` | datos de la institución |

## 3. Campos de la ficha

Ejemplo del cartel `20261002859`. «¿Sirve para decidir?» es la propuesta; la última columna es la decisión de Oscar
(2026-10-27, comunicada por Ivania). Los campos con ☑ se guardan en columnas propias en la lección 2.

| Campo en pantalla | Campo JSON | Ejemplo | ¿Sirve para decidir? | Oscar |
|---|---|---|---|---|
| Estado del concurso | `cartelStatStr` (búsqueda) | En recepción de ofertas | Sí: pasa «por verificar» a un estado real | ☑ sí |
| Número de SICOP | `cartelNo` | 20261002859 | Clave de unión (texto) | ☑ sí |
| Número de procedimiento | `instCartelNo` | 2026LD-000031-0018000001 | Ya lo tenemos | ☑ sí |
| Versión del pliego | `cartelSeq` · `cartelVersion` · `cartelModYn` | 00 · 21102026153640 · N | Sí: detecta modificaciones | ☑ sí |
| Descripción | `cartelNm` | Servicio de Monitoreo y Localización Satelital… | Ya lo tenemos | ☑ sí |
| Tipo de procedimiento | `proceTypeNm` | LICITACIÓN REDUCIDA | Ya lo tenemos | ☑ sí |
| Tipo de modalidad | `proceTypeDetailNm` | Según demanda | Sí: cambia cómo leer el monto | ☑ sí |
| Clasificación del objeto | `ppsTypeNm` | BIENES/SERVICIOS | Poco | ✗ no |
| Tipo de recepción de ofertas | `biddocTypeNm` · `onlineYnNm` | Común - firma digital de XML · En línea | Sí (requisito para ofertar) | ☑ sí |
| Inicio / cierre de recepción | `biddocStartDt` / `biddocEndDt` | 2026-10-21T17:00 / 2026-10-28T09:00 | Sí: confirma el plazo (coincide con la base) | ☑ sí |
| Apertura de ofertas | `openbidDt` | 2026-10-28T09:00 | Sí | ☑ sí |
| Límite de aclaraciones | `explainRcvEndDt` | 2026-10-22T23:59 | Sí: fecha para preguntar | ☑ sí |
| Monto total estimado | `cartelBudget` | 291782.16 | Sí (moneda por confirmar: hay `cartelBudgetUsd` aparte) | ☑ sí |
| Garantías, pago adelantado, multas, reajuste | secciones 6 y 8, `amtReadjustYn`… | — | Sí (riesgo del contrato) | ☑ sí |
| Criterios sociales, ambientales… | `epCartelSustCriteria` | 2 criterios | Poco | ☑ sí |
| Funcionarios encargados | `epCartelRoleStaff`, `umUser` | (no se copia aquí) | Ver sección 5 | ✗ no |
| Líneas | `prodId`, `prodNm`, `prodQty`, `prodUnit`, `prodPrc`, `currencyType` | 8311160292034727 · 1 NA · 4052.53 CRC | Ya las tenemos; sirve para comparar | ☑ sí |

Secciones de la ficha en pantalla: 1 Información general · 2 Funcionarios · 3 Criterios de compra pública
estratégica · 4 Aclaración y recurso · 5 Pago para PYMES · 6 Garantías · 7 Oferta · 8 Condiciones de contrato ·
9 Bien, servicio u obra · 10 Sistema de evaluación · 11 Documentos del pliego · 12 Procesos por partida ·
13 Recurso para todas las partidas.

Cuidados de datos (lección 2):
- Montos: en el JSON vienen como número decimal (`291782.16`); leerlos con `Decimal` directamente del texto del
  JSON, nunca como `float`, y siempre con su moneda.
- Códigos (`prodId`, 16 dígitos) y números SICOP: como texto.
- Fechas: la búsqueda usa `21/10/2026 17:00` y la ficha `2026-10-21T17:00:00`, sin zona horaria (hora de Costa Rica).
- Líneas: la página solo carga la primera página (100). Las líneas ya vienen completas de los datos abiertos, así
  que de la ficha basta `totalElements` para comparar; no se recorren las páginas (menos consultas).
- `cartelBudget` puede venir vacío (convenio marco).
- Versión: `cartelModYn` = Y y un `cartelVersion` nuevo indican que el pliego se modificó; `cartelSeq` siguió en
  «00» con la modificación.

## 4. Documentos

Lista en `getCartelFilesById` y en la tabla «11. Documento del pliego de condiciones». El cartel tenía 5:

| N.º | Tipo de documento (`fileTypeNm`) | Archivo (`clientFileNm`) | MB |
|---|---|---|---|
| 1 | Documentos del Pliego de condiciones | Código de conducta del Conglomerado… .pdf | 0.34 |
| 2 | Documentos del Pliego de condiciones | Ejemplo Cuadro para Estructura del Precio Final.xlsx | 0.46 |
| 3 | Documentos del Pliego de condiciones | Formulario Conozca a su Proveedor… .xlsx | 0.05 |
| 4 | Documentos del Pliego de condiciones | Instructivo de Conducta del Proveedor.pdf | 0.22 |
| 5 | Especificaciones técnicas | 2026-10-21 Final…Espec.Técn.yRequis.Plie.Condic.GPS.pdf | 0.9 |

- **No todos son PDF:** en los 3 carteles hay `.xlsx`, `.xlsm`, `.docx` y muchos `.zip` (28 de 49 en el convenio
  marco). La lección 3 debe decidir qué hacer con ellos (guardarlos sin extraer texto, abrir los ZIP con las
  mismas reglas que `zip_pliegos`, o extraer también de Word y Excel). Un `.xlsm` trae macros: se guarda como
  dato y nunca se abre.
- Volumen: un convenio marco puede tener ~50 documentos y ~45 MB; conviene un tope por cartel además de
  `DOCUMENT_MAX_MB` por archivo.
- El documento útil para las reglas es el de «Especificaciones técnicas».
- El nombre del archivo es texto de una celda, no un enlace: cómo se descarga queda para la lección 3.

## 5. Recomendación de acceso

**Usar la interfaz con Playwright (como una persona) y leer las respuestas JSON que recibe la propia página.**

- **Leer la pantalla:** no conviene. Los valores están en casillas de solo lectura y se rompe con cualquier
  cambio de diseño.
- **Abrir la URL de la ficha directamente:** no se puede. La ficha no tiene URL propia.
- **Llamar a `prod-api.sicop.go.cr` directamente, sin navegador:** no. SICOP respondió el 26/10 que no ofrece API
  ni integración para terceros (`DECISION_OBTENCION.md` §8), y en la obtención ya se decidió usar la interfaz y
  no la API interna (`ACCESO_SICOP.md`, 2A).
- **Escuchar el JSON dentro del navegador** (`page.on("response")`) no hace ninguna petición extra a SICOP: son las
  mismas que hace la página para una persona. Da datos ordenados (fechas, montos, versión, documentos) y la
  copia fiel de la lección 2 es ese JSON.
- Datos personales: **no se guardan** las respuestas de funcionarios (`epCartelRoleStaff`, `umUser`: nombres,
  correos, teléfonos), ni en columnas ni en la copia fiel (decisión de Oscar, 2026-10-27).

## 6. Pendiente

- [x] Explorar los otros 2 carteles (2026-10-27, Ivania): sin bloqueo; resultados arriba.
- [x] Tipos de documento (Oscar, 2026-10-27): **se guardan todos** (PDF, ZIP, Word, Excel). Ninguno se abre con
      otro programa; `.xlsm` y similares, solo guardados. Falta el tope por cartel (lección 3).
- [ ] Confirmar la casilla del Número SICOP y cómo se abre el resultado (pasos que se hicieron a mano; lección 2).
- [x] Campos útiles marcados por Oscar (sección 3) y datos de funcionarios: no se guardan (2026-10-27).
- [x] Prueba real de la lección 2 (2026-10-27, Ivania): el «Monto total estimado» está en **colones** en la
      pantalla de SICOP, como lo guarda la app.

## 7. Dónde queda cada campo (lección 2)

`python -m app.cli enrich --nro N` guarda una fila por versión en `tender_details` (migración 0018,
`app/sources/sicop_tender_detail.py`):

| Columna | De dónde sale |
|---|---|
| `copia_fiel` | las respuestas `busqueda` (el resultado), `ficha`, `lineas` (1.ª página), `documentos`, `criterios` e `impactos`, tal como llegaron, sin campos de personas |
| `campos_quitados` | los nombres de los campos de personas que se quitaron |
| `content_hash` | SHA-256 de la copia fiel sin lo que cambia solo con el reloj (`startPassYn`, `endPassYn`, `openbidPassYn`, `…EndYn`, `isDateTrue`, paginación) |
| `estado_concurso` | `cartelStatStr` |
| `version_pliego` · `secuencia` · `modificado` | `cartelVersion` · `cartelSeq` · `cartelModYn` |
| `numero_procedimiento` · `descripcion` · `tipo_procedimiento` · `tipo_modalidad` | `instCartelNo` · `cartelNm` · `proceTypeNm` · `proceTypeDetailNm` |
| `tipo_recepcion` | `biddocTypeNm` · `onlineYnNm` |
| `inicio_recepcion` · `cierre_recepcion` · `apertura` · `limite_aclaraciones` | `biddocStartDt` · `biddocEndDt` · `openbidDt` · `explainRcvEndDt`, con zona de Costa Rica |
| `monto_estimado` + `moneda_monto` · `monto_estimado_usd` | `cartelBudget` (Decimal, CRC) · `cartelBudgetUsd` |
| `garantias` | garantías de participación, cumplimiento y colateral, pago adelantado, multa (`fine`, `fineArticle`), reajuste y vigencia/prórroga del contrato, con sus nombres de SICOP |
| `criterios` | `criterioCont` e `impactDesc` |
| `lineas_total` | `totalElements` de las líneas |
| `documentos` | `docFileSeqno`, `fileTypeNm`, `docNm`, `clientFileNm`, `fileSizeMb`, `serverFileNm`, `fileServerPath` (para la lección 3) |
