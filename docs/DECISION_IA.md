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
