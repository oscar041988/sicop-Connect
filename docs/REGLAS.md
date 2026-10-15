# Reglas de detección de oportunidades

Cómo SICOP CONNECT decide si un cartel le interesa a Hermatix, cómo se cambian las reglas y cómo se
comprueba que un cambio mejoró las cosas. Las reglas están en `config/hermatix_rules.yaml` y se editan
**a mano**; el código (`app/matching/`) no contiene ninguna palabra clave.

Fuente de los términos: `docs/Diccionario_palabras_clave_v2_aprobado.pdf` (aprobado por Oscar el 2026-10-07).

## Receta rápida: agregar o quitar una palabra

1. Anota el cartel que motivó el cambio (número SICOP) y mira por qué salió así:
   `python -m app.cli evaluate --nro NRO_SICOP`
2. Escribe qué esperas que cambie (tu predicción).
3. Edita `config/hermatix_rules.yaml`: minúsculas, sin tildes, comillas rectas, y un comentario `#` con quién lo
   decidió y la fecha.
4. Mide: `python -m pytest tests/test_golden_medicion.py -s` y `python -m app.cli evaluate`.
5. Si se cumplió tu predicción y el golden set no bajó, regístralo en la sección 6 y haz commit.

El detalle de cada paso está en las secciones 3 y 4.

---

## 1. Cómo decide el motor

### 1.1 Qué texto mira

- El **título** del cartel (`tenders.descripcion`).
- El **nombre de catálogo** de cada línea, solo si el código de la línea une con el catálogo (reporte 10.2).
  Las líneas sin catálogo no aportan texto, pero bajan la calidad de datos a «Código sin catálogo».
  Hoy solo **36 de 73 991 líneas** tienen catálogo descargado (3 códigos de clasificación), así que la mayoría
  de los carteles se evalúa solo por el título.

### 1.2 Cómo compara

- **Normaliza solo para comparar**: minúsculas, sin tildes, espacios duros (NBSP) y signos como espacios.
  La evidencia se guarda con el texto **original**.
  Ejemplo: «CÁMARAS CORPORALES» y «camaras corporales» coinciden, y la evidencia muestra «CÁMARAS CORPORALES».
- **Palabra completa, con plural**: «edificio» coincide con «edificios», pero «lora» no coincide dentro de «exploración».
- **La frase más larga gana**: en «monitoreo GPS» no se cuenta además «gps» suelto. En «control de llantas»
  (señal) no se cuenta la exclusión «llantas».
- **Frase exacta**: no admite palabras intermedias. «monitoreo **y localización satelital mediante el sistema** GPS»
  no contiene «monitoreo gps». Se decidió no cambiarlo (2026-10-09): permitir 1–3 palabras intermedias no
  arreglaba ese caso (había 6) ni cambiaba el golden set; se agregó la frase real al YAML (ver sección 5).

### 1.3 Cómo se decide el encaje de una familia

Para cada familia, en este orden:

| Paso | Si… | Resultado |
|---|---|---|
| 1 | hay una **exclusión en el título** | **Sin coincidencia** para todo el cartel, con la exclusión como evidencia |
| 2 | hay al menos una **señal alta** | **Alta** |
| 3 | hay una **señal media** junto a otra media distinta o a un término de **contexto** | **Media** |
| 4 | hay una **señal media sola** | **Baja** |
| 5 | solo hay contexto, o nada | no se guarda nada |

Una exclusión **dentro de una línea** solo anula las señales de esa línea, no las del resto del cartel.

Solo **Alta** y **Media** son candidatos (se muestran y se miden). **Baja** queda guardada para análisis.

Ejemplos reales:

- «CONTRATACIÓN DE SERVICIO DE MONITOREO GPS PARA LA FLOTILLA VEHICULAR» → «monitoreo gps» es señal alta → **Alta**, FleetMatix.
- «Servicio de uso de tarjeta para suministro de combustible y GPS en la flotilla Municipal» → «gps» (media)
  + «flotilla» (contexto) → **Media**. Sin «flotilla» sería **Baja**.
- «ADQUISICIÓN DE EQUIPO TOPOGRAFÍA GNSS» → «gnss» es exclusión → **Sin coincidencia**.

### 1.4 Dimensiones separadas

Cada resultado (tabla `opportunity_assessments`) guarda por separado:

| Dimensión | Valores | De dónde sale |
|---|---|---|
| Encaje comercial | Alta · Media · Baja · Sin coincidencia | Las reglas |
| Plazo / estado | Abierto · Cierra en 7 días o menos · Vencido · Por verificar | Fecha de cierre de recepción |
| Calidad de datos | Completo · Sin líneas · Código sin catálogo | Líneas y catálogo. «Archivo parcial» (de la guía) **aún no se detecta** |
| Requisitos | Viabilidad pendiente · Revisado | Decisión humana. **Pendiente**: llega con el panel y las revisiones (lección 5) |

«Alta» habla del encaje con el portafolio, **no** de que Hermatix pueda o deba participar.

Cada fila también guarda la **regla** (qué términos decidieron), la **evidencia** (frases exactas y si salieron
del título o de qué línea) y la **versión de reglas**.

### 1.5 Cómo leer la salida de `evaluate`

```text
  20260900967 · Alta · gps_flotas (fleetmatix) · Vencido · Completo
      ALQUILER SISTEMA DE MONITOREO GPS PARA LA FLOTA VEHICULAR MUNICIPAL
      regla: senales_alta: sistema de monitoreo gps + senales_media: gps
      evidencia: «SISTEMA DE MONITOREO GPS» (título) · «GPS» (línea 1) · «GPS» (línea 2) · «GPS» (línea 3)
```

| Parte | Significa |
|---|---|
| `20260900967` | Número SICOP del cartel |
| `Alta` | Encaje comercial |
| `gps_flotas (fleetmatix)` | Familia y producto de Hermatix |
| `Vencido` | Plazo: la recepción de ofertas ya cerró |
| `Completo` | Calidad de datos: tiene líneas y todas unen con el catálogo |
| segunda línea | Título original, tal como viene en SICOP |
| `regla` | Qué términos del YAML decidieron, con su tipo (`senales_alta`, `senales_media`, `contexto`, `exclusiones`) |
| `evidencia` | Frases exactas que coincidieron y de dónde salieron: el título o una línea |

Arriba de la lista, el resumen dice cuántas filas son nuevas, cuántas cambiaron y cuántas quedaron «sin cambios».
Si todo dice «sin cambios», ni las reglas ni los datos cambiaron desde la última evaluación.

### 1.6 Familias actuales

Candidatos con las reglas `92aef8277e2e` sobre 10 339 carteles reales (julio a octubre de 2026):

| Familia | Producto | Alta | Media | Baja |
|---|---|---|---|---|
| `gps_flotas` | FleetMatix | 7 | 3 | 13 |
| `videotelematica` | Fenova IA | 0 | 0 | 33 |
| `seguridad_vial` | Fenova IA | 0 | 0 | 9 |
| `transporte_corporativo` | MoveOn | 0 | 0 | 0 |
| `rastreo_activos` | SmartTags | 0 | 2 | 18 |
| `iot_frio` | Osmia IoT | 6 | 0 | 3 |
| `camaras_corporales` | BodyCams | 3 | 0 | 2 |
| `conteo_pasajeros` | PassengerIQ | 0 | 0 | 4 |
| `mantenimiento_flotas` | FleetRun | 0 | 0 | 97 |

Una familia sin candidatos no es un error: en este periodo no hubo compras de ese producto.

---

## 2. Estructura del YAML

```yaml
familias:
  gps_flotas:                      # nombre de la familia (sin espacios ni tildes)
    producto: fleetmatix           # producto de Hermatix
    senales_alta: ["monitoreo gps", "rastreo vehicular"]
    senales_media: ["gps", "control de combustible"]
    contexto: ["flotilla", "vehiculos"]
    exclusiones: ["topografico", "levantamiento"]   # comentario: el programa ignora lo que va después de #
```

Reglas de escritura:

- Solo existen estas 5 claves por familia. Una clave mal escrita (`Exlcusiones`) **detiene** el comando con un
  error, para que una familia no quede sin exclusiones sin que nadie lo note.
- Términos en minúsculas, sin tildes y entre comillas rectas `" "` (no las curvas `“ ”` de Word).
- Las variantes van por separado: «GNSS / RTK» se escribe `"gnss", "rtk"`.
- Las notas para personas van como comentario `#`, nunca dentro del término: «(sin software)» nunca aparece en un cartel.
- Conviene escribir en singular: «camara de solapa» también encuentra «camaras de solapa»; al revés, no.

---

## 3. Cómo cambiar una regla

1. **Parte de un caso real.** Un falso positivo de `evaluate` o un fallo del golden set, con su número SICOP.
2. **Busca la causa** en la regla y la evidencia que muestra el comando:
   `python -m app.cli evaluate --nro 20261000101`
3. **Elige el cambio más pequeño** que la corrige:
   - ¿Falta una señal? Agrégala al nivel que corresponda.
   - ¿Un término es demasiado general? Bájalo a media o a contexto, o reemplázalo por una frase más precisa.
   - ¿Falta una exclusión? Agrégala, comprobando que no esté **dentro** de una señal de la misma familia.
4. **Escribe tu predicción antes de medir**: qué carteles cambian y a qué nivel.
5. **Edita el YAML** y deja un comentario con la decisión, quién la tomó y la fecha.
6. **Mide** (sección 4) y compara con tu predicción. Si no se cumplió, entiende por qué antes de seguir.
7. **Si el golden set baja con los mismos casos**, el cambio no se acepta tal como está. Si bajó porque se
   **agregaron casos** nuevos al golden set, no es culpa del cambio de reglas: compara con la medición anterior
   sobre los mismos carteles.
8. **Registra** la decisión en la sección 6 (con la versión de reglas que imprime `evaluate`) y haz commit.

No ajustes reglas solo para que acierte un caso del golden set (sobreajuste). Cada término debe tener sentido
comercial: ¿lo diría una institución que compra ese producto?

---

## 4. Cómo medir el efecto

```powershell
# Acierto contra el golden set (meta O3: al menos 80 %), con los casos fallidos y su evidencia
python -m pytest tests/test_golden_medicion.py -s

# Todas las pruebas (incluye los casos de la guía y las decisiones registradas)
python -m pytest -q

# Evaluar todos los carteles y ver los primeros 20 candidatos
python -m app.cli evaluate

# Un solo cartel
python -m app.cli evaluate --nro NRO_SICOP
```

- **Versión de reglas**: es una huella del archivo YAML (p. ej. `2de4846a5a7e`). Cambiar una sola palabra genera
  una versión nueva; las evaluaciones anteriores **no se borran**, así que se pueden comparar el antes y el después.
- **Reevaluar es idempotente**: con la misma versión y los mismos datos, la segunda vez dice «sin cambios».
- El resumen de `evaluate` muestra, por familia, cuántos carteles quedaron en Alta / Media / Baja / Sin coincidencia.
  Ese conteo es la forma rápida de ver si una familia se llenó de ruido.

**La medición usa título y líneas**, igual que el motor. Las líneas de los carteles del golden set están en
`tests/golden/golden_lineas.csv`, copiadas de la base (ver `tests/golden/README.md`).

Por qué importa: hasta el 2026-10-09 la medición solo usaba títulos, y la cifra no coincidía con la base, en las
dos direcciones:

- **La medición fallaba, pero el motor acertaba.** Los data loggers `20260903830` y `20260901813` se titulan
  «compra medidor de condiciones ambientales…» y «COMPRA DE EQUIPO DE LABORATORIO»; la señal («REGISTRADOR DE
  DATOS») está en la línea. Al agregarlos, la medición bajó de 25/26 = 96,2 % a 25/28 = 89,3 %. Con las líneas:
  27/28 = 96,4 % (28/29 = 96,6 % tras confirmar `20260800233`, y 29/29 tras agregar «localizacion satelital», el mismo día).
- **La medición acertaba, pero el motor fallaba.** `20260900951` («termohigrometros digitales portátiles») acertaba
  con el título y salía Media al sumar sus líneas (antes del ajuste de `iot_frio`).

Si se agregan carteles al golden set o se descarga catálogo nuevo, hay que **regenerar** `golden_lineas.csv`;
si no, la medición vuelve a ver menos que el motor. Además del porcentaje, revisar los candidatos reales de `evaluate`.

---

## 5. Trampas conocidas

Lecciones de la primera revisión (2026-10-09):

| Trampa | Ejemplo real | Qué hacer |
|---|---|---|
| Contexto demasiado general | «sistema» subía a Media el «mantenimiento preventivo de los sistemas de bombeo» | Usar frases precisas: «sistema de software» |
| Palabra con otro sentido en otro mercado | «carga trasera y carga lateral» en compras de contenedores de basura | Quitarla o exigir la frase completa («rastreo de carga») |
| Exclusión que anula una señal propia | «combustible» anulaba «control de combustible» | Exclusión más precisa: «compra de combustible» |
| Exclusión de una palabra común | «reparacion» saca los talleres, pero también anularía «reparación del sistema GPS» | Aceptarlo solo si se decide a conciencia; anotar el riesgo y vigilarlo |
| Dos señales de la misma ficha | Toda ficha de higrómetro dice «humedad relativa»: con «termohigrometro» sumaba dos medias | Dejar los datos técnicos como contexto |
| Título genérico | «COMPRA DE EQUIPO DE LABORATORIO», «Insumos varios II»: la señal solo está en las líneas | Descargar el catálogo de las familias (reporte 10.2); no inventar señales para el título |
| Siglas cortas | «dsm» coincidió con «AC para DSM» (aire acondicionado) | Siglas como señal media, nunca alta |
| Palabras intermedias | «Monitoreo y Localización Satelital mediante el Sistema GPS» quedó en Baja | Agregar la frase real al YAML («localizacion satelital», que es el nombre del catálogo SICOP). Permitir palabras intermedias en el motor se simuló y no ayudó |

---

## 6. Registro de decisiones

La versión es la que imprime `evaluate` después del cambio. Con ella se consultan en la base los resultados
de antes y de después.

| Fecha | Versión | Familia | Cambio | Decidió | Efecto medido |
|---|---|---|---|---|---|
| 2026-10-09 | `92299b2db230` | todas | Primer YAML a partir del diccionario v2 (9 familias) | Ivania (escrito a mano), revisado por Claude | Golden set 96,2 % (25/26); 13 Alta, 36 Media |
| 2026-10-09 | `6b803626ecde` | mantenimiento_flotas | Contexto «sistema» y «plataforma» → solo «software», «plataforma digital / de software», «sistema de software / digital» | Ivania | 18 Media → Baja; golden set igual |
| 2026-10-09 | `dd24ffc38ab2` | rastreo_activos | Contenedores y carga solo cuentan con rastreo: altas «gps para contenedores», «monitoreo de contenedores», «rastreo de carga», «monitoreo de carga»; se quita el contexto «carga»; exclusiones «compra de contenedores», «adquisicion de contenedores», «impresora termica» | Ivania | Media 4 → 2 (quedan los 2 casos RFID reales); golden set igual |
| 2026-10-09 | `4f7b797dfa37` | gps_flotas | Exclusión «mantenimiento preventivo y correctivo de vehiculos» → «mantenimiento preventivo y correctivo» | Ivania | 2 talleres de flotilla salen de Media; predicción cumplida |
| 2026-10-09 | `4f7b797dfa37` → `e0756b34bfac` | iot_frio | «termohigrometro» y «humedad relativa» pasan de señal media a contexto | Ivania (Oscar: termohigrómetro portátil no interesa) | 4 termohigrómetros salen de Media. La predicción falló en el primer intento (`4f7b797dfa37`): con solo «termohigrometro» movido, «humedad relativa» + contexto seguía dando Media |
| 2026-10-09 | `2de4846a5a7e` | gps_flotas | Exclusión «reparacion»; «flotilla vehicular» pasa de señal media a contexto; señal alta «rastreo gps» | Ivania | Salen 2 talleres de Media (`20260803580` reparación, `20260701797` enderezado y pintura); `20260802605` sube a Alta. Predicción simulada antes y cumplida. Riesgo aceptado: «reparación» también anularía un servicio de reparación de equipos GPS |
| 2026-10-09 | `2de4846a5a7e` (sin cambio) | iot_frio | Data loggers comprados como equipo de laboratorio **interesan** (`20260903830`, `20260901813`): sin cambio en el YAML (ya eran Alta); se agregan al golden set | Oscar (confirmado a Ivania) | Golden set de 31 a 33 carteles: 25/28 = 89,3 %. Los 2 fallan en la medición porque su señal está en las líneas y el golden set solo mide títulos (sección 4) |
| 2026-10-09 | `2de4846a5a7e` (sin cambio) | — | La medición del golden set usa también las líneas (`tests/golden/golden_lineas.csv`) | Ivania | 27/28 = 96,4 %; predicción cumplida. El provisional `20260800233` pasa a «fallaría» (cadena de frío en un termómetro, pendiente con Oscar) |
| 2026-10-09 | `f3368bcc09e3` | iot_frio · gps_flotas | «compra de vacunas» confirmada como exclusión; «navegacion» pasa de exclusión a contexto en gps_flotas | Ivania | Entró como Media `20260700052` («…sistemas didácticos y GPS de navegación») |
| 2026-10-09 | `99bbfdb33641` | gps_flotas · iot_frio | Exclusión «didactico» (gps_flotas); exclusión «de mano» (iot_frio: un aparato de mano no interesa, uno inalámbrico sí); «camara de refrigeracion» pasa de señal media a contexto (Hermatix no vende el equipo; solo cuenta si se pide monitoreo) | Ivania | `20260700052` vuelve a Sin coincidencia; `20261000163` (cámara de refrigeración para banco de sangre) deja de ser candidato. «de mano» no cambia nada hoy. Los termómetros «para cadena de frío» (`20260800233`, `20260703372`) siguen Alta: su ficha no dice «de mano», así que interesan |
| 2026-10-09 | `99bbfdb33641` (sin cambio) | iot_frio | Criterio: un dispositivo que mide temperatura, humedad o GPS y tiene **pantalla o panel** interesa; sin pantalla (medidor portátil) no interesa. Si dice «de mano», queda fuera siempre, aunque tenga pantalla (exclusión). `20260800233` pasa a «interesa» confirmado en el golden set | Ivania (Hermatix) | Coincide con lo que ya hace el motor: los termómetros con «PANTALLA LCD» son Alta y los termohigrómetros sin pantalla no son candidatos. Golden set 28/29 = 96,6 % |
| 2026-10-09 | `92aef8277e2e` | gps_flotas | Señal alta «localizacion satelital» (nombre del catálogo SICOP del servicio GPS). Se descartó permitir palabras intermedias en el motor: simulado con 1, 2 y 3 palabras, no arreglaba el caso | Ivania | `20260902620` pasa a Alta y `20260900818` sube de Media a Alta. Golden set 29/29 = 100 %; 21 candidatos. Predicción simulada antes y cumplida |
| 2026-10-12 | `92aef8277e2e` (sin cambio) | — | Se confirman los 4 provisionales del golden set sin el pliego (concursos cerrados): `20260702834` interesa (`iot_frio`, el registrador transmite datos); `20260700980` no interesa (no se dan asesorías); `20260701485` no interesa (no se da mantenimiento de cuartos fríos); `20260701333` falso positivo (no se trabaja con LIDAR, GNSS ni RTK) | Ivania (Hermatix) | Golden set 33/33 = 100 %, sin provisionales |

### Pendiente de decidir con Oscar

- Nada por ahora: los 4 provisionales del golden set se confirmaron el 2026-10-12.

---

## 7. Propuesta para la lección 13: sugerencias a partir de las revisiones

> **Diseño, no implementado.** Requiere revisiones humanas acumuladas (empiezan con el panel, lección 5).
> Idea de Ivania (2026-10-09), corregida en la revisión.

Principio: **el sistema propone y una persona decide.** Nunca escribe el YAML solo, porque una exclusión
mal aprendida anula familias enteras sin que nadie lo note.

1. **Candidatos.** Después de cada importación, el sistema busca frases de 1 a 3 palabras que no estén en el YAML,
   descartando palabras vacías («de», «para») y genéricas («compra», «servicio»). Cada candidata se guarda con su
   familia y el fragmento de texto donde apareció.
2. **Qué cuenta.** Solo carteles revisados por una persona y el golden set. Un descarte cuenta solo si el motivo
   fue «no encaja con el portafolio», no si fue por plazo, requisitos o presupuesto.
3. **Proporciones, no carreras.** Casi todos los carteles son «no interesa», así que contar quién llega primero a 10
   haría exclusión de cualquier palabra común. Con al menos 10 carteles revisados, se calcula qué proporción interesó.
   Ejemplo de umbrales (los fija Oscar):
   - 80 % o más interesó → proponer como **contexto**; con cada 10 casos más puede proponerse subir a media y a alta.
   - 10 % o menos interesó → proponer como **exclusión**, con la lista de carteles como prueba.
   - Entre ambos → **mixta**: proponer como señal media o dejarla para que Oscar la revise.
4. **Escalera y exclusión son caminos distintos.** Contexto → media → alta mide cuánto suma un término; la exclusión
   anula y exige más evidencia.
5. **Aprobación.** Una persona acepta o rechaza cada propuesta y edita el YAML a mano. Antes de guardar se mide el
   golden set; si el acierto baja, no se acepta.
6. **Trazabilidad.** Cada cambio queda en el registro de la sección 6 y genera una versión de reglas nueva.

Riesgo a vigilar: si un cartel se mostró **por** un término, su revisión no debería contar para subir ese mismo
término (el sistema se confirmaría a sí mismo).
