# SICOP CONNECT sin Ivania: qué corre solo y qué hace una persona

Hoja de traspaso (2026-11-17, Ivania con Claude), para Oscar y para quien quede a cargo del día a día. Es el resumen;
el detalle está en las guías que se citan. Nada de esto cambia la app.

## Lo primero: hoy todo depende de la laptop de Ivania

Las tareas automáticas corren en el Programador de tareas de Windows de esa laptop. **Solo corren si la laptop
está encendida y con la sesión abierta.** El servidor (`https://sicop.hermatix.com`) sigue con la versión del
15/10 (`02b569b`) y no corre ninguna tarea. Si la laptop se apaga, se detienen los avisos, el enriquecimiento y
los resúmenes.

Para que funcione sin la laptop, Oscar tiene que:

1. Unir el PR de `desarrollo` (texto en `docs/PR_DESARROLLO.md`).
2. Actualizar el servidor con `docs/ACTUALIZACION_SERVIDOR.md`, pasos 0 a 10. Ese día se apagan las tareas de
   Windows.
3. Elegir la PC que hará el enriquecimiento (`docs/TRASPASO_ENRIQUECIMIENTO.md`) y conectarla al servidor (paso 11
   de la guía del servidor).

## Qué corre solo (lunes a viernes, hora de Costa Rica)

| Hora | Qué hace | Hoy | Después de actualizar el servidor |
|---|---|---|---|
| 8:00 | Ciclo: importa lo que haya en la carpeta de entrada, evalúa y **manda el correo de avisos**. Los lunes, además, el resumen semanal | Laptop («SICOP CONNECT - ciclo diario») | Servidor (`sicop-cycle.timer`) |
| 10:00 | Enriquecimiento: consulta en SICOP la ficha y los documentos de hasta 20 carteles (abre un navegador) | Laptop («SICOP CONNECT - enriquecimiento») | La PC elegida, que lo manda al servidor |
| Al terminar el enriquecimiento (en el servidor, 10:45) | Resúmenes con IA de los carteles que ya tienen documentos (máx. 10 y 5 USD al día) | Laptop, en la misma tarea de las 10:00 | Servidor (`sicop-ia-cola.timer`) |
| 14:00 | Segunda vuelta de los resúmenes, por si la de la mañana falló | Laptop («SICOP CONNECT - resumenes IA») | Servidor (el mismo `sicop-ia-cola.timer`) |

## Lo que tiene que hacer una persona

**Cada día hábil, antes de las 8:00 (lo más importante).** Los datos de SICOP **no llegan solos**: SICOP bloqueó
la solicitud automática el 10/11. Una persona pide el reporte «Detalle pliego de condiciones» y sube el ZIP tal
como llega. Hay dos formas: en el panel, «Cargar archivo», tipo «pliegos (.zip)»; o dejándolo en la carpeta de
entrada antes de las 8:00. Si nadie lo carga, el ciclo sale en «FALLO · no llegó ningún archivo nuevo» y ese día
**no hay correo de carteles nuevos**: solo salen los avisos de cierre próximo. La app no está rota. Detalle:
`OPERACION.md` §1.1 y §1.2. Evitar subir el ZIP entre las 10:00 y las 10:30, mientras corre el enriquecimiento.

**Cada día, 5 minutos:**

- [ ] El correo de las 8:00 llegó **una sola vez**. Si llegó doble, hay dos ciclos encendidos (laptop y servidor).
- [ ] Panel → «Bitácora»: la corrida del enriquecimiento dice «ok». **Un CAPTCHA o un FALLO no llega por correo**
      (`ENRICH_EMAILS=false`); solo aparece ahí, el mismo día.
- [ ] Revisar en el panel los carteles Alta y Media nuevos: Interesa, Revisar o No interesa.

**Cada semana (lunes):**

- [ ] Panel → «Productividad», la semana pasada: que ningún cartel Alta o Media haya cerrado sin revisión.
- [ ] El resumen semanal llegó. También se ve en el panel: «Último correo» → «Último resumen semanal».
- [ ] Respaldo (`OPERACION.md` §6.1). Mientras siga la laptop: `backup` y el ZIP al Drive de Hermatix. En el
      servidor, el destino y la frecuencia los decide Oscar (pendiente).

## Si pasa algo

| Qué pasa | Qué hacer | Dónde dice más |
|---|---|---|
| No llegó el correo de las 8:00 | ¿Se cargó el ZIP del día? ¿La laptop estaba encendida (o el servidor arriba)? Correr `doctor` | `OPERACION.md` §3 y §5 |
| «Bitácora» con CAPTCHA o bloqueo | **Nunca** resolver el CAPTCHA a mano. La app ya reintentó una vez. Avisar a Oscar; se vuelve a intentar al día siguiente | `TRASPASO_ENRIQUECIMIENTO.md`, «Si algo sale mal» |
| Un cartel sin resumen de IA | Esperar la vuelta de las 14:00 o la del día siguiente. Si llegó al tope del día, también espera | `OPERACION.md` §3.3 |
| «database is locked» o la base ocupada | Las tareas esperan hasta 10 min solas. No subir archivos grandes a las 10:00 | `ESTADO_PROYECTO.md`, 10/11 |
| Un aviso «fallido» o «incierto» | Panel → «Avisos» → «Reintentar» (antes, mirar Gmail › Enviados) | `OPERACION.md` §4.4 |
| «Faltan migraciones… ejecuta migrate» | Respaldo y después `migrate`, con el panel cerrado | `OPERACION.md` §5.3 |
| Alguien deja la empresa u olvida la contraseña | Un administrador, en «Usuarios» y «Seguimiento» | `OPERACION.md` §5.3 |
| La base se daña | Restaurar el último respaldo (apartar también `-wal` y `-shm`) | `OPERACION.md` §6.2 |

## Lo que nunca se hace

- Resolver un CAPTCHA de SICOP a mano, o tener dos computadoras con el enriquecimiento encendido a la vez.
- Dejar encendidos el ciclo de la laptop y el del servidor a la vez (salen correos dobles).
- Pasar claves (OpenAI, Anthropic, Gmail, el token del enriquecimiento) por correo, chat o Claude: van en persona.
- Copiar el `.db` a mano mientras la app trabaja: siempre `backup`.

## Lo que está pendiente de Oscar

En `ESTADO_PROYECTO.md`, buscar «Pendiente · Oscar». Los que afectan al funcionamiento: unir el PR y actualizar el
servidor, la PC del enriquecimiento, el respaldo del servidor, la clave de Anthropic (hoy se usa OpenAI) y si se
consulta a SICOP por el bloqueo de la solicitud automática.
