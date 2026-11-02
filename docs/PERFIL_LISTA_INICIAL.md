# Perfil de Hermatix: lista inicial (borrador para revisar con Oscar)

Asistente de elegibilidad, lección 1 (`docs/Guia_Asistente_Elegibilidad_SICOP.docx`). **Borrador del 2026-11-02**,
armado por Ivania con Claude. Falta acordarlo con Oscar: él dice qué entra al perfil y quién entrega cada dato.

## Cómo se armó

- Fuente: los **183 requerimientos** que extrajeron los resúmenes con IA de los **15 carteles** que hoy tienen
  resumen (información pública de SICOP): 70 legales, 69 técnicos, 29 financieros y 15 de experiencia.
- No se leyó ningún documento de Hermatix.
- «Carteles» = en cuántos de los 15 aparece. «Excluyente» = en cuántos de esos el pliego dice que, si no se cumple,
  la oferta queda fuera. Son **conteos aproximados**: se buscaron palabras en el texto de cada requerimiento.

## Lo que proponemos guardar en el perfil

Tipo de respuesta: **número**, **documento**, **fecha** o **sí/no**. «Vence»: si el elemento tiene fecha de
vencimiento y la app debe avisar antes.

| Tipo | Elemento | Carteles | Excluyente | Respuesta | Vence | ¿Va al perfil? (Oscar) | ¿Quién lo entrega? (Oscar) |
|---|---|---|---|---|---|---|---|
| Experiencia | Años de experiencia en GPS y flotas, con declaración jurada (piden 1, 5 o 10 años) | 4 | 4 | número + documento | no | | |
| Experiencia | Constancias o cartas de clientes: servicios GPS a instituciones en los últimos 5 años, recibidos a satisfacción | 5 | 4 | documento por cliente (con fecha) | sí (antigüedad) | | |
| Experiencia | Clientes activos con número de vehículos y última factura | 1 | 1 | documento | sí | | |
| Personal | Lista y currículos de técnicos de instalación y mantenimiento (≥ 2 años) y profesionales en planilla (por ejemplo ingeniero en sistemas, técnico en autotrónica) | 3 | 3 | documento por persona | no | | |
| Certificación | Carta del fabricante, integrador autorizado o certificado de marca de los equipos (alguna pide ≤ 6 meses) | 3 | 1 | documento | sí | | |
| Certificación | Certificados de calidad o normas de los equipos (calidad, NDAA, EN 840) | 3 | 2 | documento | depende | | |
| Permiso | Patente municipal vigente y constancia de estar al día | 8 | 5 | documento + fecha | sí | | |
| Permiso | Permiso sanitario de funcionamiento (o constancia de que no se requiere) | 5 | 3 | documento + fecha | sí | | |
| Póliza | Riesgos del trabajo del INS, acorde a la actividad | 7 | 2 | documento + fecha | sí | | |
| Póliza | Responsabilidad civil (al adjudicatario) | 2 | 0 | documento + fecha | sí | | |
| Póliza | Seguro de los equipos | 1 | 1 | documento + fecha | sí | | |
| Legal | Al día con la CCSS (certificación) | 7 | 5 | sí/no + documento | sí (fecha de la consulta) | | |
| Legal | Al día con FODESAF | 4 | 3 | sí/no + documento | sí | | |
| Legal | Al día con Hacienda, con actividad económica afín al objeto | 5 | 4 | sí/no + documento | sí | | |
| Legal | Actividad comercial registrada afín al objeto | 4 | 3 | texto | no | | |
| Legal | Declaración jurada de prohibiciones (art. 28 y 29 de la Ley General de Contratación Pública) | 6 | 3 | documento (plantilla) | no | | |
| Legal | Declaración de beneficiarios finales y propiedad de las acciones | 6 | 3 | documento | sí (si cambia) | | |
| Legal | Firma digital del representante legal (oferta firmada por quien tiene poder) | 4 | 2 | sí/no + fecha | sí (certificado) | | |
| Financiero | Estados financieros u otros datos financieros | 0 | 0 | documento | sí | | |

Notas:
- **Financiero:** en estos 15 carteles no se pidieron estados financieros; se deja la fila por si Oscar sabe que
  otros carteles los piden.
- **Firma digital:** el certificado vence; conviene guardar hasta cuándo es válido.

## Lo que NO va al perfil (cambia en cada oferta)

| Requisito | Carteles | Por qué no |
|---|---|---|
| Estructura de precios y desglose de costos | 12 | Se arma para cada oferta |
| Garantía de cumplimiento del adjudicatario | 6 | Depende del monto del cartel y solo si se gana |
| Vigencia de la oferta | 2 | Se escribe en cada oferta |
| Fichas técnicas, literatura del fabricante y muestras del producto | — | Dependen del equipo que se ofrezca |

## Para decidir con Oscar

1. ¿Qué elementos de la tabla entran al perfil? (columna «¿Va al perfil?»)
2. ¿Quién entrega cada uno: Oscar, el área administrativa u otra persona? (columna «¿Quién lo entrega?»)
3. **Capacidades de la empresa** que también se repiten: soporte técnico (5 carteles, 4 excluyentes; por ejemplo
   24/7 con atención en 24 horas), taller con dirección (2) y garantía técnica (2). ¿Van al perfil como un tipo
   nuevo, «capacidad», o se dejan fuera?
4. ¿Con cuánto tiempo de anticipación avisa la app que algo va a vencer? La guía dice 30 días.
5. ¿Falta algo que Oscar sabe que piden otros carteles y no salió en estos 15?
