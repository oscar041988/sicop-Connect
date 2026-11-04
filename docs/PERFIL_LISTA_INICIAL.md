# Perfil de Hermatix: lista para revisar con Oscar

Asistente de elegibilidad (`docs/Guia_Asistente_Elegibilidad_SICOP.docx`). **Versión en limpio del 2026-11-04**,
armada por Ivania con Claude, sobre el borrador del 2026-11-02. Falta que Oscar la apruebe: él dice qué entra al
perfil y quién entrega cada dato.

## Para qué sirve el perfil

El perfil guarda **una sola vez** lo que piden casi todos los carteles. Con el perfil cargado, el asistente casi no
pregunta: muestra el dato guardado y basta con «Sí, es correcto». Sin perfil, las mismas preguntas se repiten en
cada cartel, y eso es lo que hoy lo hace lento.

La lista está en dos partes:

- **Parte A · Datos:** números, textos, fechas y sí/no. No son documentos delicados: **se pueden cargar ya**.
- **Parte B · Documentos:** PDF o imagen. Son delicados: **se cargan al final**, cuando Oscar decida cómo se
  protegen (hoy el asistente permite responder «Lo tiene · archivo pendiente» sin subirlos).

## De dónde sale

- Los **183 requerimientos** de los 15 carteles con resumen con IA (borrador del 2026-11-02). «Carteles» y
  «Excluyente» son conteos aproximados de esa fuente.
- Las **5 listas de verificación** revisadas por Ivania (2026-11-03 y 2026-11-04) y la lectura completa de dos
  expedientes (`docs/revision_faltantes_20261104.md`): de ahí salen las filas marcadas **(nuevo)**, sin conteo.
- No se leyó ningún documento de Hermatix: todo es información pública de SICOP.

## Parte A · Datos (se pueden cargar ya)

| Tipo | Dato | Carteles | Excluyente | Respuesta | Vence | ¿Va? (Oscar) | ¿Quién lo da? (Oscar) |
|---|---|---|---|---|---|---|---|
| Experiencia | Años de experiencia en GPS y gestión de flotas (piden 1, 5 o 10) | 4 | 4 | número | no | | |
| Experiencia | **(nuevo)** Años de experiencia en CCTV y redes (uno pide 10) | — | — | número | no | | |
| Experiencia | **(nuevo)** Cantidad de proyectos terminados, por tipo (GPS, CCTV, centros de monitoreo) | — | — | número | no | | |
| Legal | **(nuevo)** Años inscrita en Hacienda en la actividad (uno pide 10) | — | — | número | no | | |
| Legal | Actividad comercial registrada afín al objeto | 4 | 3 | texto | no | | |
| Legal | **(nuevo)** Inscrita en SICOP y en el Registro de Proveedores; datos al día (no más de 24 meses) | — | — | sí/no + fecha | sí | | |
| Legal | **(nuevo)** Citas de inscripción de la sociedad (tomo, folio, asiento) y plazo de la sociedad | — | — | texto + fecha | no | | |
| Legal | Firma digital del representante legal: hasta cuándo vale el certificado | 4 | 2 | fecha | sí | | |
| Personal | Cantidad de técnicos en planilla y años en el área | 3 | 3 | número | no | | |
| Personal | **(nuevo)** Técnicos con carné de trabajo en alturas: cuántos | — | — | número | sí (carné) | | |
| Capacidad | Soporte técnico: horario y tiempo de atención (por ejemplo 24/7, 24 horas) | 5 | 4 | texto | no | | |
| Capacidad | Taller o centro de servicio: dirección, correo y teléfonos | 2 | — | texto | no | | |
| Capacidad | Garantía técnica que ofrece Hermatix (meses) | 2 | — | número | no | | |
| Capacidad | **(nuevo)** Marcas que vende Hermatix y si es distribuidor autorizado | — | — | texto | no | | |
| Evaluación | **(nuevo)** Condición PYME (certificación del MEIC): sí/no y vencimiento | — | 0 (da puntos) | sí/no + fecha | sí | | |
| Evaluación | **(nuevo)** ISO 14001, Bandera Azul u otro programa ambiental o de residuos | — | 0 (da puntos) | sí/no + fecha | sí | | |
| Evaluación | **(nuevo)** Política de inclusión laboral de mayores de 45 años | — | 0 (da puntos) | sí/no | no | | |

## Parte B · Documentos (al final)

| Tipo | Documento | Carteles | Excluyente | Vence | ¿Va? (Oscar) | ¿Quién lo da? (Oscar) |
|---|---|---|---|---|---|---|
| Experiencia | Constancias o cartas de clientes (recibido a satisfacción, últimos 5 años) | 5 | 4 | sí (antigüedad) | | |
| Experiencia | Clientes activos con número de vehículos y última factura | 1 | 1 | sí | | |
| Experiencia | Declaración jurada de años de experiencia | 4 | 4 | no | | |
| Personal | Currículos y títulos de técnicos y profesionales (y CFIA, si es ingeniero) | 3 | 3 | no | | |
| Personal | **(nuevo)** Certificaciones de los técnicos (CCTV, cableado, redes, VMS) y carnés de alturas | — | — | sí | | |
| Certificación | Carta del fabricante o certificado de marca (alguna pide no más de 1 o 6 meses) | 3 | 1 | sí | | |
| Certificación | Certificados de calidad o normas de los equipos (NDAA, EN 840…) | 3 | 2 | depende | | |
| Permiso | Patente municipal vigente y comprobante de pago | 8 | 5 | sí | | |
| Permiso | Permiso sanitario de funcionamiento (o constancia de que no se requiere) | 5 | 3 | sí | | |
| Póliza | Riesgos del trabajo del INS | 7 | 2 | sí | | |
| Póliza | Responsabilidad civil (alguno la pide desde la oferta) | 2 | 0 | sí | | |
| Póliza | Seguro de los equipos | 1 | 1 | sí | | |
| Legal | Certificación de estar al día con la CCSS | 7 | 5 | sí (fecha de consulta) | | |
| Legal | Al día con FODESAF | 4 | 3 | sí | | |
| Legal | Al día con Hacienda | 5 | 4 | sí | | |
| Legal | **(nuevo)** Certificación de personería jurídica (alguno pide no más de 1 mes) | — | — | sí | | |
| Legal | Declaración jurada de prohibiciones (art. 28 y 29 LGCP) — plantilla | 6 | 3 | no | | |
| Legal | Declaración de beneficiarios finales y propiedad de las acciones | 6 | 3 | sí (si cambia) | | |
| Financiero | Estados financieros (ningún cartel de los 15 los pidió) | 0 | 0 | sí | | |

## Lo que NO va al perfil (cambia en cada oferta)

| Requisito | Por qué no |
|---|---|
| Estructura de precios, desglose de costos e índices | Se arma para cada oferta |
| Garantía de cumplimiento y garantía colateral | Dependen del monto del cartel y solo si se gana |
| Vigencia de la oferta y plazos de entrega | Se escriben en cada oferta |
| Fichas técnicas, literatura, muestras y matriz de cumplimiento | Dependen del equipo que se ofrezca |
| Cronograma, memoria de cálculo y planes de mantenimiento | Se preparan para cada proyecto |

## Para decidir con Oscar

1. ¿Qué filas entran al perfil? (columna «¿Va?»)
2. ¿Quién da cada dato o documento? (columna «¿Quién lo da?»)
3. ¿Se cargan ya los datos de la **Parte A**, aunque los documentos esperen?
4. ~~¿Las filas de **Capacidad** y **Evaluación** van como tipos nuevos del perfil?~~ **Sí** (Ivania, 2026-11-04):
   migración 0035; `config/perfil.yaml` ya trae la parte A como sugerencias.
5. ¿Con cuánta anticipación avisa la app que algo vence? La guía dice 30 días.
6. **Para que el asistente no retrase** (comentario de Ivania, 2026-11-04): ¿pregunta primero solo los
   excluyentes y deja el resto para cuando el cartel interese de verdad?
7. ¿Falta algo que Oscar sabe que piden otros carteles?

Cuando Oscar decida, se ajusta `config/perfil.yaml` (sugerencias y frases que proponen cada elemento): no hace falta
tocar código.
