# Gestor de documentos

> Mejora pedida por Oscar (nombre suyo: «Gestor de documentos»). Requerimientos contados por Ivania y ordenados
> con Claude el 2026-10-26. **Estado: los 5 pasos hechos (1A el 2026-10-26; 1B, 2 y 5 el 2026-10-29; 3 y 4 el 2026-10-30), solo local.** Se construye
> poco a poco: cada paso se prueba y
> se entrega por separado (en `desarrollo`, solo local, como todo desde el 21/10).

## Qué es

Hoy la app encuentra carteles, los revisa y avisa. Con el gestor, un cartel que interesa se puede **trabajar** en
la app: tiene un **expediente**, es decir, la carpeta de trabajo del cartel.

Ejemplo: «Cartel `20261001497` · encargada: Ivania · 3 notas · `pliego.pdf`, `oferta-borrador.docx` · etapa:
preparando».

Requerimientos de Oscar:

1. Dar seguimiento a un cartel que interesa o que le sirve a Hermatix.
2. Ver quién trabaja en la propuesta de ese cartel.
3. Subir el cartel completo (pliego, anexos) y lo que se vaya preparando.
4. Escribir notas.
5. Si el trabajo pasa de una persona a otra, que la nueva pueda ver y **descargar toda la información**.

## Decisiones (Oscar, por medio de Ivania, 2026-10-26)

| Tema | Decisión |
|---|---|
| Página propia | Sí: una página o sección nueva con los carteles en seguimiento |
| Tipos de archivo | Los cuatro: PDF, Word, Excel y ZIP (versatilidad) |
| Tamaño máximo | 10 MB por archivo **por ahora**; tiene que poder cambiarse sin tocar código (variable de configuración) |
| Aviso al nuevo encargado | Sí, por correo |
| Etapas del seguimiento | Se **suman** a las decisiones «Ofertada» y «No se oferta»; no las reemplazan |
| Quién ve y edita | **Solo el encargado asignado y los administradores** (opción B). Los demás encargados ven que el cartel **está en seguimiento**, para evitar confusiones (que dos personas trabajen el mismo cartel), pero no pueden abrir el expediente ni editarlo |
| Marca para los demás | Muestra el nombre del encargado: «En seguimiento · Ivania» |
| Cómo se abre | Botón **«Dar seguimiento»** en la página del cartel (la de «ver toda la información»). Al darlo, el cartel aparece en la página de seguimiento |
| Quién asigna y cambia el encargado | **Solo un administrador** |
| Quién ve el botón «Dar seguimiento» | **Cualquier usuario.** El cartel queda «En seguimiento · sin encargado» hasta que un administrador lo asigne; mientras tanto, solo los administradores entran al expediente |
| Cuándo sale el correo al encargado | **Con el ciclo diario** (8:00), junto con los demás avisos: al asignar queda preparado en la outbox |
| Etapas (paso 5) | **Aprobadas** las propuestas: preparando · enviada · ganada · perdida |
| Entregas | El paso 1 se parte en **1A** (botón, marca, página, asignación) y **1B** (correo), por separado |

## Preguntas abiertas

Lo demás se decidió el 2026-10-26 (tabla de arriba).

- Ninguna por ahora: las etapas quedaron aprobadas el 2026-10-26.

## Pasos

| Paso | Qué agrega | Necesita |
|---|---|---|
| 1A | Botón «Dar seguimiento», marca «En seguimiento · <nombre>», página «Seguimiento», expediente con encargado e historial de quién lo tuvo; solo el administrador asigna | **Hecho** (2026-10-26) |
| 1B | Correo al nuevo encargado, con el ciclo diario | **Hecho** (2026-10-29) |
| 2 | Subir y bajar archivos (PDF, Word, Excel, ZIP; 10 MB) | **Hecho** (2026-10-29) |
| 3 | Notas con autor y fecha | **Hecho** (2026-10-30) |
| 4 | «Descargar expediente»: un ZIP con archivos, notas e historial (el traspaso) | **Hecho** (2026-10-30) |
| 5 | Etapas del seguimiento: preparando · enviada · ganada · perdida | **Hecho** (2026-10-29) |

El paso 1 va primero aunque se vea poco: sin expediente, los archivos y las notas no tienen dónde colgarse.

### Paso 1A, cómo quedó

- **Tablas** (migración `0015_seguimiento.sql`): `seguimientos` (uno por cartel) y `seguimiento_asignaciones`
  (el encargado vigente es la última fila; cambiarlo agrega una fila). No se borran ni se modifican (triggers) y
  ni `import` ni `evaluate` las tocan.
- **Lógica:** `app/seguimiento.py`. La regla de acceso es una sola función, `puede_entrar`: un administrador o el
  encargado vigente. Cada cambio va a `audit_log` («Dio seguimiento a un cartel», «Asignó el encargado…»).
- **Panel:** botón y marca en la página del cartel; marca en el panel de carteles; página `/seguimiento` (todos);
  expediente `/seguimiento/<N.º>` (encargado y administradores; los demás reciben «Este expediente es de…», 403);
  formulario de asignación solo para administradores.
- **Pruebas:** `tests/test_seguimiento.py` (10, datos SINTÉTICOS). La de acceso se comprobó con la regla rota a
  propósito: falla.
- **Para usarlo en una base existente:** respaldo y `python -m app.cli migrate` (aplica la 0015).

### Paso 1B, cómo quedó (2026-10-29, plan aprobado por Ivania)

- **Al asignar o cambiar el encargado** queda un aviso «preparado» en la outbox (motivo `asignacion`, migración
  `0024_aviso_encargado.sql`), en la misma transacción que la asignación. Va al correo del usuario encargado: no
  tiene que estar en «Destinatarios». Clave de deduplicación: encargado | N.º SICOP | id de la asignación |
  `asignacion`. Si el administrador se asigna a sí mismo, no se prepara.
- **Sale con el ciclo diario** (`app/aviso_encargado.py`, paso nuevo de `run-cycle`), en dry-run o real según el
  ciclo, aunque la fuente haya fallado (no depende de los datos del día). Un correo por encargado con todas sus
  asignaciones: título, institución, cierre, quién lo asignó, quién lo tenía antes y el enlace al expediente.
- **Solo lo vigente:** si el cartel cambió de encargado antes del envío o el usuario se desactivó, ese aviso no
  sale (queda «preparado», no se borra). Un cartel ya cerrado sí sale: el expediente sigue sirviendo.
- **No entra en el correo diario** de oportunidades. Si falla, aparece en «Avisos» como «Correo al nuevo
  encargado» y se reintenta mientras la asignación siga vigente.
- **Pruebas:** `tests/test_aviso_encargado.py` (11, datos SINTÉTICOS y envío SIMULADO), más la 0024 en las listas
  de migraciones.
- **Para usarlo en una base existente:** respaldo y `python -m app.cli migrate` (aplica la 0024).

### Paso 2, cómo quedó (2026-10-29, plan aprobado por Ivania)

- **Tabla** (migración `0027_expediente_archivos.sql`): `seguimiento_archivos`, una fila por archivo subido. No se
  borra ni se modifica (triggers); el mismo archivo (misma huella) no entra dos veces en el mismo expediente.
- **Lógica:** `app/expediente_archivos.py`. Tipos PDF, Word (`.docx`, `.doc`), Excel (`.xlsx`, `.xls`) y ZIP; se
  comprueba el **contenido** (firma de los primeros bytes; un `.docx` / `.xlsx` tiene que traer sus piezas de Word /
  Excel), no solo la extensión. Tamaño máximo `EXPEDIENTE_MAX_MB` (10), cortado al copiar y, si la petición lo
  declara, antes de recibirla.
- **En disco:** `EXPEDIENTES_DIR/<N.º SICOP>/<sha256>.<extensión>` (por defecto `data/expedientes`, fuera de Git).
  El nombre que manda el navegador solo se muestra (sin carpetas ni caracteres de control); nunca es una ruta.
- **Panel:** sección «Archivos» del expediente: subir, lista (nombre, tipo, tamaño, quién y cuándo), «Descargar» y
  «Ver» para PDF, Excel y ZIP (el mismo visor de los documentos de SICOP; Word y `.xls` solo se descargan).
  Suben, bajan y ven el encargado vigente y los administradores: en un traspaso, el encargado nuevo baja todo y el
  anterior ya no. Cada subida va a `audit_log`.
- **Respaldo:** `backup` guarda también `sicop_<fecha>_expedientes.zip` con la carpeta.
- **Pruebas:** `tests/test_expediente_archivos.py` (21, archivos SINTÉTICOS). La de acceso se comprobó con la regla
  rota a propósito: falla.
- **Para usarlo en una base existente:** respaldo y `python -m app.cli migrate` (aplica la 0027).
- **Fuera de este paso:** quitar o archivar un archivo subido por error (hoy nada se borra).

### Paso 3, cómo quedó (2026-10-30, pedido por Ivania)

- **Tabla** (migración `0028_expediente_notas.sql`): `seguimiento_notas`, una fila por nota, con autor (el nombre
  se copia) y fecha en hora de Costa Rica. No se borra ni se modifica (triggers): para corregir, otra nota. Hasta
  2000 caracteres (como el comentario de una revisión); la base pone el mismo tope.
- **Lógica:** `seguimiento.escribir_nota` y `seguimiento.notas_de` (de la más reciente a la más vieja). Se quitan
  los espacios de los extremos y los saltos de línea se guardan como LF.
- **Panel:** sección «Notas» del expediente: formulario y lista con autor y fecha; los saltos de línea se
  respetan y el texto se muestra como texto (nunca como HTML). Si hay un error, el texto vuelve al formulario.
  Escriben y leen el encargado vigente y los administradores: en un traspaso, el encargado nuevo lee todo y el
  anterior ya no.
- **Historial (`audit_log`):** «Escribió una nota…» con el número de la nota, **sin el texto**: el texto solo vive
  en el expediente, con su regla de acceso (el historial es otro registro de la base y no la tiene).
- **Pruebas:** 4 nuevas en `tests/test_seguimiento.py` (SINTÉTICO). La de acceso se comprobó con la regla rota a
  propósito: falla.
- **Para usarlo en una base existente:** respaldo y `python -m app.cli migrate` (aplica la 0028).

### Paso 4, cómo quedó (2026-10-30, pedido por Ivania)

- **Botón «Descargar todo el expediente (ZIP)»** en el expediente → `GET /seguimiento/<N.º>/descargar`. Lo usan
  el encargado vigente y los administradores (la misma regla `puede_entrar`): en un traspaso, la persona nueva
  baja todo y la anterior ya no. Sin migración ni dependencias nuevas.
- **El ZIP** (`expediente_<N.º>_<aaaammdd-hhmm>.zip`, `app/expediente_descarga.py`) trae:
  - `expediente.txt` (UTF-8): datos del cartel, encargado y etapa vigentes, historial de encargados, etapas, notas
    y la lista de archivos con tipo, tamaño, quién lo subió, fecha y huella SHA-256 (para comprobar que llegaron
    completos);
  - `archivos/`: los archivos con el nombre que se ve en el panel; si dos se llaman igual, el segundo lleva « (2)».
  - Un archivo que falta en disco no detiene la descarga: `expediente.txt` dice «FALTA EN DISCO».
- **No van** los documentos de SICOP del cartel (se bajan desde la página del cartel; pueden pesar hasta 100 MB).
- **Se arma en un archivo temporal**, no en memoria, y se borra después de enviarlo.
- **Historial (`audit_log`):** «Descargó todo el expediente…» con cuántos archivos y notas llevaba. Solo se anotan
  las descargas permitidas.
- **Pruebas:** `tests/test_expediente_descarga.py` (6, SINTÉTICO) y la ruta en `test_anonimo_es_redirigido_al_login`.
  La de acceso se comprobó con la regla rota a propósito: falla.

### Paso 5, cómo quedó (2026-10-29, plan aprobado por Ivania)

- **Tabla** (migración `0025_seguimiento_etapas.sql`): `seguimiento_etapas`. La etapa vigente es la última fila;
  sin filas, el cartel está «preparando» (así empieza al darle seguimiento). No se borra ni se modifica (triggers);
  la base solo acepta las cuatro etapas.
- **Quién la cambia:** el encargado vigente y los administradores (la misma regla `puede_entrar`). Cualquier cambio
  vale, también volver atrás, para corregir. Cada cambio va a `audit_log` («Cambió la etapa…: Preparando → Enviada»).
- **Panel:** botones en la sección «Etapa» del expediente, con su historial; la etapa se ve en la marca del cartel y
  del panel («En seguimiento · Ivania · enviada») y en la página «Seguimiento».
- **Se suma a las decisiones:** no cambia «Ofertada» ni «No se oferta». En «enviada», si el cartel no está marcado
  «Ofertada», el expediente lo sugiere con un enlace a la revisión; no se hace solo.
- **Pruebas:** 5 nuevas en `tests/test_seguimiento.py` (SINTÉTICO).
- **Para usarlo en una base existente:** respaldo y `python -m app.cli migrate` (aplica la 0025).
- **Fuera de este paso (ideas):** aviso por correo al cambiar la etapa; ligar «ganada/perdida» con las
  adjudicaciones de SICOP.

## Reglas que aplican (de `CLAUDE.md` y del resto del proyecto)

- **Nada se borra al actualizar datos.** Igual que las revisiones: una importación o una reevaluación no toca
  expedientes, notas, archivos ni el historial de encargados. Un cambio de encargado se agrega al historial, no
  reemplaza el anterior.
- **Archivos fuera de Git y de la base**, en una carpeta de datos (p. ej. `data/expedientes/<N.º SICOP>/`), con
  su huella SHA-256: la misma huella que ya se usa para las importaciones. Se comprueba el tipo real del archivo,
  no solo la extensión, y el nombre que llega no se usa como ruta.
- **Número SICOP siempre como texto.**
- **Correo al encargado** por la misma outbox de los avisos, con clave de deduplicación (no se repite) y en
  dry-run hasta que se decida el envío real. Nunca un envío real sin instrucción.
- **Seguridad del panel:** sesión obligatoria y token CSRF en cada formulario, como en el resto de las páginas;
  cada cambio va a `audit_log`.
- **Respaldos:** `backup` hoy copia la base. Con archivos, el respaldo tiene que incluir también la carpeta de
  expedientes, y hay que medir cuánto espacio ocupa en el servidor (Oscar hace los respaldos del servidor).
- **El pliego se sube a mano:** SICOP no permite descargarlo con un programa (respuesta del 26/10,
  `DECISION_OBTENCION.md` §8).
