# Prueba del resumen con IA: v3, v4 y v5 (2026-11-04)

Decisión de Oscar (reunión del 2026-11-04): probar el resumen v3 en 3 carteles y comparar antes de activarlo.
Carteles: `20261002408` (cámaras del liceo), `20261003280` (GPS) y `20261003242` (etiquetas RFID), los primeros
con la lista de verificación corregida a mano. Nada se activó: `IA_PROMPT_VERSION` sigue en `v2` y las listas no
cambiaron. Los resúmenes nuevos quedan en `ia_summaries` (en esos 3 carteles el panel muestra el más reciente).

## v3 y v4: no sirven así

| Prueba | Límite | Resultado | Costo |
|---|---|---|---|
| v3 en 20261002408 | 8000 tokens | Fallido: respuesta incompleta (usó los 8000) | 0,051 USD |
| v4 (v3 con especificaciones cortas) en 20261002408 | 8000 tokens | Fallido: respuesta incompleta (usó los 8000) | 0,051 USD |
| v4 en 20261002408 | 16000 tokens | Fallido: la IA tardó más de 120 s (`IA_TIMEOUT_SECONDS`) | sin dato |

El v2 de ese mismo cartel usa unos 3900 tokens. Lo más probable es que el modelo gaste buena parte del límite
«pensando» con las reglas largas del v3/v4 (cada especificación por separado y con texto literal). Para carteles
grandes (Liberia: ~450 especificaciones) sería peor. **Conclusión: no activar el v3 ni el v4.**

## v5: el v2 + una regla corta (funciona)

`config/prompts/resumen_cartel_v5.md` = el v2 + «incluye siempre, en una línea corta y con su cita: la garantía de
participación y de cumplimiento (porcentaje o monto y vigencia), cualquier otra garantía con su plazo, los plazos de
entrega, instalación y atención de averías, y la vigencia de la oferta».

| Cartel | Requerimientos v2 | Requerimientos v5 | Lista actual (a mano) | Excluyentes en v5 | Costo v5 |
|---|---|---|---|---|---|
| 20261002408 · cámaras | 16 | **19** | 50 (34) | 19 de 19 | 0,028 USD |
| 20261003280 · GPS | 12 | **29** | 115 (103) | 13 de 29 | 0,040 USD |
| 20261003242 · RFID | 13 | **23** | 80 (67) | 1 de 23 | 0,039 USD |

- **Garantía de cumplimiento:** el v5 la trae como requerimiento en GPS y RFID. En el liceo dice que «no procede»
  (igual que el pliego y que lo agregado a mano).
- **Plazos y vigencia de la oferta:** aparecen en los 3 (en el liceo, «instalar en 10 días hábiles» y «oferta vigente
  30 días»), que el v2 no traía como requerimientos.
- **Especificaciones técnicas:** el v5 trae algunas más, pero no una por una; siguen faltando la mayoría (las de la
  lista a mano). Para eso sigue haciendo falta la revisión del pliego (a mano o con Claude).
- **Multas:** el v5 no las trae como requerimientos (tampoco el v2); en las listas se agregaron a mano.
- **Excluyentes:** sigue el problema ya visto: en el liceo marca todo como excluyente y en RFID casi nada.
- **Costo:** igual que el v2 (0,03–0,04 USD por cartel), dentro del límite de 4000 tokens de salida.

## Recomendación para Oscar

1. **Activar el v5** para la cola automática (`IA_PROMPT_VERSION=v5` en el `.env`): mismo costo que el v2 y trae lo
   que más faltaba (garantías, plazos, vigencia). Los carteles con v2 volverían a la cola (≈0,04 USD cada uno, 10
   al día).
2. **No usar v3/v4.** Las especificaciones una por una siguen como revisión del pliego.
3. Pendiente aparte: que la IA marque mejor qué es excluyente (revisar con un cartel donde Oscar diga cuáles son).

Gasto total de la prueba: ≈0,21 USD (más la llamada que se cortó). Gasto del día: 0,58 USD de 1.00.
