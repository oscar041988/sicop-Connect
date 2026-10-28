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
  Solo **41 de 87 344 líneas** tienen catálogo descargado (3 códigos de clasificación; base local, 2026-10-23),
  así que la mayoría de los carteles se evalúa solo por el título.

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
| Requisitos y decisión | Interesa · No interesa · Revisar requisitos · Ofertada · No se oferta | Decisión humana en el panel: va en `reviews`, no en esta tabla |

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

Candidatos con las reglas `b880e0d350e1` sobre 12 260 carteles reales publicados del 7 de julio al 21 de
octubre de 2026 (base local, evaluación completa del 2026-10-22):

| Familia | Producto | Alta | Media | Baja |
|---|---|---|---|---|
| `gps_flotas` | FleetMatix | 9 | 5 | 15 |
| `videotelematica` | Fenova IA | 1 | 0 | 43 |
| `seguridad_vial` | Fenova IA | 0 | 0 | 9 |
| `transporte_corporativo` | MoveOn | 0 | 0 | 0 |
| `rastreo_activos` | SmartTags | 0 | 2 | 23 |
| `iot_frio` | Osmia IoT | 7 | 0 | 3 |
| `camaras_corporales` | BodyCams | 5 | 0 | 2 |
| `conteo_pasajeros` | PassengerIQ | 0 | 0 | 4 |
| `mantenimiento_flotas` | FleetRun | 0 | 0 | 115 |

Antes, con `92aef8277e2e` sobre 10 339 carteles (2026-10-09): gps_flotas 7/3/13, iot_frio 6/0/3, camaras_corporales
3/0/2. Desde entonces entraron 1 921 carteles y el único cambio de reglas fue la exclusión «intraoral» (sección 6).

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
- **Qué versión muestra el panel:** la de la última `evaluate` **completa**. `evaluate --nro` sirve para mirar un
  cartel con el YAML nuevo, pero no cambia el panel ni los avisos. Si se vuelve a un YAML anterior, basta un
  `evaluate` completo para que esa versión sea otra vez la vigente.
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

### 4.1 Precisión y cobertura por familia: `score-rules` (A3)

El acierto del golden set dice si el cartel completo salió bien. `score-rules` dice **qué familia** falla y **de qué
forma**:

- **Precisión:** de las alertas, ¿cuántas eran correctas? Si es baja, el correo trae ruido.
- **Cobertura:** de lo que sí interesaba, ¿cuánto se alertó? Si es baja, se pierden negocios.
- Mejorar una suele empeorar la otra: una exclusión nueva sube la precisión, pero puede bajar la cobertura. El
  equilibrio lo decide Oscar según qué le cuesta más a Hermatix: leer una alerta de más o perder un concurso.

```powershell
python -m app.cli score-rules                # tabla por familia, errores con su evidencia; guarda la medición
python -m app.cli score-rules --mostrar 50   # más errores
```

En el panel: Administración → «Calidad de reglas» (la misma medición, sin guardarla, y la evolución).

**Con qué compara** (código: `app/calidad.py`):

- El **golden set** (solo filas confirmadas), con la familia esperada de cada cartel.
- Las **revisiones del panel**: la última de cada cartel. Encaja si es «Interesa», «Revisar requisitos» u
  «Ofertada»; no encaja solo si es «No interesa» con el motivo «No encaja con el portafolio». Las demás (plazo,
  requisitos, presupuesto, «No se oferta») no cuentan: son decisiones de negocio. Las revisiones no dicen la
  familia, así que la cobertura **por familia** sale solo del golden set.
- Se mide con el YAML **actual**, sin pasar por `evaluate`: un cambio de reglas se ve en la medición siguiente.

**Cómo se lee un error:**

| Error | Qué pasó | Qué baja |
|---|---|---|
| Falsa alerta | El cartel no encaja y se alertó | La precisión de esa familia |
| Otra familia | El cartel encaja, pero también salió en una familia que no es la suya | La precisión de esa familia (no es ruido en el correo: el cartel interesa) |
| No alertado | Encajaba y no se alertó en su familia | La cobertura |

Cada medición queda guardada con su versión de reglas. Si se repite con la misma versión y los mismos resultados,
no se guarda otra. Así se ve la evolución: **antes y después de cada cambio del YAML**, corre `score-rules` y
compara (es el paso 4 de «Cómo medir el efecto»).

**Primera medición (2026-10-23, reglas `b880e0d350e1`, sobre una copia de la base real):** 34 casos del golden set
y 3 de revisiones. Total por cartel: precisión **95,0 %** (19/20), cobertura **100 %** (19/19).

| Familia | Precisión | Cobertura |
|---|---|---|
| `gps_flotas` | 100 % (10/10) | 100 % (9/9) |
| `iot_frio` | 83,3 % (5/6) | 100 % (5/5) |
| `camaras_corporales` | 100 % (3/3) | 100 % (2/2) |
| `rastreo_activos` | 50 % (1/2) | 100 % (1/1) |

Las otras 5 familias no tienen casos para medir. Los 2 errores:

- **Falsa alerta en `iot_frio`:** `20261000990` («telemetría… Acueducto Municipal»), revisado como «No interesa ·
  No encaja». «telemetria» es señal alta. **Propuesta lista (2026-10-26), pendiente de Oscar:** bajarla a señal
  media (sección 6, «Pendiente de decidir con Oscar»).
- **Otra familia en `rastreo_activos`:** `20260802605` (RFID para combustible + rastreo GPS) interesa por
  `gps_flotas`, pero «RFID» y «etiquetas inteligentes» lo ponen también en Media en `rastreo_activos`.

**Límite:** son pocos casos (34 del golden set y 3 revisiones), así que un solo error mueve mucho el porcentaje de
una familia. La cifra sirve sobre todo para comparar antes y después de un cambio. Con más revisiones en el panel,
la medición se vuelve más confiable.

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
| Palabra con otro sentido: equipo médico | «Cámaras intraorales… y carros para transporte para equipo médico» (CCSS) daba Media por «cámaras» + «transporte» | Exclusión precisa («intraoral»), no «equipo medico»: en el título anularía también «cámaras a bordo para ambulancias y equipo médico» |
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
| 2026-10-20 | `b880e0d350e1` | videotelematica | Exclusión «intraoral» (falso positivo CCSS `20261001749`, cámaras dentales); el cartel entra al golden set como falso positivo. Se descartó «equipo medico» (riesgo con ambulancias) | Ivania | `20261001749` pasa de Media a Sin coincidencia; el OIJ (`20260903798`) sigue Alta; ningún cartel entra. Golden set 34/34 = 100 %. Predicción simulada antes sobre los 11 829 carteles y cumplida |
| 2026-10-28 | `7ff3fd001247` | todas (9) | Exclusión «consultoria» en las 9 familias: Hermatix no da consultorías ni asesorías (ya decidido el 2026-10-12 con `20260700980`). Caso: `20260800923`, consultoría para la terminal de contenedores de Moín (TCM), Media en rastreo_activos por «contenedores» (título) + «trazabilidad» (PDF); entra al golden set como falso positivo | Ivania | `20260800923` pasa de Media a Sin coincidencia (rastreo_activos) y de Baja a Sin coincidencia (conteo_pasajeros); 35 → 34 candidatos; ningún otro cartel cambia. Golden set 35/35 = 100 %. Simulado antes en memoria (Claude) sobre los 13 162 carteles, con título, líneas y PDF: 43 dicen «consultoría», solo cambia este. Ivania no escribió predicción propia. Riesgo aceptado: un título «monitoreo GPS y consultoría…» también quedaría fuera |

### Pendiente de decidir con Oscar

- Los 4 provisionales del golden set se confirmaron el 2026-10-12.
- **«telemetria» en `iot_frio` (propuesta del 2026-10-26, Ivania con Claude; pendiente de Oscar).**
  - **Caso** (paso 1 de la sección 3): `20261000990`, «Solución integral de telemetría para el monitoreo en tiempo
    real y control remoto de los sistemas del Acueducto Municipal». Sale **Alta** en `iot_frio` y la revisión dice
    «No interesa · No encaja». Es la falsa alerta que encontró `score-rules` (sección 4.1).
  - **Causa** (paso 2): `evaluate --nro 20261000990` → `senales_alta: telemetria`, evidencia «telemetría»
    (título). Una señal alta basta sola para marcar Alta.
  - **Pregunta para Oscar:** ¿Osmia IoT vende telemetría para acueductos (sensores de nivel, bombas)?
    - **Sí:** el cartel encajaba y hay que corregir la revisión, no la regla.
    - **No:** se aplica el cambio propuesto.
  - **Cambio propuesto** (paso 3): pasar «telemetria» de `senales_alta` a `senales_media` en `iot_frio`. Sola da
    Baja (no se avisa, pero se ve en el panel con «Todas»); junto a otra señal o a un contexto, como «vacunas», da
    Media y sí se avisa.
  - **Simulado en memoria** (2026-10-26, base local en solo lectura, 12 260 carteles; el YAML real sin tocar): solo
    3 carteles mencionan «telemetría» y solo cambia el falso positivo.

    | Cartel | Hoy | Con el cambio |
    |---|---|---|
    | `20261000990` Acueducto | Alta | Baja |
    | `20260802530` telemetría cardiaca | sin coincidencia (exclusión «rehabilitacion») | igual |
    | `20260700797` calibradores de proceso | sin coincidencia (exclusión «calibradores de proceso») | igual |

    En `gps_flotas` no cambia nada: ya era señal media. El golden set no tiene casos que dependan de «telemetria»
    como señal alta.
  - **Descartado:** exclusión «acueducto». Sería ajustar la regla a un solo caso (sobreajuste) y dejaría fuera de
    `iot_frio` cualquier compra de un acueducto, aunque sí le interesara a Hermatix.
  - **Si Oscar aprueba,** siguen los pasos 4 a 8: predicción escrita por Ivania, YAML con comentario (quién y
    cuándo), `score-rules` y pruebas, y la fila en la tabla de arriba.

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
