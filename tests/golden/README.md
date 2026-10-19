# Golden set

`golden_set.csv` es la «hoja de respuestas» con la que se mide si las reglas de detección aciertan
(guía, sección 16.5). **Las etiquetas son de Hermatix (Oscar), no de Claude.**

- **Datos: REALES.** 33 carteles públicos de `Detalle de pliegos de condiciones.csv` (2026-10-07). El título
  es el texto exacto del cartel (puede traer espacios duros, NBSP). Sin datos confidenciales.
- Origen de las etiquetas: reunión de Oscar con Ivania, 2026-10-08 (las registró Ivania).
- Formato: UTF-8 con BOM, separador `;`, CRLF.

## Columnas

| Columna | Valores | Nota |
|---|---|---|
| `nro_sicop` | texto, 11 dígitos | Clave del cartel. En Excel, importarla como **texto** |
| `titulo` | texto | Exacto, tal como viene en SICOP |
| `etiqueta` | `interesa`, `no_interesa`, `falso_positivo_conocido` | |
| `familia_esperada` | una o varias familias separadas por `;` | Obligatoria si interesa; vacía si no interesa; en un falso positivo, la familia que aparenta. Con varias, cualquiera cuenta como acierto |
| `confirmada` | `sí`, `no` | `no` = provisional: se guarda, pero **no cuenta** al medir |
| `nota` | texto libre | Por qué se etiquetó así o qué falta para confirmar |
| `fuente` | texto | Quién etiquetó |
| `actualizado` | `aaaa-mm-dd` | Fecha del último cambio de la fila |

Familias (del diccionario aprobado v2): `gps_flotas` (FleetMatix), `videotelematica` (Fenova IA),
`seguridad_vial`, `conteo_pasajeros` (PassengerIQ), `transporte_corporativo` (MoveOn),
`rastreo_activos` (SmartTags), `mantenimiento_flotas` (FleetRun), `iot_frio` (Osmia IoT),
`camaras_corporales` (BodyCams).

## Líneas de los carteles (`golden_lineas.csv`)

La medición evalúa el título **y** el nombre de catálogo de las líneas, igual que `evaluate`. Sin las líneas,
un cartel con título genérico («COMPRA DE EQUIPO DE LABORATORIO») fallaría en la medición aunque el motor acierte.

- **Datos: REALES**, copiados de `data/sicop.db` (vista `v_tender_lines`, solo líneas `en_catalogo`) el 2026-10-09.
- Columnas: `nro_sicop`, `numero_linea`, `codigo_identificacion` (16 dígitos, texto), `nombre_catalogo`.
- Mismo formato que `golden_set.csv`. Hoy: 22 líneas de 17 carteles.
- **Regenerarlo** cuando se agreguen carteles al golden set o se descargue catálogo nuevo: copiar de la base las
  líneas con `estado_catalogo = 'en_catalogo'` de los `nro_sicop` del golden set, ordenadas por cartel y línea.

## Cómo actualizarlo

Se puede cambiar o agregar filas cuando Oscar confirme algo o haya carteles nuevos:

1. Editar la fila (con un editor de texto, o con Excel importando `nro_sicop` como texto).
2. Cambiar `confirmada` a `sí` si ya no hay duda, y actualizar `nota`, `fuente` y `actualizado`.
3. Ejecutar `python -m pytest tests/test_golden_set.py`: comprueba que el archivo siga siendo válido.
4. Hacer commit con un mensaje que diga qué cambió y quién lo decidió.

## Pendientes de confirmar (actualizado 2026-10-12)

Ninguno. Las 4 filas provisionales (`20260702834`, `20260700980`, `20260701485`, `20260701333`) se confirmaron
el 2026-10-12 (Ivania, Hermatix) **sin el pliego**: los concursos ya cerraron y su información no se puede
revisar con certeza, así que se decidió con el conocimiento de lo que Hermatix vende y no vende.

`20260800233` se confirmó el 2026-10-09 como «interesa» (iot_frio) con la regla de Hermatix: un dispositivo
que mide temperatura, humedad o GPS y tiene pantalla o panel interesa; sin pantalla, no. Si dice «de mano»,
no interesa nunca, aunque tenga pantalla.
