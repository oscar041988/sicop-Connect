# Decisión: ¿se puede automatizar la descarga de SICOP? (A1)

**DECIDIDO (2026-10-21): obtención automática completa, aprobada por Oscar.** Ver la sección 6 (decisión) y la
sección 8 (reglas nuevas). La guía de construcción es `docs/Guia_Obtencion_Automatica_SICOP.docx`.

Las secciones 1–5 y 7 son el análisis del 2026-10-20 y se conservan como historia. Se hicieron cuando la app
estaba pensada con una parte manual y bajo la regla de la guía original: «no se eluden códigos de validación,
CAPTCHA ni términos de uso». Con la aprobación de Oscar, **esa regla cambia para el código por correo**: el
código demuestra que Hermatix controla `licitaciones@hermatix.com`, y leerlo de su propio buzón no engaña a
nadie. **El CAPTCHA y los bloqueos siguen sin saltarse** (sección 8).

## 1. Problema

Hoy una persona descarga de SICOP el archivo de carteles y líneas y lo deja en la carpeta de entrada (o lo sube
desde el panel) antes de las 8:00. Si nadie lo hace, el ciclo de las 8:00 termina en «fallo · no llegó ningún
archivo nuevo» y no avisa. La pregunta es si el sistema puede obtener el archivo solo.

## 2. Evidencia (observada, `docs/ACCESO_SICOP.md`)

Descargas del 6, 7, 8, 9, 13 y 19/10, con Oscar, Anabelle e Ivania. Siempre el mismo flujo:

| Paso | Quién lo hace hoy | ¿Exige a una persona? |
|---|---|---|
| 1. Entrar al reporte y elegir el formato (CSV) | Persona | No necesariamente |
| 2. Escribir un correo en una ventana | Persona | No necesariamente |
| 3. Llega al correo un código de 6 caracteres (≈ 1 min) | SICOP | — |
| 4. Escribir el código en la ventana | Persona | **Sí: es un control de validación** |
| 5. Llega al correo el enlace de descarga (≈ 1 min) | SICOP | — |
| 6. Abrir el enlace y bajar el ZIP | Persona | No necesariamente |
| 7. Descomprimir y dejar los 2 CSV en la carpeta de entrada | Persona | No |

- **Cada solicitud pide un código nuevo** (observado los dos días que se probó).
- El enlace dura **al menos 3 h y menos de ≈ 16,5 h** (plazo exacto desconocido).
- El reporte se genera al pedirlo: un enlace reabierto entrega el mismo archivo.
- Sin filtros, el portal entrega ≈ 3 meses de publicaciones.
- **No se ha verificado ninguna API pública documentada** (guía 16.1). Las llamadas internas que hace el
  navegador no son una API autorizada ni estable.
- El ciclo no aceptaba el ZIP de «Detalle pliego de condiciones» y había que descomprimirlo (paso 7). Ya no hace
  falta desde la rama `zip-pliegos` (ver O4a).

**Conclusión de la evidencia:** el paso 4 es una validación pensada para una persona. Automatizarlo sería
eludirla, y la guía lo prohíbe. Por lo tanto, **ninguna opción permitida elimina a la persona en cada solicitud**.

## 3. Opciones, de la más robusta a la menos

### O1 · API oficial documentada

- Requiere: que SICOP publique una API con acceso para Hermatix.
- Evidencia: ninguna. **No viable hoy.** **Confirmado por SICOP (respuesta recibida el 2026-10-26, sección 8): no
  hay API, servicios web ni integración para terceros.**
- Lo único posible: preguntarle a soporte de SICOP si existe (la decisión de preguntar es de Hermatix;
  `ACCESO_SICOP.md` tiene la tabla de preguntas).

### O2 · Leer el buzón para el enlace (la persona sigue pidiendo y escribiendo el código)

La persona hace los pasos 1–4 (≈ 2 min). La app lee el correo con el enlace (paso 5), baja el ZIP, lo
descomprime y deja los CSV en la carpeta de entrada (pasos 6–7).

- Requiere:
  - permiso de **lectura** del buzón que recibe los correos de SICOP (`gmail.readonly`). Es mucho más amplio
    que el actual (`gmail.send`, solo enviar): la app podría leer **todo** el correo de esa cuenta;
  - saber qué buzón usa la descarga, el remitente y el formato del correo de SICOP (**pendiente de
    verificar**; no se anotan enlaces ni códigos en Git);
  - descomprimir el ZIP de pliegos.
- Qué puede romperse: que SICOP cambie el remitente, el texto del correo o el formato del enlace; que el
  enlace venza antes de leerse; que llegue un correo viejo y se baje un reporte que no es de hoy.
- ¿Intervención humana? **Sí, en cada solicitud** (pasos 1–4).
- Términos de uso: abrir el enlace que SICOP nos envía es el uso normal, pero hacerlo con un programa hay que
  revisarlo en los términos. Riesgo de privacidad por el permiso de lectura.
- Ahorro real: los pasos 6 y 7, unos minutos al día.
- Nivel que se podría declarar: **obtención asistida** (no automática).

### O3 · Navegador automatizado

Un programa que abre el portal, llena la ventana, lee el código del correo y lo escribe.

- *(2026-10-20)* Escribir el código por programa es **eludir la validación** (paso 4). **Descartada** por la
  regla de la guía, sin importar si técnicamente funcionara.
- **2026-10-21: aceptada por Oscar** (sección 6). El código se lee del buzón propio de Hermatix, con permiso de
  solo lectura; el riesgo de fragilidad se cubre con FALLO visible, capturas y vuelta al modo manual (sección 8).
- Además: es frágil (cualquier cambio del portal lo rompe sin avisar), necesita dependencias nuevas y tiene un
  riesgo alto con los términos de uso.

### O4 · Mejorar el modo asistido, sin permisos nuevos

- **a. Aceptar el ZIP de pliegos tal como llega**, en la carpeta de entrada y en el panel: elimina el paso 7.
  **Hecho 2026-10-20** en la rama `zip-pliegos` (`41cf4db`, PR para Oscar); en el servidor aplica al
  actualizarlo. El ciclo importa los dos CSV del ZIP (carteles y luego líneas) y mueve el ZIP entero a
  `procesados`, o a `con_error` si está dañado, le falta o le sobra un archivo, o un CSV viene cortado. El panel
  tiene el tipo de reporte «pliegos (.zip)». Con el ZIP real del 9/10, los dos CSV salieron «YA IMPORTADO»
  (#7 y #8): subir el ZIP o descomprimirlo a mano no duplica nada.
- **b. Recordatorio** a quien descarga si a cierta hora (por ejemplo, 7:30) no hay archivo nuevo. Usa el envío
  que ya funciona (`gmail.send`). Hay que decidir a quién y a qué hora.
- **c. Instrucciones cortas** en `docs/OPERACION.md` para la persona que descarga (ya existen en buena parte).

## 4. Recomendación provisional (2026-10-20, reemplazada por la decisión de la sección 6)

1. **O4a y O4b ahora**: quitan fricción sin permisos nuevos ni riesgos con los términos. O4a ya está hecho
   (2026-10-20, falta unirlo y actualizar el servidor); queda O4b.
2. **O2 solo si Oscar lo pide**, después de revisar los términos de uso y aceptar a conciencia el permiso de
   lectura del buzón. Aun así, sigue siendo asistido.
3. **O1**: preguntarle a soporte de SICOP si existe una API, si Hermatix lo decide.
4. **O3 no se hace.**

Nivel que se declara hoy: **obtención asistida; análisis y avisos automáticos** (guía 16.1). No se declara
«automático» hasta que un ciclo real lo demuestre.

## 5. Para decidir con Oscar

- ¿Qué dicen los términos de uso del portal sobre descargas con programas? (Revisarlos juntos.)
- ¿Quién descarga cada día hábil y a qué hora? ¿Qué buzón usa?
- O4a ya está hecho (rama `zip-pliegos`): ¿lo une? ¿O4b le parece bien? ¿A quién va el recordatorio y a qué hora?
- ¿Le interesa O2 a cambio de dar permiso de lectura del buzón?
- ¿Se le pregunta a soporte de SICOP si hay una API (O1)?
- **¿Avisar por correo cuando el ciclo falla?** Hoy un «FALLO» (no llegó el archivo, ZIP dañado, error de Gmail…)
  solo queda en `journalctl` y en `source_runs`: el ciclo no le avisa a nadie (`app/ciclo.py` solo llama a los
  avisos cuando todo salió bien). Si nadie revisa, una semana de fallos se ve igual que una semana sin
  oportunidades. Es más amplio que O4b (que solo cubre «no llegó el archivo»). ¿A quién se avisa?

## 6. Decisión

- Fecha: 2026-10-21 (comunicada por Ivania).
- Opción aceptada: **obtención automática completa** (O3 ampliada con el lector de Gmail de O2): la app pide el
  reporte en el portal, lee el código y el enlace del buzón `licitaciones@hermatix.com`, descarga el ZIP y lo
  deja en la carpeta de entrada para el ciclo.
- Decidió: Oscar.
- Comentarios:
  - Se construye y se prueba **en local** (decisión de Oscar del mismo día); el servidor se actualiza al final.
  - O4a (ZIP de pliegos) sigue sirviendo: es el formato que la obtención automática dejará en la carpeta.
  - El modo asistido (`SOURCE_MODE=manual`) se mantiene como plan B.
  - Queda abierto: O4b (recordatorio) y avisar por correo cuando el ciclo falla (sección 5); con la obtención
    automática, el aviso de FALLO pasa a ser parte de la lección 4 de la guía nueva.

## 7. Autoevaluación (guía, lección 11; la responde Ivania)

Respuestas de Ivania (2026-10-20), con ajustes de Claude: **las dos correctas.**

- **¿Por qué un resultado «no viable» también tiene valor?** Evita perder días construyendo un bot que intentara
  saltarse el código de validación de SICOP: habría violado los términos de uso y se rompería con cualquier
  cambio del portal. El documento deja registrado por qué se descartó, con la evidencia, para que nadie repita
  la investigación dentro de seis meses. Y orientó el esfuerzo hacia algo útil: el modo asistido mejorado (O4a),
  sin saltarse controles.
  *Ajustes:* O3 se descarta **aunque técnicamente funcionara**, porque elude la validación; esa es la razón de
  fondo. La decisión de Oscar todavía no está escrita (sección 6): hoy queda la evidencia y el razonamiento.
- **¿Qué riesgo tendría un adaptador que se rompe sin avisar?** Que el sistema falle en silencio y el equipo
  crea que no hay concursos mientras se pierden oportunidades reales. El mensaje de «FALLO» lo evita porque hace
  visible el problema el mismo día.
  *Ajuste:* hoy el «FALLO» solo es visible para quien lo busca (`journalctl`, `source_runs`); nadie recibe un
  correo. De ahí la pregunta para Oscar de la sección 5 (avisar cuando el ciclo falla).

## 8. Reglas de la obtención automática (desde 2026-10-21)

Reemplazan, solo para la obtención, la regla «no se eluden códigos de validación» de la guía original.

1. **El código por correo sí se automatiza**, leyéndolo del buzón propio de Hermatix.
2. **CAPTCHA, bloqueo o aviso del portal contra programas: la app se detiene** con FALLO «control no
   automatizable», no reintenta y se vuelve al modo manual. Eso no se salta nunca.
3. **Términos de uso: revisados el 2026-10-21 (Ivania con Claude), sin prohibición.** Ningún documento habla de
   programas, robots ni descargas automáticas. Documentos en `docs/normativa_sicop/`:
   - *Condiciones Generales de Uso* (`docs/. Condiciones Generales de Uso.txt`): 5c, no «sobrecargar» la
     plataforma (→ regla 4); 5d, no reproducir ni comercializar la información «ante terceros» (uso interno de
     Hermatix: sí; vender o compartir los datos fuera de Hermatix: no); 1e, pueden cambiar en cualquier momento
     (releerlas al desplegar).
   - *Lineamientos de seguridad del SDU* (Hacienda, 2023): las consultas públicas sin autenticación quedan fuera
     de las exigencias de firma digital (6.1, art. 2); conexión segura y navegador HTML 5 (art. 3); SICOP puede
     bloquear conexiones por «comportamiento de navegación» o «cantidad de consulta por periodo» (6.2, art. 5)
     → reglas 2 y 4.
   - *Manual de verificación de correo* (P-PS-185): el código sirve para «verificar que la dirección de correo…
     funcione correctamente»; llega en ≈ 1 minuto y vale hasta 1 hora (es el flujo de validar el correo del
     usuario, no el del reporte: solo referencia).
   - *Manual de configuración* (P-PS-146): Chrome 60 o superior y ventanas emergentes permitidas para
     `www.sicop.go.cr` y `vpj.sicop.go.cr` (dato técnico para la lección 2).
   - *Manual de registro de proveedores* (P-PS-123): al registrarse se aceptan los términos y un «Contrato de
     uso» de datos personales, cuyo texto completo no se tiene; la descarga de datos abiertos no pide sesión.
   - **Pendiente:** el *Reglamento para la Utilización de SICOP* (cláusula 1a), no conseguido. Si aparece, se
     revisa; si prohíbe descargas con programas, se anota aquí y se vuelve a decidir.
4. **Una sola solicitud a SICOP por día** (restricción en la base). Las pruebas reales, de una en una.
5. **Permiso de Gmail solo de lectura** (`gmail.readonly`), con un **token aparte** del de enviar avisos
   (`gmail.send`): cada parte de la app tiene solo el permiso que necesita. Se reutiliza el mismo cliente de
   Google (`GOOGLE_CLIENT_FILE`).
6. **Solo correos de `info@sicop.go.cr`** con los asuntos «Código verificación para reporte» y «Envío de
   reporte» (observados en las capturas de la guía). No se leen, mueven ni marcan otros correos.
7. **Sin secretos en logs, Git ni chats:** códigos, enlaces, `processId` y tokens se muestran enmascarados.
8. **Pruebas automáticas siempre con SICOP y Gmail simulados** (datos marcados «SIMULADO»).
9. **Ningún fallo en silencio:** un archivo vacío, con otro formato o un enlace vencido es FALLO, nunca «cero
   oportunidades». El enlace se descarga apenas llega: el portal dice 24 h, pero se observó uno vencido a las
   ≈ 16,5 h (sección 2).
10. **`SOURCE_MODE=manual|auto`**, manual por defecto: volver al modo asistido no requiere tocar código.
11. **No se declara «automática»** hasta que un ciclo real lo demuestre de punta a punta.

Datos por confirmar en la primera solicitud real: cuánto tarda el correo con el enlace (la guía dice horas; lo
observado en `ACCESO_SICOP.md` fue ≈ 1 minuto) y si la ventana «Procesando el reporte» trae el `processId`.

Observado el 2026-10-21 (solicitud manual de Ivania, correos guardados en `data/correos_sicop/`): el correo del
código llegó a las 13:34:03 y el del enlace a las 13:36:03, **2 minutos después**. El código tiene 6 letras y
números (distingue mayúsculas) dentro de `<strong>…</strong>`, en un cuerpo HTML `quoted-printable`. El enlace
es `…/ext-report-download?processId=<número>`, en HTML `7bit`. Copias anonimizadas para las pruebas:
`tests/fixtures/correo_*_simulado.eml`.

Primera lectura real con `obtain check-mail` (2026-10-21, permiso `gmail.readonly`): 11 correos de SICOP de los
últimos 3 días, **todos reconocidos** (ninguno con formato desconocido). Entre el código usado y el enlace pasaron
**2 a 6 minutos** (19/10: 10:34 → 10:37 y 15:21 → 15:25; 21/10: 11:28 → 11:33 y 11:34, y 13:34 → 13:36). Hay
códigos sin enlace propio, como el de las 13:32, al que siguió otro a las 13:34: por eso solo vale el código más
reciente posterior a la solicitud.

**Primera prueba real de punta a punta (2026-10-22, Ivania con Oscar, solicitud #3):**
- `obtain request --ver`: el código llegó 31 s después del correo y SICOP lo aceptó a las 08:05:22. La ventana
  «Procesando el reporte» **no trajo el `processId`**.
- El correo con el enlace llegó entre las 08:51 y las 08:56: **≈ 50 minutos**. Rango observado hasta hoy: de 2 a
  50 min. El plazo de 12 h (`OBTAIN_LINK_MAX_HOURS`) sigue siendo suficiente.
- **SICOP bloqueó la descarga hecha por el programa.** En vez del ZIP mostró «No fue posible acceder a la página
  solicitada. Por favor, póngase en contacto con nosotros», con un «ID de soporte». Desde el commit siguiente,
  esa página es FALLO «control no automatizable» (regla 2) y el motivo guarda el ID de soporte.
- Con el mismo enlace, **la descarga a mano en Chrome funcionó**. El ciclo #28 (dry-run) importó ese ZIP sin
  rechazos.
- **Pendiente · Oscar:** decidir entre preguntarle a SICOP, con el ID de soporte, si se permite descargar con un
  programa, o dejar la descarga en manual (la solicitud y el código siguen automáticos). Mientras no se decida,
  no se reintenta la descarga automática ni se cambia el navegador para evitar el bloqueo.
  **Consulta enviada (22/10, Ivania):** a call-center@sicop.go.cr, con el ID de soporte.

**Respuesta de SICOP (recibida por Ivania y reenviada a Oscar el 2026-10-26; resumen fiel del texto):**
- «No es posible autorizar accesos externos ni mecanismos de integración directa con la base de datos».
- «SICOP no dispone de API, servicios web ni esquemas oficiales de integración de datos para consumo externo»;
  no hay mecanismos de interoperabilidad para conectarse desde sistemas de terceros.
- Lo fundamentan en sus políticas de seguridad de la información y en la normativa de protección de datos y
  control de accesos, que restringen dar acceso a terceros «sin la debida autorización institucional y
  justificación técnica».

Lectura (Claude, para que Oscar decida):
- **O1 queda descartada con respuesta oficial:** no hay API ni integración para terceros.
- La respuesta **no habla de forma expresa** de la descarga con un programa desde la página pública de reportes,
  que fue lo que se bloqueó. No la permite ni la prohíbe con esas palabras.
- Sí deja claro que SICOP no autoriza mecanismos de integración para terceros, y el bloqueo del 22/10 es un
  control de acceso. Con la regla 2, eso basta para **no** buscar la forma de descargar con un programa.
- **Recomendación:** dejar la descarga en manual (plan B: alerta → descarga a mano → ZIP en `INCOMING_DIR`). La
  solicitud y el código pueden seguir automáticos, porque se hacen en la misma página pública que usa una
  persona y SICOP no los bloqueó; si Oscar prefiere no automatizar nada, `SOURCE_MODE=manual` y no se toca código.
- **Pendiente · Oscar:** decidir con esta respuesta. Hasta entonces sigue sin reintentarse la descarga automática.

**Lección 4 (2026-10-22): `obtain auto` integra la obtención al ciclo** (`docs/OPERACION.md` 3.1). Aplica estas
reglas así:
- Regla 2: una solicitud fallida no se reintenta; se manda **una** alerta con el plan B (descarga a mano).
- Regla 4: una solicitud por día, aunque falle.
- Regla 7: la alerta no lleva el enlace, el código ni el `processId`.
- Regla 10: con `SOURCE_MODE=manual` no hace nada.
- Regla 11: sigue sin declararse «automática» hasta que un ciclo real lo demuestre.
