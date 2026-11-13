# Revisión: desacuerdos entre las reglas y la IA (2026-11-09)

Pedido de Ivania. Datos **REALES** de `data/sicop.db`, solo lectura: los 41 carteles con resumen de la IA, su
prioridad según las reglas vigentes (`c40b2c956048`) y la recomendación del último resumen. Ninguno tiene todavía
una revisión humana. No se cambió nada: las decisiones de abajo son de Ivania (y de Oscar si hace falta).

## Resumen

| Reglas | IA | Carteles | ¿Desacuerdo? |
|---|---|---|---|
| Alta | Revisar requisitos | 3 | No (la IA pide confirmar algo) |
| Alta | Descartar | 1 | **Sí** |
| Media | Revisar requisitos | 3 | No |
| Media | Descartar | 1 | **Sí** |
| Baja | Descartar | 22 | No |
| Baja | Revisar requisitos | 8 | **Sí** |
| Sin coincidencia | Descartar | 3 | No |

**10 desacuerdos.** Los 2 primeros importan más: las reglas les dieron Alta o Media, así que **salieron en los
avisos por correo**, y la IA dice descartar.

Dato curioso: en los 41 resúmenes la IA nunca recomendó «Dar seguimiento»; lo más positivo fue «Revisar
requisitos».

## A. Las reglas avisaron y la IA dice descartar (2)

### A1 · 20261002824 «cOMPRA DE CAMARAS Y ACCESORIOS» (cerró el 04/11)
- **Reglas: Media** en videotelemática, por «CAMARAS» (título) y «GRABACIÓN DE VIDEO» (pliego, pág. 3).
  Avisado a 4 destinatarios.
- **IA: Descartar.** «Las 18 líneas solicitan cámaras fotográficas, de video y videoconferencia».
- **Opinión de Claude:** la IA tiene razón; es un falso positivo de las reglas, como el de las paradas.
- **Propuesta:** exclusiones «camara fotografica», «camaras fotograficas» y «videoconferencia» en
  videotelemática (y en las familias de cámaras), y el cartel al golden set como `falso_positivo_conocido`.

### A2 · 20261003868 «64 sensores LoRaWAN para detección de inundaciones y 1 Gateway LoRaWAN integrado al BMS» (cierra hoy, 23:59)
- **Reglas: Alta** en iot_frio (Osmia), por «LoRaWAN», «Internet de las Cosas», «IoT» y «Gateway».
  Avisado a 3 destinatarios.
- **IA: Descartar.** «El objeto es detectar inundaciones e integrar sensores al BMS del edificio, no una de las
  familias de servicios identificadas de Hermatix».
- **Opinión de Claude:** no está claro, y es una decisión comercial. Hermatix se presenta como empresa de IoT y
  M2M, pero Osmia es monitoreo de temperatura y cadena de frío. «LoRaWAN» e «IoT» como señales **altas** de
  iot_frio son muy amplias: cualquier proyecto de sensores sale Alta.
- **Opciones:**
  1. **Sí interesa** (Hermatix puede vender sensores IoT en general): se agrega al criterio de la IA que el IoT
     en general también es de interés.
  2. **No interesa** (solo frío y temperatura): «LoRaWAN», «IoT» y «Gateway» pasan de señal alta a media en
     iot_frio (solas darían Baja y no saldrían en avisos), y el cartel va al golden set como falso positivo.

## B. Las reglas dicen Baja y la IA dice revisar requisitos (8)

Ninguno salió en los avisos (Baja no se avisa), así que no hay daño. Pero la IA los pone en «Revisar requisitos»
en el reporte y en el panel.

### B1 · Mantenimiento mecánico de vehículos (7)
`20261100749`, `20261100774`, `20261100779`, `20261100786`, `20261100790`, `20261100794` (mantenimiento preventivo
M1/M2/M3 de compactadores y vagonetas IVECO, cierran el 10/11) y `20261004211` (mantenimiento, mecánica,
enderezado, pintura y tapicería de una flotilla, cerró el 06/11).

- **Reglas: Baja** en mantenimiento_flotas, solo por «mantenimiento preventivo».
- **IA: Revisar requisitos.** «Se alinea con la familia de mantenimiento de flotas (FleetRun)», pero piden
  herramientas originales IVECO exclusivas de AUTOCORI.
- **Opinión de Claude:** las reglas tienen razón. Es trabajo de taller, y el 2026-10-09 Ivania decidió que el
  taller sin software no interesa (por eso existen las exclusiones «mantenimiento preventivo y correctivo» y
  «reparacion»). La IA confunde **FleetRun** (software para gestionar el mantenimiento) con el **taller** que hace
  el mantenimiento.
- **Propuesta:** un prompt nuevo (**v8**, sobre v7) que aclare en el criterio de Hermatix: «mantenimiento de flotas
  → FleetRun es software para programar y controlar el mantenimiento; la reparación o el mantenimiento mecánico
  hecho en taller no se alinea → descartar». Se prueba en 2 o 3 de estos carteles antes de activarlo.

### B2 · 20261003748 «Sistemas de cámaras de seguridad Liberia» (cerró el 05/11)
- **Reglas: Baja** en videotelemática, solo por «cámaras» en el título.
- **IA: Revisar requisitos.** Los documentos piden **dos cámaras corporales** (BodyCams) compatibles con Motorola,
  además de videovigilancia fija.
- **Opinión de Claude:** aquí la IA vio algo que las reglas no: las cámaras corporales venían en los documentos,
  no en el título ni en las líneas. Por la decisión de Ivania del 2026-10-27, lo que solo está en el PDF deja la
  familia como máximo en Baja. El cartel ya cerró y sus documentos se retiraron al cierre.
- **Para decidir (sin urgencia):** si una señal **alta** de BodyCams que aparece solo en el PDF debería subir a
  Media (y salir en los avisos). Hoy no lo hace a propósito, para evitar ruido de los pliegos.

## Decisiones (Ivania, 2026-11-09)

| Caso | Decisión | Qué se hizo |
|---|---|---|
| A1 | Arreglar y al golden set | Las exclusiones por página no bastaban (30 páginas de cámaras y video). La causa era «grabacion de video» como **señal media**: pasó a **contexto** en videotelemática. Medido en una copia de la base: solo cambia este cartel (Media → Baja); golden set 39/39 con el cartel como `falso_positivo_conocido` |
| A2 | **Preguntar a Oscar** | Nada todavía: ¿le interesan a Hermatix los sensores IoT en general, no solo de frío y temperatura? |
| B1 | Prompt **v8** y probarlo | v8 = v7 + «FleetRun es software para gestionar el mantenimiento; el mantenimiento o la reparación en taller se descarta». IA real: `20261100749` (IVECO) y `20261004211` (flotilla, enderezado y pintura) pasan de «Revisar requisitos» a **Descartar** («Hermatix no presta servicios de taller»); 0.046 USD |
| B2 | Sin cambio | Se deja como está (decisión del 2026-10-27) |
