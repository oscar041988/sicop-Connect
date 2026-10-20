# Decisión: ¿se puede automatizar la descarga de SICOP? (A1)

**BORRADOR (2026-10-20), sin decisión.** Preparado por Ivania con Claude para la lección 11 (guía, sección 13,
y 16.1). Lo decide Oscar después de revisar juntos los términos de uso del portal.
Regla de la guía: no se eluden códigos de validación, CAPTCHA ni términos de uso. «No es viable sin
intervención humana» es un resultado válido.

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
- El ciclo no acepta el ZIP de «Detalle pliego de condiciones»: hay que descomprimirlo (paso 7).

**Conclusión de la evidencia:** el paso 4 es una validación pensada para una persona. Automatizarlo sería
eludirla, y la guía lo prohíbe. Por lo tanto, **ninguna opción permitida elimina a la persona en cada solicitud**.

## 3. Opciones, de la más robusta a la menos

### O1 · API oficial documentada

- Requiere: que SICOP publique una API con acceso para Hermatix.
- Evidencia: ninguna. **No viable hoy.**
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

- Escribir el código por programa es **eludir la validación** (paso 4). **Descartada** por la regla de la guía,
  sin importar si técnicamente funcionara.
- Además: es frágil (cualquier cambio del portal lo rompe sin avisar), necesita dependencias nuevas y tiene un
  riesgo alto con los términos de uso.

### O4 · Mejorar el modo asistido, sin permisos nuevos

- **a. Aceptar el ZIP de pliegos tal como llega**, en la carpeta de entrada y en el panel: elimina el paso 7.
  Riesgo bajo; reutiliza la revisión de ZIP dañado que ya existe para el catálogo.
- **b. Recordatorio** a quien descarga si a cierta hora (por ejemplo, 7:30) no hay archivo nuevo. Usa el envío
  que ya funciona (`gmail.send`). Hay que decidir a quién y a qué hora.
- **c. Instrucciones cortas** en `docs/OPERACION.md` para la persona que descarga (ya existen en buena parte).

## 4. Recomendación provisional

1. **O4a y O4b ahora**: quitan fricción sin permisos nuevos ni riesgos con los términos.
2. **O2 solo si Oscar lo pide**, después de revisar los términos de uso y aceptar a conciencia el permiso de
   lectura del buzón. Aun así, sigue siendo asistido.
3. **O1**: preguntarle a soporte de SICOP si existe una API, si Hermatix lo decide.
4. **O3 no se hace.**

Nivel que se declara hoy: **obtención asistida; análisis y avisos automáticos** (guía 16.1). No se declara
«automático» hasta que un ciclo real lo demuestre.

## 5. Para decidir con Oscar

- ¿Qué dicen los términos de uso del portal sobre descargas con programas? (Revisarlos juntos.)
- ¿Quién descarga cada día hábil y a qué hora? ¿Qué buzón usa?
- ¿O4a y O4b le parecen bien? ¿A quién va el recordatorio y a qué hora?
- ¿Le interesa O2 a cambio de dar permiso de lectura del buzón?
- ¿Se le pregunta a soporte de SICOP si hay una API (O1)?

## 6. Decisión

- Fecha:
- Opción aceptada:
- Decidió:
- Comentarios:

## 7. Autoevaluación (guía, lección 11; la responde Ivania)

- ¿Por qué un resultado «no viable» también tiene valor?
- ¿Qué riesgo tendría un adaptador que se rompe sin avisar?
