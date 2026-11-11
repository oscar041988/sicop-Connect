# Decisión: usar IA (API de OpenAI) para el Reporte de cartel Hermatix

**ACEPTADO por Oscar el 2026-10-29 (comunicado por Ivania).** Redactado por Ivania con Claude el 2026-10-28.
Lo marcado **[por decidir · Oscar]** todavía no está decidido; no se llena hasta que él lo diga.

Guía de construcción: `docs/Guia_Reporte_Cartel_IA_SICOP.docx` (traída por Luis). Qué se envía al modelo y qué
nunca: `docs/RESUMEN_IA.md`.

## 1. Problema

Con el enriquecimiento, cada cartel de interés trae su ficha de SICOP y el texto de sus PDF: pliegos de decenas o
cientos de páginas que nadie alcanza a leer a diario. Las reglas de palabras clave dicen **si** un cartel puede
interesar, pero no **qué piden**, qué requisitos excluyen ni qué plazos y garantías exigen. Hoy eso exige leer el
pliego completo.

## 2. Qué se propone

Conectar SICOP CONNECT con un modelo de OpenAI para que lea el expediente de cada cartel (datos del cartel,
líneas, ficha de SICOP y texto de los PDF) y genere el **Reporte de cartel Hermatix**: máximo 2 páginas con los
indicadores clave, los requerimientos con su cita al documento y página, y una recomendación **preliminar**.

Cambia una regla del proyecto: `CLAUDE.md` dice «Sin API de IA». Con esta decisión se usa la API de OpenAI,
**solo** para el reporte y con las reglas de la sección 4.

## 3. Decisión

- Fecha: 2026-10-28 (comunicada por Ivania).
- Opción aceptada: **ampliación «Reporte de cartel Hermatix con IA»**, en las 5 lecciones de la guía.
- Decidió: Oscar.
- Comentarios:
  - Se construye y se prueba **en local**, como el enriquecimiento; el servidor se actualiza al final.
  - La lección 1 (expediente) ya está hecha y no llama a OpenAI (commit `77e0ed9`).

## 4. Reglas (las «reglas de oro» de la guía)

1. Los indicadores que ya están en SICOP (monto estimado, líneas, unidades, fechas, estado) los **calcula la
   app**, nunca el modelo.
2. Solo se envía **información pública de SICOP** (y el portafolio de Hermatix). Nunca decisiones, comentarios,
   usuarios, seguimientos ni datos internos (`docs/RESUMEN_IA.md` §2).
3. La clave de OpenAI **nunca** va a Git, a Claude ni a un chat: vive en `.env` (local) y en `/etc/sicop-connect`
   (servidor). Si se filtra, se revoca de inmediato.
4. **Límite de gasto** mensual en OpenAI y **presupuesto diario** en la app.
5. El resumen **no inventa**: lo que no está en los documentos es «no encontrado», y cada requisito cita su
   documento y página.
6. La recomendación es **preliminar**: decide el encargado. La IA complementa a las reglas, no las reemplaza.
9. El reporte tiene **máximo 2 páginas** y se entiende **sin conocer el proyecto ni SICOP**: alguien nuevo en
   Hermatix lo lee y sabe qué piden, qué falta y qué hacer (pedido explícito de Oscar en la reunión, comunicado por
   Ivania el 2026-10-29). Se aplica en el prompt (lección 3) y en el diseño (lección 4).
   **Cambio del 2026-11-09 (Oscar, por Ivania): hasta 3 páginas.** Al final va «Por qué se recomienda»: unos media
   página que explican en detalle la recomendación (las tres: dar seguimiento, revisar requisitos y descartar), con
   citas. La escribe el modelo en el mismo resumen (prompt v6, campo `explicacion_recomendacion`); migración 0039.
   Prompt v7 (Ivania, mismo día): igual, sin mencionar documentos que no se pudieron leer.
7. Las pruebas automáticas usan siempre un **modelo simulado** (no gastan dinero).
8. Con la IA apagada (`AI_MODE=none`), el sistema funciona igual que antes.

## 5. Para decidir con Oscar

| Tema | Decisión | Lección |
|---|---|---|
| Presupuesto mensual de OpenAI (límite de gasto del proyecto) | **Sin límite**: Oscar lo dejó así a propósito (2026-10-29, por Ivania). **Choca con la regla 4**; el único freno será el presupuesto diario de la app (lección 5). Riesgo anotado | 2 |
| Presupuesto diario en la app: resúmenes por día (`IA_MAX_SUMMARIES_PER_DAY`) y costo máximo (`IA_MAX_DAILY_COST`) | **Provisional (Ivania, 2026-10-30): 10 resúmenes y 1.00 USD al día**, hasta que Oscar decida. **[por decidir · Oscar]** | 5 |
| Cuenta de la API a nombre de Hermatix y proyecto «SICOP CONNECT» | Proyecto creado por Oscar (2026-10-29, por Ivania) | 2 |
| Quién genera y guarda la clave; entrega en persona | La generó Oscar y se la pasó a Ivania (2026-10-29); Ivania la escribe en su `.env`. Clave **con todos los permisos** y todos los modelos (Oscar) | 2 |
| Modelo (`OPENAI_MODEL`), según calidad y precio de la documentación oficial de OpenAI | Oscar no fijó uno (2026-10-29): **lo elige Ivania** con la tabla de precios. **[por decidir · Ivania]** | 2 |
| Qué datos se envían y cuáles nunca: confirmar la lista de `docs/RESUMEN_IA.md` §2 | **[por decidir · Oscar]** | 1 |
| Datos de personas **dentro del texto de los PDF** (nombres, cargos, firmas, correos y teléfonos de funcionarios que publica la institución; aparecen en 13 de 15 carteles, `RESUMEN_IA.md` §2): ¿se envían porque son públicos, o se filtran los correos y teléfonos antes de enviar? | **Se envían** tal cual: son documentos públicos que la institución publica en SICOP. Decidió Ivania, 2026-10-28; Oscar aceptó el documento el 2026-10-29 | 1–2 |
| Tamaño máximo del expediente (`IA_MAX_INPUT_TOKENS`; hoy 50 000 tokens) | **[por decidir · Oscar + Ivania]** | 1 |
| Qué carteles reciben reporte (¿solo Alta y Media? ¿también Baja?) | **Ivania (2026-10-30): Alta, Media y Baja (todos los del panel) ya enriquecidos**, con plazo abierto, hasta que Oscar decida. **[por decidir · Oscar]** | 5 |
| Criterio de Hermatix para el prompt: productos de interés, montos mínimos, requisitos que descartan una oferta | **Dado por Ivania (2026-10-30), prompt `v2`:** decide qué piden; monto, cantidad, garantías y plazo de entrega no importan (se negocian); 14 años de funcionamiento; marcas Wialon y Howen. Detalle en `RESUMEN_IA.md` §4 | 3 |
| Diseño de las 2 páginas y logo oficial | Máximo 2 páginas, fácil para alguien nuevo (regla 9, Oscar). Diseño y logo: **[por decidir · Oscar]** | 4 |

### Privacidad (dato de la guía, a confirmar en la documentación vigente de OpenAI)

Según la guía, los datos enviados por la API no se usan para entrenar los modelos salvo que la cuenta lo
autorice, y OpenAI los guarda hasta 30 días para vigilar abusos. Por eso solo se envía información pública.
**Confirmado por Oscar (2026-10-29, por Ivania):** revisó las condiciones de privacidad en la cuenta de Hermatix.

## 6. Aceptación

- [x] Oscar leyó este documento y acepta la decisión y las reglas (fecha: 2026-10-29, comunicado por Ivania).
- [ ] Las filas de la sección 5 de las lecciones 1 y 2 están decididas antes de la lección 2. Faltan: modelo,
  límite de gasto (regla 4) y tamaño del expediente.
- [x] `CLAUDE.md` actualizado: «Sin API de IA» → la excepción de este documento (2026-10-29).

## 7. Ampliación: asistente de elegibilidad

**APROBADO por Oscar el 2026-11-02 (comunicado por Ivania).** Guía: `docs/Guia_Asistente_Elegibilidad_SICOP.docx`.

- **Qué se aprueba:** usar la API de OpenAI también en el asistente de elegibilidad: armar la lista de verificación
  del cartel (lección 2), hacer las preguntas al encargado (lección 3) y explicar el resultado (lección 4).
- **Cambia la regla 2 solo para el asistente:** además de la información pública de SICOP, se envían la lista de
  verificación y las **respuestas escritas** del encargado (datos internos de Hermatix, como los años de
  experiencia). Nunca contraseñas, usuarios ni datos personales.
- **Documentos de Hermatix** (permisos, certificaciones, estados financieros): **no se envían** mientras
  `ASSISTANT_SEND_DOCUMENTS=false`. Enviarlos o no: **[por decidir · Oscar]**. Hoy (lección 3, 2026-11-03) solo
  existe el camino false: las preguntas del asistente se redactan con la lista de verificación y nada más; con
  true la app avisa que ese camino falta y no guarda ni envía nada.
- **Reglas del asistente** (las de la guía): nunca supone, lo que no está confirmado lo pregunta; los números y las
  fechas los compara la app, no la IA; el resultado es una orientación y decide el encargado; los documentos de
  Hermatix van fuera de Git, en el respaldo, con permisos y registro de cada acceso; pruebas siempre con IA simulada.
- **Quién usa el asistente y ve el perfil:** los dos niveles, Administrador y Encargado (Oscar, 2026-11-02, por
  Ivania).
- El costo se suma al presupuesto diario de la sección 5.
- **Decisiones de Oscar del 2026-11-04 (reunión con Ivania):**
  - Documentos de Hermatix: **solo en el servidor**, cuando esté actualizado (no en la laptop). Mientras tanto,
    «Lo tiene · archivo pendiente».
  - Texto de esos documentos a la IA: **no**; `ASSISTANT_SEND_DOCUMENTS` sigue en `false`.
  - Presupuesto diario: se deja en **1.00 USD** (`IA_MAX_DAILY_COST`).
  - Resumen v3: **probarlo en 3 carteles** y comparar antes de activarlo para todos.
    Resultado (`docs/comparacion_resumen_v3_20261104.md`): v3 y v4 fallaron; el **v5** funcionó. **Activado por
    Ivania el 2026-11-05** (`IA_PROMPT_VERSION=v5`), provisional hasta que Oscar lo confirme.
  - Reglas del resultado (lección 4): **de acuerdo** con las dos (archivo pendiente → «si completan»; excluyente
    en «Revisar» sin decidir → «Falta información»).

## 8. Ampliación: cambio a la API de Anthropic (aprobado por Oscar, 2026-11-05, comunicado por Ivania)

- **Aprobado:** usar la API de Anthropic (Claude) en lugar de la de OpenAI para el resumen, la lista de
  verificación, las preguntas del asistente y la explicación del resultado. Valen las mismas reglas de las
  secciones 4 y 7 (qué se envía y qué nunca, presupuesto diario, la app calcula y la IA solo explica).
- **Transición:** primero se termina el saldo ya comprado en OpenAI. La app tendrá las dos opciones y se elige con
  `AI_MODE` (`openai` · `anthropic` · `none`); el cambio es una línea del `.env`, sin tocar código.
- **Al cerrar OpenAI (Oscar):** apagar la recarga automática si existe, revocar la clave de la app y revisar si el
  saldo vence.
- **[por decidir · Oscar]:** el modelo de Anthropic y sus precios (se comparan en 3 carteles antes de cambiar), y la
  fecha del cambio.
- **Construido (2026-11-11, Ivania con Claude):** `AI_MODE=anthropic` en `app/ai/cliente.py`, junto a OpenAI, con
  el SDK oficial `anthropic` 2.8.0. Configuración: `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL` y `ANTHROPIC_EFFORT`
  (opcional: cuánto razona el modelo; ese razonamiento cuenta dentro de `IA_MAX_OUTPUT_TOKENS`). Las instrucciones
  van como «system», el texto como mensaje y la salida estructurada con el mismo JSON Schema. Mismos reintentos,
  mismo registro en `ia_usage` y el mismo presupuesto diario; los precios `IA_PRECIO_*` son los del modelo activo.
  Pruebas con Anthropic SIMULADO en `tests/test_ia_anthropic.py` (regla 7). **Todavía no se llamó a la API real.**
  - Sin «fallbacks» (pasar a otro modelo si el elegido se niega): cambiaría el modelo y el costo sin que Oscar lo
    decida. Un rechazo queda como fallo «rechazo del modelo» y la app sigue sin IA, como hoy.
  - **Falta (Oscar con Ivania):** la clave de Anthropic con límite de gasto, el modelo y los precios en el `.env`;
    `ia probar`; y la comparación en 3 carteles. Antes de esa comparación, revisar que los esquemas de salida
    (`FORMATO` de cada módulo) los acepte Anthropic: si no, la llamada sale «BadRequestError 400».

## 9. Ampliación: la IA en la oferta completa (pedido de Oscar, comunicado por Ivania, 2026-11-10)

Oscar quiere que la oferta salga con un solo botón, sin formulario, con la forma de la de NAVSAT
(`DECISION_PROPUESTA.md` §12). La IA hace **una sola cosa**: marcar dónde empieza cada sección del pliego (número,
título, DOC y página, las primeras palabras copiadas tal cual) y si la respuesta es «cumple» o «acepta»
(`app/ai/oferta.py`, prompt `config/prompts/oferta_secciones_v1.md`, propósito `oferta` en `ia_usage`, migración 0043).

- **Lo que la IA no hace:** no copia ni reescribe el pliego (lo copia la app del texto original); no decide si
  Hermatix cumple (lo decide la app con el asistente de elegibilidad, y lo que no cumple sale en rojo); no pone
  precios (salen del tarifario de Oscar, `config/tarifario.yaml`); no ve documentos de Hermatix.
- **Lo que se le envía:** solo el texto público del pliego (documentos de SICOP), igual que en el resumen (regla 2).
- **Control:** cada sección se comprueba contra el texto de su página; la que no coincide se descarta. Con la IA
  apagada, sin presupuesto o si falla, la oferta sale igual con el pliego entero en una sola sección.
- **Costo:** una llamada por pliego; con el mismo pliego no se repite (caché por huella). Cuenta en el presupuesto
  diario (`IA_MAX_DAILY_COST`).
- Pruebas con IA SIMULADA (`tests/test_propuesta.py`), regla 7.

## 10. Ampliación: el asistente como chat y la oferta corregida conversando (pedido de Oscar, comunicado por Ivania, 2026-11-11)

**APROBADO por Oscar el 2026-11-11 (comunicado por Ivania), después de ver la maqueta.** Redactado por Ivania con
Claude el mismo día. Lo marcado **[a confirmar · Oscar]** se precisa mientras se construye.

### 10.1 Qué pide Oscar

1. El asistente de elegibilidad deja de ser una pregunta tras otra y pasa a ser un **chat** en la página del cartel,
   como el de Claude o ChatGPT: la IA pregunta por los requisitos y la persona contesta, escribe dudas o sube archivos.
2. En el mismo chat, la persona le dice **qué cambiar y qué no** en la oferta, y cómo mejorar el diseño.
3. Cuando no falta nada, el chat dice **«Ya está listo»** y la persona pide la **oferta completa** (§9 y
   `DECISION_PROPUESTA.md` §12), con todos los documentos subidos en la conversación, como la de NAVSAT.
4. Con la oferta hecha, Oscar la revisa y vuelve a decir en el chat qué cambiar; la app arma otra versión.
5. Gasta más en la API: Oscar dijo que **no hay problema** (falta fijar el tope, 10.5).

### 10.2 Qué cambia respecto a lo aprobado

Hoy la IA **no escribe nada de la oferta**: solo marca dónde empieza cada sección (§9). Con el chat, la IA
**propone cambios** a la oferta. Para que eso sea seguro, la IA no edita el PDF ni el texto directamente: elige
de una **lista cerrada de acciones** («herramientas») y la app las comprueba y las aplica. Ejemplo:

> Oscar escribe «quita la sección 5» → la IA pide `quitar_seccion(5)` → la app la quita y guarda la versión 2.
> Si pide algo que no está en la lista, la IA responde «eso no lo puedo cambiar» y no pasa nada.

### 10.3 Reglas que se proponen

Siguen todas las de las secciones 4, 7 y 9. Además:

1. **Qué hace el chat y qué puede cambiar (decidido por Oscar, comunicado por Ivania, 2026-11-11):**
   - El chat **es el asistente de elegibilidad**, como el de hoy: toma la información de los documentos del cartel
     y pide todo lo necesario para hacer la oferta.
   - **Solo puede modificar el documento de la oferta.** No puede cambiar ningún archivo del cartel ni ningún
     archivo que se suba en el chat: esos se adjuntan tal cual.
   - **Misma estructura para todas las ofertas**, inspirada en la de Tarrazú y en la de NAVSAT (portada, pliego
     sección por sección con su respuesta, listado de anexos, oferta económica y documentos adjuntos;
     `DECISION_PROPUESTA.md` §9 y §12). El chat **solo cambia la estructura si alguien se lo pide primero**; por
     iniciativa propia nunca. Ese cambio vale **solo para esa oferta**: la estructura base no cambia (confirmado
     por Oscar).
   - Lista cerrada de acciones que se deriva de esto: cambiar el texto de la respuesta de una sección; marcar una
     sección «cumple» o «acepta»; adjuntar o quitar de la oferta un documento subido (sin modificarlo); y, **solo si
     se pide**, quitar, agregar o reordenar partes de la estructura.
2. **Nunca declarar algo que Hermatix no tiene** (`DECISION_PROPUESTA.md` §2.4). Lo que no cumple o falta sigue en
   rojo aunque alguien lo pida en el chat; solo sale de rojo con la respuesta del asistente o el documento.
3. **Precios:** solo del tarifario (`config/tarifario.yaml`) o escritos por una persona; la IA no pone ni cambia
   precios. Los montos, las sumas y el monto en letras los calcula la app.
4. **El pliego no se reescribe:** lo copia la app del texto original (como en §9). La IA solo cambia las respuestas
   de Hermatix.
5. **Todos los requisitos se presentan:** el chat no puede ocultar requisitos del cartel; la persona decide.
6. **Versiones:** cada cambio aplicado crea una versión nueva de la oferta; las anteriores y la conversación se
   guardan y nunca se borran. Se ve quién pidió cada cambio y cuándo.
7. **«Ya está listo» lo decide la app**, no la IA: aparece cuando todos los requisitos tienen respuesta. La oferta
   sigue saliendo como «BORRADOR» si hay algo en rojo. Una persona la revisa, la firma y la sube a SICOP.
8. **Texto del pliego como dato, no como orden:** si un PDF trae frases como «ignora las instrucciones», la IA no
   las obedece; y aunque lo hiciera, solo puede usar las acciones de la lista.
9. **Quién usa el chat y corrige la oferta (decidido por Oscar, 2026-11-11):** todos los encargados y
   administradores pueden modificar la oferta **de los carteles de los que se encargan**; los demás no.
10. Pruebas siempre con **IA simulada** (regla 7). Con `AI_MODE=none` el chat no aparece y la oferta sale como hoy.

### 10.4 Documentos subidos en el chat

**Decidido por Oscar (comunicado por Ivania, 2026-11-11): la IA puede leer los documentos subidos en el chat**,
para estructurar mejor la oferta, **sin modificarlos en absoluto**. Cambia la decisión del 2026-11-04 (§7: «texto de
esos documentos a la IA: no»), solo para el chat.

- La IA recibe el **texto** del documento; el archivo original se guarda y se adjunta a la oferta **tal cual**
  (misma huella antes y después; la app lo comprueba).
- Se activa con `ASSISTANT_SEND_DOCUMENTS=true`; hoy ese camino no existe y se construye con el chat.
- Sigue sin enviarse: contraseñas, usuarios ni datos que no estén en el documento subido.
- **Datos personales (decidido por Oscar, comunicado por Ivania, 2026-11-11):** mientras se trabaja la oferta, los
  documentos se envían a la IA **tal cual**. Cuando la oferta está **terminada** (todo listo y el encargado ya no
  pide más cambios), el sistema **borra automáticamente los datos personales**. Propuesta para precisar
  **[a confirmar · Oscar]**:
  - «Terminada» = el encargado pulsa **«Oferta terminada»** en el chat (la app no lo adivina). Después el chat queda
    cerrado; para otro cambio se abre una oferta nueva.
  - Se borran: el texto que la IA leyó de los documentos y los datos personales escritos en la conversación
    (cédulas, teléfonos, correos, firmas), que quedan como «[dato personal borrado]». Los mensajes no se borran
    (regla «nunca borrar revisiones humanas»): solo se tapa el dato.
  - Se conservan: la oferta final (PDF y Word) y los archivos originales adjuntos, porque son la oferta que se
    presenta en SICOP.
- **[a confirmar · Oscar]:** ¿sigue valiendo que los documentos reales se guarden **solo en el servidor** (§7)?
  Mientras tanto, en la laptop se prueba con documentos **SINTÉTICOS** (de prueba).

### 10.5 Costo

Un chat **reenvía toda la conversación** en cada mensaje: el décimo mensaje cuesta más que el primero. Además se
envía el pliego (ya está en el resumen). Con el tope actual de **1.00 USD al día** (`IA_MAX_DAILY_COST`) no alcanza
para conversar con varios carteles.

- Tope **por día** (decidido por Oscar, 2026-11-11), sin tope por cartel. Monto **durante las pruebas: 5 USD al día**
  (Oscar lo dejó a criterio de Claude, 2026-11-11): con el modelo de OpenAI actual un cartel cuesta ≈ 1 USD (la
  mitad que Sonnet 5.5), así que alcanza para 3 carteles de prueba más los resúmenes. El monto definitivo se fija
  con el costo medido y el modelo elegido.
- Al llegar al tope, el chat avisa «presupuesto del día agotado» y no llama a la IA; lo ya hecho no se pierde.
- Cada mensaje se anota en `ia_usage` con el propósito `chat`, para ver cuánto gasta cada cartel.
- Antes de construir, se mide el costo real en 3 carteles con conversaciones de prueba y se le muestra a Oscar.

**Estimación (Ivania con Claude, 2026-11-11; ESTIMADA, no medida).** Base real: en `ia_usage`, un pliego que lee la
IA tiene en promedio ≈ 27 000 tokens de entrada (64 resúmenes) y un resumen cuesta ≈ 0.04 USD con el modelo de
OpenAI. Supuestos por cartel: ≈ 50 000 tokens fijos (pliego, documentos subidos e instrucciones), ≈ 30 mensajes de
conversación, la oferta generada y 2 rondas de correcciones; con caché (el pliego se cobra completo la primera vez
y después a una décima parte). Escenario: **3 carteles al día**, 22 días hábiles al mes.

| Modelo de Anthropic | Por cartel | 3 carteles al día | Al mes |
|---|---|---|---|
| Claude Haiku 5.5 (el más barato) | ≈ 0.10 USD | ≈ 0.30 USD | ≈ 7 USD |
| **Claude Sonnet 5.5** | **≈ 2 USD** | **≈ 6 USD** | **≈ 130 USD** |
| Claude Opus 5.5 (el más capaz) | ≈ 4 USD | ≈ 12 USD | ≈ 260 USD |

Precios por millón de tokens según la documentación de Anthropic (confirmar en la cuenta antes de decidir): Sonnet
5.5, 2 USD de entrada y 10 de salida; Opus 5.5, 4 y 20; Haiku 5.5, 0.10 y 0.50.

- **Recomendación: Claude Sonnet 5.5 con un tope de 8 USD al día** (≈ 6 USD de chat + 1 USD de los resúmenes de
  hoy + margen). Opus cuesta el doble; Haiku arriesga la calidad de una oferta que se presenta a una institución.
  Si en la medición Sonnet se equivoca, se compara con Opus. Lo decide Oscar.
- **Costo medido (2026-11-11, 4 mensajes reales con OpenAI):** 0.0026–0.0047 USD por mensaje (2 200–3 900
  tokens de entrada, 75–160 de salida; 4–5 s). Un cartel de ≈ 30 mensajes: **≈ 0.10 USD**, diez veces menos que la
  estimación de arriba, porque el chat no manda el pliego completo (solo sus requisitos con la cita). Al empezar el
  asistente se gastan además ≈ 0.05 USD una vez (lista de verificación y preguntas).
- Sin caché cada cartel costaría ≈ 4 veces más. La caché dura unos minutos: si el chat queda quieto media hora, el
  siguiente mensaje vuelve a pagar el pliego completo (incluido en el margen).

### 10.6 Anthropic u OpenAI

`AI_MODE=anthropic` ya está en la app (§8, 2026-11-11). La API de Anthropic guarda en caché la parte que no cambia
(pliego e instrucciones), y eso baja el costo de cada mensaje.

**Decidido por Oscar (comunicado por Ivania, 2026-11-11):** las pruebas del chat se hacen **con OpenAI**, para
gastar primero el saldo que queda. El modelo de Anthropic lo dice Oscar **después de las pruebas**.

### 10.6 bis La oferta también en Word

**Pedido de Oscar (comunicado por Ivania, 2026-11-11):** además del PDF, la oferta sale en **Word (.docx)**: el mismo
documento, en otro formato, para poder editarlo a mano si hace falta.

- Mismo contenido y misma estructura que el PDF: portada, secciones, anexos, oferta económica y documentos. Lo que
  está en rojo o dice «BORRADOR» en el PDF sale igual en el Word.
- Los documentos adjuntos (PDF de Hermatix) no se pueden meter como PDF dentro de un Word: van **como imagen de
  cada página** (130 dpi), así el Word es el mismo documento completo. El archivo original solo se lee, nunca se
  cambia, y el PDF de la oferta lo sigue llevando tal cual. **[a confirmar · Oscar]**
- Necesita una dependencia nueva, `python-docx` (escribe archivos de Word desde Python, sin Word instalado). Se
  justifica por este pedido; se agrega con el mismo cuidado que `anthropic` (entorno limpio y ruedas para Linux).
- No depende del chat: se puede construir antes, sobre la oferta de hoy (`DECISION_PROPUESTA.md` §12).

### 10.7 Orden de construcción (una tarea a la vez, en local)

1. Este documento aprobado por Oscar.
2. ~~Anthropic en `app/ai/cliente.py`, junto a OpenAI (§8)~~ **hecho (2026-11-11).**
2 bis. ~~La oferta también en Word (10.6 bis)~~ **hecho (2026-11-11):** botón «Oferta en Word»
   (`app/propuesta_word.py`, `python-docx` 1.2.0), sin migración.
3. ~~El chat de elegibilidad en el cartel, con subida de archivos y «Ya está listo» → botón «Oferta». Reemplaza a las
   preguntas actuales; las respuestas ya guardadas no se tocan.~~ **Hecho (2026-11-11):** `app/ai/chat.py`, plantilla
   `_chat.html`, prompt `config/prompts/chat_asistente_v1.md`, migración **0044** (`asistente_chat`; `ia_usage`
   acepta `chat`). Se enciende con `ASSISTANT_CHAT=true` (con la IA encendida); apagado, el asistente de siempre.
   - **Cómo funciona:** la IA lee el mensaje y **propone** respuestas (salida estructurada: requisito, estado, valor,
     vencimiento y si usa el archivo). La app las guarda con `asistente.responder`, con las mismas validaciones que
     el formulario: un documento no queda «respondido» sin el archivo, aunque se pida. Lo guardado y la pregunta
     siguiente los escribe **la app**, no la IA. Cada respuesta lleva la nota «Desde el chat del asistente.».
   - **A la IA va:** el cartel (número y objeto), los requisitos con su cita y su respuesta actual, los últimos 30
     mensajes y el mensaje nuevo; con `ASSISTANT_SEND_DOCUMENTS=true`, el texto del archivo (hasta 15 000
     caracteres). No va el pliego completo (sí sus requisitos con la cita) ni el perfil: el dato vigente del perfil
     se confirma con el botón «Sí, es correcto», como siempre. Por eso cuesta menos que la estimación de 10.5.
   - Pruebas con IA SIMULADA: `tests/test_chat_asistente.py` (11).
   - **Primera prueba con la IA real (Ivania, 2026-11-11, cartel 20261001587, OpenAI):** no inventó nada («sí,
     cumplimos» no cumplió un requisito de documento), leyó un archivo que no correspondía y no lo usó, y contestó
     una duda con la cita. Faltaba: cómo avanzar sin la respuesta (se quedó en la pregunta 1), la pregunta se
     repetía entera, traía 10 citas y mezclaba «vos» con «usted». **Corregido el mismo día:** prompt
     `chat_asistente_v2.md` (trato de usted; «lo subo después» / «no lo tenemos» / «no sé» avanzan; la IA recibe la
     PREGUNTA ACTUAL), la pregunta dice cómo avanzar, no se repite entera y muestra como máximo 2 citas seguidas.
     4 pruebas nuevas (15 en total).
4. Corregir la oferta desde el chat: acciones de 10.3.1 y versiones de la oferta (migración nueva).
5. «Oferta terminada» y el borrado de datos personales (10.4).
6. Medir el costo con Oscar y ajustar el tope.

### 10.8 Riesgos

- **Más gasto** del previsto si las conversaciones son largas (lo frena el tope de 10.5).
- **La IA entiende mal un pedido** y cambia otra sección: cada versión se puede comparar con la anterior y
  volver atrás.
- **Confiar demasiado en «Ya está listo»:** sigue siendo un borrador; la revisión y la firma son de una persona.
- **Más tiempo de construcción:** son 4 tareas, no una; el resto del proyecto (servidor, fichas técnicas) espera.

### 10.9 Aceptación

- [x] Oscar leyó esta sección y acepta las reglas de 10.3 (fecha: 2026-11-11, comunicado por Ivania).
- [x] Qué hace el chat y qué puede cambiar (10.3.1) y quién corrige la oferta (10.3.9): Oscar, 2026-11-11.
- [x] Documentos a la IA (10.4: sí, sin modificarlos) y tipo de tope (10.5: por día): Oscar, 2026-11-11.
- [x] Oscar vio la maqueta del chat y le gustó (comunicado por Ivania, 2026-11-11):
  https://claude.ai/artifact/49wN3PpodRhAaamFwnEPtQ (datos SINTÉTICOS).
- [x] Datos personales (10.4: tal cual mientras se trabaja; se borran al terminar la oferta), tope durante las
  pruebas (10.5: 5 USD al día), pruebas con OpenAI (10.6) y oferta también en Word (10.6 bis): Oscar, 2026-11-11.
- [ ] Faltan: precisar «terminada» y qué se borra (10.4), dónde se guardan los documentos reales (10.4), los
  adjuntos en el Word (10.6 bis) y el modelo de Anthropic después de las pruebas (10.6).
