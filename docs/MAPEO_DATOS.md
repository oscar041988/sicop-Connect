# Mapeo de datos — columna del reporte → campo interno

Plantilla para registrar cómo cada columna de los reportes de SICOP (guía, sección 16.3) se
traduce a un campo interno de la app.

**Estado: PARCIAL.** Reportes 2, 2.1 y 1 contrastados con archivos reales del 2026-10-07
(ver `docs/ACCESO_SICOP.md`). Ofertas: archivo sin filas. Reportes 10.2 (3 clasificaciones) y 11 contrastados con archivos reales
del 2026-10-08. Adjudicaciones en firme (6, 6.1 y 6.2) contrastadas con el archivo real del 2026-10-22.
La columna "Diccionario" usa los nombres del **diccionario oficial de SICOP**
(`docs/referencias/Diccionario_de_datos_reporte_de_contratos_de_Datos_abiertos.pdf`, revisado 2026-10-07);
la guía 16.3 solo lista un subconjunto. Los encabezados reales **sí son distintos** (tildes,
mayúsculas, espacios). En "Verificado", `sí` = el encabezado existe y los valores tienen la forma
esperada; lo marcado como *supuesto* sigue por confirmar. El archivo original siempre se conserva.

Cómo llenar cada tabla:

- **Encabezado real**: copiado exactamente del archivo (ver `docs/ACCESO_SICOP.md`). Si no viene: `NO VIENE`.
- **Campo interno**: nombre propuesto en la app (tablas de la guía 16.3). Es propuesta nuestra,
  no un campo de SICOP; se confirma al escribir el importador.
- **Tipo**: `texto`, `decimal`, `fecha`, `fecha-hora`, `entero`.
- **Verificado**: `sí` solo después de comprobarlo con un archivo real (anotar archivo y fecha).

## Reglas que aplican a todo el mapeo

- Identificadores siempre como **texto** (8, 16 y 24 dígitos; conservar ceros iniciales).
  Según el diccionario oficial: clasificación = 8 dígitos (UNSPSC); identificación = 16 dígitos,
  cuyos 8 primeros son la clasificación; producto = 24 dígitos, cuyos 16 primeros son la identificación.
  Un código truncado o en notación científica no se reconstruye: se registra y se pide otro archivo.
- Uniones solo por claves verificadas: `NRO_SICOP` (y secuencia), código de catálogo, cédula de institución.
  Nunca por parecido del título.
- Dinero como **decimal con su moneda**. Cantidad × precio unitario es una estimación por línea,
  no el presupuesto ni el monto adjudicado.
- Fechas: anotar la zona horaria de la fuente; la app muestra hora de Costa Rica.
  **Decisión 2026-10-07 (Ivania), confirmada el 2026-10-09:** el archivo no indica zona; es hora de Costa Rica
  y se guarda en ISO 8601 con `-06:00` (p. ej. `2026-10-07T08:51:08-06:00`). El texto original queda en `raw_snapshots`.
  Evidencia: (1) SICOP es una plataforma exclusiva de Costa Rica y usa solo su hora en reportes y carteles
  (Ivania, 2026-10-09); (2) la solicitud de las 08:55 trajo carteles hasta las 08:51; (3) las horas de cierre más
  comunes en 10 339 carteles son 10:00 (1 916), 23:59 (1 265), 09:00 (1 101) y 08:00 (1 030): horas de oficina
  locales, que en UTC no tendrían sentido.
  Costa Rica no tiene horario de verano, por eso el desfase fijo es exacto.
  Una fecha de cierre futura no prueba que el concurso siga activo: sin estado conocido → «estado por verificar».
  `ESTADO` del reporte de ofertas es de la oferta, no del procedimiento.
- Si viene `NRO_SEQ_SICOP` (el ERD oficial lo pone en carteles, líneas, ofertas, adjudicaciones…;
  el diccionario no lo lista y los archivos reales no lo traen), se conserva. Si no, se guardan instantáneas con
  hash de contenido (detecta cambios, pero no es una secuencia oficial).
  **Duda cerrada 2026-10-09 (Ivania):** no viene en los archivos; las instantáneas con hash cumplen la función.
  La columna `tenders.nro_seq_sicop` queda lista por si algún día aparece.

## Reporte 2 · Detalle carteles → `tenders`

Importador: `python -m app.cli import --path ARCHIVO --report carteles --origen real|sintetico|simulado`
(`app/importers/carteles.py`).

- **Fila rechazada** (con línea y motivo): número de columnas distinto al encabezado; cualquier celda en
  notación científica (código dañado por Excel); `Número SICOP` vacío, no numérico o repetido en el
  archivo; fecha no vacía con formato distinto de `dd/mm/aaaa hh:mm:ss`.
- **Advertencia** (la fila se acepta): sin fechas de recepción; inicio de recepción **más de 1 hora** antes de la
  publicación (decisión 2026-10-08, Ivania: 107 de los 108 casos reales eran de 0 a 14 minutos, ruido normal).
- **Archivo rechazado** (no se escribe nada): falta algún encabezado de la tabla de abajo.
- Las columnas marcadas «después» no van a `tenders`, pero quedan completas en `raw_snapshots.payload`.

Archivo de referencia: `Detalle de pliegos de condiciones.csv` (10 339 filas) · Fecha de obtención: 2026-10-07

| Diccionario | Encabezado real | Campo interno (propuesto) | Tipo | Regla / nota | Verificado |
|---|---|---|---|---|---|
| NRO_SICOP | `Número SICOP` | `nro_sicop` | texto | 11 dígitos en este archivo; único por fila | sí |
| NRO_SEQ_SICOP (si viene) | NO VIENE | `nro_seq_sicop` | texto | Sin secuencia: usar instantáneas con hash de contenido | sí |
| NRO_PROCEDIMIENTO | `Numero de procedimiento` (sin tilde) | `nro_procedimiento` | texto | Forma `2026XX-000000-0000000000`; único por fila | sí |
| CEDULA_INSTITUCION | `Cédula` | `institution_cedula` | texto | 10 dígitos, 315 distintas. Diccionario: cédula jurídica de la institución que tramitó la compra | sí |
| DESCRIPCION | `Descripción` | `descripcion` | texto | 8 961 filas traen espacios no separables (U+00A0): normalizar para buscar, guardar el original | sí |
| FECHA_PUBLICACION | `Fecha Publicación` | `fecha_publicacion` | fecha-hora | `dd/mm/aaaa hh:mm:ss`; zona de la fuente: no indicada | sí (forma) |
| FECHA_INICIO_RECEPCION | `Fecha Inicio Recepción` | `fecha_inicio_recepcion` | fecha-hora | 487 vacías; 108 anteriores a la publicación: 107 por 0–14 min (normal) y 1 por un año (`20260802713`, línea 5099: inicio 21/08/2025, publicación 21/08/2026). Portal, 2026-10-08 (Ivania): ese cartel **no aparece** (por Número SICOP ni por procedimiento); no se pudo verificar | sí (forma) |
| FECHA_CIERRE_RECEPCION | `Fecha Cierre Recepción` | `fecha_cierre_recepcion` | fecha-hora | 487 vacías; no prueba que siga activo | sí (forma) |

## Reporte 2.1 · Detalle líneas de carteles → `tender_lines`

Importador: `python -m app.cli import --path ARCHIVO --report lineas --origen …` (`app/importers/lineas.py`).
Importar antes los carteles (y el catálogo, si lo hay).

- **Fila rechazada**: columnas o notación científica (igual que carteles); `Número SICOP` o `Numero de linea`
  vacíos o no numéricos; `Código identificación` que no tenga exactamente 16 dígitos; `Cantidad` o
  `Precio Unitario Estimado` que no sean número con punto decimal; `Moneda` que no sea de 3 letras;
  (`Número SICOP`, `Numero de linea`) repetido en el archivo.
- **Advertencia** (la fila se acepta): línea huérfana (su cartel no está importado: queda solo en
  `raw_snapshots`, no en `tender_lines`); código sin catálogo (clasificación no descargada, o la
  clasificación sí está pero el código no); cantidad o precio en cero.
- `estimado_linea` = cantidad × precio unitario en Decimal, guardado como texto exacto y en la moneda de la
  línea. Los totales se calculan por moneda (`app/dinero.py`); CRC y USD nunca se suman.
- La vista `v_tender_lines` marca cada línea con `estado_catalogo`: `en_catalogo`,
  `clasificacion_no_descargada` o `codigo_no_esta_en_catalogo`. Se calcula al consultar, así que importar
  el catálogo después actualiza la marca sin reimportar las líneas.

Archivo de referencia: `Detalles lineas.csv` (73 991 filas) · Fecha de obtención: 2026-10-07

| Diccionario | Encabezado real | Campo interno (propuesto) | Tipo | Regla / nota | Verificado |
|---|---|---|---|---|---|
| NRO_SICOP | `Número SICOP` | `nro_sicop` | texto | Une con reporte 2: todas las líneas tienen cartel; 26 carteles sin líneas | sí |
| NUMERO_LINEA | `Numero de linea` | `numero_linea` | texto | (`Número SICOP`, `Numero de linea`) no se repite en el archivo | sí |
| NUMERO_PARTIDA | `Numero partida` | `numero_partida` | texto | | sí |
| CODIGO_IDENTIFICACION | `Código identificación` | `codigo_identificacion` | texto | 16 dígitos en todas las filas; une con 10.2. Excel lo destruiría (>15 dígitos) | sí |
| CANTIDAD_SOLICITADA | `Cantidad` | `cantidad_solicitada` | decimal | Punto decimal; 113 filas con decimales | sí |
| PRECIO_UNITARIO_ESTIMADO | `Precio Unitario Estimado` | `precio_unitario_estimado` | decimal | Punto decimal, sin miles; siempre con `moneda` | sí |
| TIPO_MONEDA | `Moneda` | `moneda` | texto | Valores vistos: `CRC` (68 426), `USD` (5 565). Nunca sumar monedas distintas | sí |

## Reporte 10.2 · Códigos de identificación → `catalog_items`

Importador: `python -m app.cli import --path ZIP --report catalogo --origen …` (`app/importers/catalogo.py`).
Acepta el ZIP tal como lo entrega el portal (usa `Codigos Identificacion.csv`) o ese CSV suelto.

Archivos de referencia: 3 ZIP «Reporte de catálogo de bienes y servicios», uno por clasificación
(`83111602`, `41112301`, `45121515`) · Fecha de obtención: 2026-10-08 (hashes en `ACCESO_SICOP.md`).
El portal exige un código de clasificación completo de 8 dígitos; no acepta parciales.
Cada ZIP trae `Codigos Clasificacion.csv`, `Codigos Identificacion.csv` y `Codigos Productos.csv`
(UTF-8 con BOM, `;`, CRLF).

**Observado: `Código identificación` trae solo 8 dígitos.** El código de 16 que usan las líneas es
`Codigo Clasificación` (8) + `Código identificación` (8), como dice el diccionario («los 8 primeros
son la clasificación»). Comprobado: las 36 líneas reales de esas 3 clasificaciones unen las 36.

| Diccionario | Encabezado real | Campo interno | Tipo | Regla / nota | Verificado |
|---|---|---|---|---|---|
| CODIGO_IDENTIFICACION | `Codigo Clasificación` + `Código identificación` | `codigo_identificacion` | texto | 8 + 8 = 16 dígitos; clave del catálogo | sí |
| CODIGO_CLASIFICACION | `Codigo Clasificación` (sin tilde en «Codigo») | `codigo_clasificacion` | texto | 8 dígitos | sí |
| NOMBRE_IDENTIFICACIÓN | `Nombre Identificacion` (sin tilde) | `nombre` | texto | | sí |
| EN_USO | `En Uso` | _(después)_ | texto | `Y` / `N`; queda en `raw_snapshots` | sí (forma) |

`Codigos Productos.csv` (24 dígitos = identificación + `Código Producto` de 8; `Des Bien Servicio` con saltos
de línea dentro del campo) no se importa: las líneas de carteles usan 16 dígitos.
**Duda cerrada 2026-10-09 (Ivania):** las 73 991 líneas de carteles importadas tienen 16 dígitos (0 con 24). Los
códigos de 24 dígitos solo aparecen en las líneas de la solicitud (reporte 1.1, 426 filas), que no se importan.
Se reabre si se importa ese reporte.

## Reporte 11 · Instituciones compradoras → `institutions`

Importador: `python -m app.cli import --path ARCHIVO --report instituciones --origen …`
(`app/importers/instituciones.py`).

Archivo de referencia: `Reporte de instituciones compradoras.csv` (691 filas) · Fecha de obtención: 2026-10-08

| Diccionario | Encabezado real | Campo interno | Tipo | Regla / nota | Verificado |
|---|---|---|---|---|---|
| CEDULA | `Cédula` | `cedula` | texto | 10 dígitos, única; une con carteles: las 315 cédulas de carteles están (0 sin institución) | sí |
| NOMBRE_INSTITUCION | `Institución` | `nombre` | texto | Ninguno vacío | sí |

Otras columnas: `Dirección`, `Telefono`, `Codigo Postal`, `Provincia`, `Cantón`, `Distrito` → «después»
(quedan en `raw_snapshots`). **`Representante` es el nombre de una persona: no se guarda en la base ni en
`raw_snapshots`**; solo queda en la copia del archivo original.

## Reporte 1 · Solicitud de contratación (complementario)

Solo se usa cuando la relación con los carteles se compruebe. Tabla interna: _(por decidir)_.

Archivo de referencia: `Solicitud de contratación.csv` dentro de `Reporte de solicitud de contratación (1).zip`
(8 856 filas) · Fecha de obtención: 2026-10-07 · Fechas de trámite: 2026-07-07 06:38 → 2026-10-06 15:48

**Relación con carteles, comprobada con datos y confirmada por el diccionario:** `CARTEL_NO` es el
número SICOP e `INST_CARTEL_NO` el número de procedimiento con que se publicó la solicitud; ambos
sirven para unir con «Detalle pliego de condiciones». En los datos, `Numero de cartel` coincide con
`Número SICOP` en 8 090 de 8 120 valores (las 30 restantes no están en el archivo de pliegos de ese día)
y `Numero de procedimiento` en los mismos 8 090. La decisión de usar el reporte sigue siendo de Hermatix.

| Diccionario | Encabezado real | Campo interno (propuesto) | Tipo | Regla / nota | Verificado |
|---|---|---|---|---|---|
| IDENTIFICADOR | `Identificador` | `identificador` | texto | Forma `SC` + 12 dígitos; único por fila | sí |
| CARTEL_NO | `Numero de cartel` | `cartel_no` | texto | 11 dígitos; = `Número SICOP` de pliegos (ver arriba) | sí |
| INST_CARTEL_NO | `Numero de procedimiento` | `inst_cartel_no` | texto | Diccionario: número de procedimiento. Coincide con pliegos (8 090) | sí |
| NUMERO_SOLICITUD | `Número de solicitud` | `numero_solicitud` | texto | 15–16 dígitos, **todos con ceros iniciales**. Consecutivo por institución (no es único global) | sí |
| CEDULA_INSTITUCION | `Cédula` | `institution_cedula` | texto | 10 dígitos, 306 distintas | sí |
| TIPO_PROCEDIMIENTO | `Tipo de procedimiento` | `tipo_procedimiento_codigo` | texto | Códigos `LD`, `PX`, `PE`, `LE`, `LY`, `RE`, `SE`. El diccionario no los decodifica; significado en «Códigos de tipo de procedimiento» (abajo) | sí |
| FECHA_TRAMITE | `Fecha de trámite` | `fecha_tramite` | fecha-hora | `dd/mm/aaaa hh:mm:ss`; zona no indicada | sí (forma) |
| JUST_PROCEDENCIA | `Procedencia` | `just_procedencia` | texto | Justificación de procedencia; `-` en 234 filas | sí |
| PRESUPUESTO | `Presupuesto` | `presupuesto` | decimal | Punto decimal, sin miles; siempre con `moneda` | sí |
| MONEDA | `Moneda` | `moneda` | texto | `CRC` (8 249), `USD` (607) | sí |
| FINALIDAD_PUBLICA | `Finalidad Publica` (sin tilde) | `finalidad_publica` | texto | Texto libre largo; 28 vacías | sí |

### Códigos de tipo de procedimiento

Fuente: PDF de SICOP «Licitación para precalificación»
(`docs/referencias/P-PS-183-07-2022_Licitacion_para_precalificacion.pdf`), consultado por Ivania el 2026-10-09.
El texto del PDF nombra los tipos (licitación mayor, procedimientos por excepción, procedimientos especiales,
subasta inversa electrónica), pero los códigos de dos letras no aparecen en el texto extraíble: la
correspondencia código → significado la confirmó Ivania al revisar el documento.
El código aparece también en el número de procedimiento de los carteles: `2026`**`LD`**`-000001-0001102399`.

| Código | Nombre en los datos (columna «Tipo de procedimiento») | Carteles (10 339, julio–octubre 2026) |
|---|---|---|
| `LY` | Licitación Mayor | 377 |
| `LE` | Licitación Menor | 881 |
| `LD` | Licitación Reducida | 6 009 |
| `RE` | Remate (según el PDF; no aparece en los datos) | 0 |
| `PX` | Procedimiento por Excepción | 2 292 |
| `PE` | Procedimientos Especiales | 66 |
| `SE` | Subasta Inversa Electrónica | 8 |
| `XE` | Procedimientos Especiales | 706 |

**Comprobado 2026-10-09:** el reporte 2 trae la columna «Tipo de procedimiento» con el nombre en palabras; se cruzó
con el código del número de procedimiento en las 10 339 copias fieles (`raw_snapshots`) y cada código tiene un solo
nombre. Corrige el registro anterior del mismo día, que decía `XE` = «Procedimiento». `PE` y `XE` comparten nombre;
la diferencia entre ambos no está documentada. `XE` no está en la lista del diccionario oficial.

### Reporte 1.1 · Líneas de la solicitud

Archivo: `Lineas Solic Contratación.csv` en el mismo ZIP (51 518 filas). Todas las líneas tienen
solicitud; 22 solicitudes sin líneas. (`Identificador`, `Numero de linea`) no se repite.

| Encabezado real | Campo interno (propuesto) | Tipo | Regla / nota | Verificado |
|---|---|---|---|---|
| `Identificador` | `identificador` | texto | Une con la solicitud | sí |
| `Numero de linea` | `numero_linea` | texto | | sí |
| `Código identificación` | `codigo_identificacion` | texto | 51 092 con 16 dígitos y **426 con 24**. Por el diccionario, 24 dígitos = código de **producto** (10.3), no de identificación; sus 16 primeros son la identificación. El ERD oficial pone `CODIGO_PRODUCTO` en esta tabla. Guardar el valor tal cual y derivar los 16 | sí |
| `Cantidad` | `cantidad` | decimal | Punto decimal | sí |
| `Unidad` | `unidad` | texto | 13 valores, p. ej. `c/u`, `NA`, `kg` | sí |
| `Precio` | `precio` | decimal | Diccionario: precio unitario estimado. **No trae moneda en la línea**: *supuesto*, es la `Moneda` de la solicitud (el diccionario no lo dice) | sí (forma) |

## Reporte 5 · Ofertas (no está en la guía 16.3)

Archivos: `Reporte de ofertas.zip` (CSV) y `Reporte de ofertas.json`, del 2026-10-06. **Ambos sin
filas**: solo se conocen los encabezados. No se mapea hasta tener datos.

- `Ofertas.csv`: `Número SICOP;Numero de procedimiento;Identificador;Cédula Empresa Proveedora;Fecha Presenta Oferta;Tipo Oferta;Id Consorcio;Elegible;Estado`
- `Lineas de Ofertas.csv`: `Número SICOP;Identificador;Numero de linea;Código Producto;Cantidad;Precio Unitario Ofertado;Moneda;Descuento;IVA;Otros Impuestos;Acarreos;Tipo Cambio CRC`
- JSON: objeto con las listas `Ofertas` y `Lineas de Ofertas` (vacías).
- Diccionario: `ESTADO` indica si la oferta sigue vigente o fue retirada (confirma la guía 16.3:
  es de la oferta, no del procedimiento).
- Nombres que difieren del diccionario: `CEDULA_PROVEEDOR` → `Cédula Empresa Proveedora`;
  en 5.1, `NRO_OFERTA` → `Identificador`, `CODIGO_PRODUCTO` (24 dígitos) → `Código Producto`.

## Adjudicaciones en firme (reportes 6, 6.1 y 6.2) · módulo de competencia (A2)

Archivo de referencia: `Reporte de adjudicaciones en firme.zip`, descargado por Ivania el 2026-10-22 (UTF-8 con BOM,
punto y coma). Trae 3 CSV: `Detalle Adjudicaciones.csv` (29 922 filas), `Det Proveedores Adj.csv` (15 430) y
`Det Lineas Adjudicadas.csv` (26 969). Adjudicaciones en firme de julio a octubre de 2026. Se importa el ZIP tal
cual: `python -m app.cli import --report adjudicaciones --path "<ZIP>" --origen real` (`app/importers/adjudicaciones.py`).
«Contratos» (reportes 7 y 7.2) todavía no se descargó.

**Adjudicatario: viene SOLO como cédula** (`Cédula Empresa Proveedora`), nunca con nombre. El nombre lo pone
Hermatix en `config/competidores.yaml`. Las cédulas tienen 10 dígitos (26 945 líneas) o 12 (24); algunas empiezan
con 0, así que se guardan como texto.

Lo que se observó en los datos reales:
- **Reporte 6:** un cartel tiene varias filas, una por acto en firme y cada una con su hora (9155 carteles en
  29 922 filas). Hay 462 filas idénticas. SICOP marca «sin valor» con un espacio (`' '`): 4345 en
  `Fecha Maxima Recursos`, 663 en `Permite Recursos` y 13 en `Fecha Comunicación`. Se guarda como vacío.
  `Desierto` es siempre `N`.
- **Reporte 6.1:** hay 7486 filas idénticas, que se guardan una vez. Todo cartel del 6.1 y del 6.2 está en el 6.
- **Reporte 6.2:** no trae descripción ni código de producto (el diccionario dice `CODIGO_PRODUCTO` y
  `NRO_OFERTA`, pero no vienen). Por eso la familia sale del cartel. Las 26 969 líneas unen con `tender_lines`
  por `Número SICOP` + `Numero de linea`.
  - **88 líneas tienen más de un registro distinto** para el mismo cartel, línea y cédula. Casi siempre cambia
    solo `Tipo Cambio CRC`, pero a veces también la moneda o la cantidad. Se guardan todos y **no se suman**.
  - `Descuento` e `IVA` son **montos, no porcentajes**. Por ejemplo, 11 × 55 000 con descuento 90 750 es un
    15 %, y el IVA 7840 es el 2 % de 392 000.

| Diccionario | Encabezado real | Campo interno | Tipo | Regla / nota | Verificado |
|---|---|---|---|---|---|
| `NRO_SICOP` | `Número SICOP` | `adjudicaciones.nro_sicop` (y en 6.1 y 6.2) | texto | une con `tenders.nro_sicop` | sí |
| `NUMERO_PROCEDIMIENTO` | `Numero de procedimiento` | `nro_procedimiento` | texto | | sí |
| `FECHA_COMUNICACION` | `Fecha Comunicación` | `fecha_comunicacion` | fecha CR | `' '` = vacío | sí |
| `FECHA_ADJ_FIRME` | `Fecha Adj Firme` | `fecha_adj_firme` | fecha CR | periodo de «Competencia»: la primera del cartel | sí |
| `PERMITE_RECURSOS` | `Permite Recursos` | `permite_recursos` | texto | `Si` / `No` / `' '` | sí |
| `FECHA_MAXIMA_RECURSOS` | `Fecha Maxima Recursos` | `fecha_maxima_recursos` | fecha CR | `' '` = vacío | sí |
| `DESIERTO` | `Desierto` | `desierto` | texto | | sí |
| `CEDULA_PROVEEDOR` (6.1) | `Cédula Empresa Proveedora` | `adjudicacion_proveedores.cedula_proveedor` | texto | **el adjudicatario**; quién gana y cuántas veces | sí |
| `NRO_LINEA` | `Numero de linea` | `adjudicacion_lineas.numero_linea` | texto | | sí |
| `CEDULA_PROVEEDOR` (6.2) | `Cédula Empresa Proveedora` | `adjudicacion_lineas.cedula_proveedor` | texto | | sí |
| `CANTIDAD_ADJUDICADA` | `Cantidad` | `cantidad` | Decimal (texto) | | sí |
| `PRECIO_UNITARIO_ADJUDICADO` | `Precio` | `precio_unitario` | Decimal (texto) | hasta 4 decimales | sí |
| `TIPO_MONEDA` | `Moneda` | `moneda` | 3 letras | CRC 22 580 · USD 4304 · EUR 85 | sí |
| `DESCUENTO` | `Descuento` | `descuento` | Decimal (texto) | monto | sí |
| `IVA` | `IVA` | `iva` | Decimal (texto) | monto; no se suma al monto | sí |
| `OTROS_IMPUESTOS` | `Otros Impuestos` | `otros_impuestos` | Decimal (texto) | no se suma | sí |
| `ACARREOS` | `Acarreos` | `acarreos` | Decimal (texto) | no se suma | sí |
| `TIPO_CAMBIO_CRC` | `Tipo Cambio CRC` | `tipo_cambio_crc` | Decimal (texto) | se guarda, **nunca se usa para convertir** | sí |
| — | (calculado) | `monto_sin_impuestos` | Decimal (texto) | cantidad × precio − descuento, en la moneda de la línea | sí |

## Columnas reales fuera de la tabla de la guía 16.3

Encabezados observados que la guía no pide. **Todos están en el diccionario oficial**, con estos
nombres: `COD_UNIDAD_COMPRA`, `NOMBRE_UNIDAD_COMPRA`, `TIPO_PROCEDIMIENTO`, `MODALIDAD_PROCEDIMIENTO`,
`EXCEPCION_CD`, `PAGO_ADELANTADO_PYMES` («indicador»; en el archivo viene `Y`/`N`), `FECHA_INVITACION`,
`FECHA_APERTURA` y `TIPO_CAMBIO_USD`. No se descartan sin decidirlo.

Nombres internos entre paréntesis = solo sugerencia; la decisión es de Hermatix.
Decisión 2026-10-07 (Ivania): **«después» para todas**. Se decide al escribir las reglas de
oportunidades; mientras tanto se conservan en los archivos de `data/raw/`, no se guardan en la base.
Lo mismo aplica a las columnas del reporte 1 que están fuera de la guía (`NUMERO_SOLICITUD`,
`CEDULA_INSTITUCION`, `TIPO_PROCEDIMIENTO`, `FECHA_TRAMITE`, `JUST_PROCEDENCIA`) y a sus líneas (1.1).

| Reporte | Encabezado real | Ejemplo de valor (sin datos sensibles) | ¿Se usa? | Decisión |
|---|---|---|---|---|
| 2 | `Cod Unidad Compra` | 5 dígitos con ceros iniciales (9 355 filas) → **texto obligatorio** | después | pendiente (`unidad_compra_codigo`) |
| 2 | `Nombre Unidad Compra` | texto, 165 valores distintos | después | pendiente (`unidad_compra_nombre`) |
| 2 | `Tipo de procedimiento` | 6 valores, p. ej. `Licitación Reducida`, `Licitación Mayor` | después | pendiente (`tipo_procedimiento`) |
| 2 | `Modalidad Procedimiento` | 14 valores, p. ej. `Cantidad definida`, `Según demanda` | después | pendiente (`modalidad`) |
| 2 | `Excepción CD` | vacío en 8 043 filas; p. ej. `Proveedor único (Inciso c del artículo 3 LGCP 9986)` | después | pendiente (`excepcion_cd`) |
| 2 | `Pago Adelantado Pymes` | `Y` / `N` | después | pendiente (`pago_adelantado_pymes`) |
| 2 | `Fecha Invitación` | `dd/mm/aaaa hh:mm:ss` | después | pendiente (`fecha_invitacion`) |
| 2 | `Fecha Apertura` | `dd/mm/aaaa hh:mm:ss`, 485 vacías | después | pendiente (`fecha_apertura`) |
| 2.1 | `Tipo Cambio USD` | `451.72` (decimal) | después | pendiente (`tipo_cambio_usd`). Solo informativo: no autoriza sumar CRC y USD |

## Cambios del mapeo

| Fecha | Cambio | Motivo / archivo que lo evidencia |
|---|---|---|
| 2026-10-06 | Plantilla inicial a partir del diccionario (guía 16.3) | Sin archivo real todavía |
| 2026-10-07 | Reglas de versiones/fechas de 16.3 y sección vacía de adjudicaciones (A2) | Revisión contra la guía |
| 2026-10-07 | Encabezados reales de reportes 2 y 2.1 y columnas extra | `Detalle de pliegos de condiciones.csv`, `Detalles lineas.csv` (hashes en ACCESO_SICOP.md) |
| 2026-10-07 | Reporte 1 con archivo real, sus líneas, relación con carteles comprobada; encabezados de Ofertas (vacío) | `Reporte de solicitud de contratación (1).zip`, `Reporte de ofertas.zip/.json` |
| 2026-10-07 | Contraste con el diccionario y ERD oficiales de SICOP: `INST_CARTEL_NO` = número de procedimiento (corrige el candidato anterior, `Número de solicitud`); 24 dígitos = código de producto; columnas de reportes 1, 5, 6, 10.2 y 11 según diccionario | `docs/referencias/Diccionario_de_datos_reporte_de_contratos_de_Datos_abiertos.pdf`, `docs/referencias/Diagrama_ERD_SICOP.pdf` |
| 2026-10-08 | Reportes 10.2 y 11 con archivos reales; catálogo = clasificación + identificación (8 + 8); importadores de líneas, catálogo e instituciones | 3 ZIP del catálogo y `Reporte de instituciones compradoras.csv` (hashes en ACCESO_SICOP.md) |
| 2026-10-08 | Advertencia de inicio de recepción solo si es más de 1 h antes de la publicación (108 → 1 caso) | Decisión de Ivania; revisión en el portal (ver `ACCESO_SICOP.md`) |
| 2026-10-09 | `XE` = «Procedimientos Especiales» (no «Procedimiento»): comprobado con la columna «Tipo de procedimiento» de los datos reales | 10 339 carteles en `raw_snapshots` |
| 2026-10-09 | Zona horaria confirmada (hora de Costa Rica, `-06:00`); significado de los 8 códigos de tipo de procedimiento; dudas cerradas: `NRO_SEQ_SICOP` y `Codigos Productos.csv` | Ivania: SICOP es exclusivo de Costa Rica; PDF de SICOP «Licitación para precalificación»; horas de cierre en los datos reales |
| 2026-10-22 | Adjudicaciones en firme (6, 6.1 y 6.2) con archivo real: adjudicatario solo por cédula, `' '` = vacío, filas idénticas, 88 líneas con registros distintos, descuento e IVA como montos | `Reporte de adjudicaciones en firme.zip` (Ivania) |
