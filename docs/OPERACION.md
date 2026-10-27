# Operación de SICOP CONNECT — borrador

Cómo se usa la app en el día a día: importar, revisar, enviar avisos, diagnosticar y recuperar (entregable E6
de la guía). La instalación, la actualización y la reversión están en `docs/DESPLIEGUE.md`.

Estado: **borrador** (2026-10-16). Secciones 1 a 6 probadas paso por paso en Windows con datos reales
(2026-10-19, Ivania con Claude) y corregidas con lo encontrado. Revisado contra el código de `desarrollo` el
2026-10-23 (ZIP sin descomprimir, adjudicaciones, A4, A5, aviso de datos sin evaluar) y **seguido al pie de la
letra en una instalación limpia** el mismo día (Ivania, Python 3.12, `C:\Users\User\sicop-prueba`; lección 18,
paso 2): README, secciones 1 a 6 en Windows; se corrigieron las 10 trabas encontradas. Falta probar en el servidor
las partes 🐧 y terminar los simulacros (sección 7).

## Cómo se corre un comando

Todos los comandos son `python -m app.cli <comando>`. Dónde se escriben:

- 🪟 **Windows (desarrollo):** en PowerShell, dentro de `C:\Users\User\sicop-connect`, con
  `.venv\Scripts\python -m app.cli <comando>`. Usa la base `data/sicop.db`.
- 🐧 **Servidor:** con la misma configuración que el servicio, sin mostrar secretos (`DESPLIEGUE.md`, 9.5):

  ```bash
  sudo systemd-run --uid=sicop --pty --wait \
    -p EnvironmentFile=/etc/sicop-connect/app.env \
    -p WorkingDirectory=/opt/sicop-connect \
    /opt/sicop-connect/.venv/bin/python -m app.cli <comando>
  ```

`python -m app.cli --help` lista todos los comandos; `python -m app.cli <comando> --help`, sus opciones.

**Comandos largos:** al copiarlos, una ruta larga puede partirse en dos líneas y el comando hace otra cosa (por
ejemplo, `Copy-Item` sin destino copia a la carpeta actual). Por eso en este manual las rutas largas van en una
variable corta, en su propia línea, y cada comando va solo:

```powershell
$z = "C:\Users\User\sicop-connect\data\incoming\procesados\2026-10-22"
Copy-Item "$z\Reporte de adjudicaciones en firme.zip" .
```

Una variable (`$z`) dura hasta cerrar la ventana de PowerShell: en una ventana nueva hay que escribirla otra vez.

## Niveles de acceso al panel

| Nivel | Puede |
|---|---|
| Encargado (`encargado`) | Ver oportunidades, guardar revisiones y cargar archivos de SICOP. |
| Administrador (`admin`) | Lo mismo, más «Destinatarios», «Usuarios» y «Avisos». |

## 1. Importar

### 1.1 Descargar de SICOP

La obtención es **manual**: una persona descarga los reportes del portal de datos abiertos de SICOP. Cómo se
hace y qué se observó: `docs/ACCESO_SICOP.md`.

- Los carteles salen del reporte **«Detalle pliego de condiciones»** (no es el pliego en PDF de un concurso).
- Llega como **ZIP** con dos CSV: `Detalle de pliegos de condiciones.csv` (carteles) y `Detalles lineas.csv`
  (líneas). **No hace falta descomprimirlo:** el panel (tipo «pliegos») y el ciclo lo importan tal como llega.
  Si alguien ya lo descomprimió, también se pueden cargar los dos CSV; el mismo archivo nunca se importa dos veces.
- **Adjudicaciones en firme** (página «Competencia»): también llega como ZIP, con tres CSV. Se importa tal como
  llega, por la carpeta de entrada o por la terminal (`--report adjudicaciones`); el panel no lo carga.
- **Catálogo de bienes y servicios** (reporte 10.2): da el nombre de cada código de las líneas. **Sin él se
  pierden candidatos**: algunos carteles solo se reconocen por el nombre de catálogo de sus líneas (por ejemplo,
  data loggers comprados como «equipo de laboratorio»), y la calidad de datos queda en «Código sin catálogo». El
  portal lo entrega **un código de clasificación de 8 dígitos por vez**; los que se usan hoy son `83111602`
  (GPS y flotas), `41112301` (IoT y frío) y `45121515` (cámaras corporales) (`docs/ACCESO_SICOP.md`). No cambia
  cada día: se carga una vez y se repite solo si se agrega una clasificación.
- **Instituciones compradoras** (reporte 11): da el nombre de cada institución. Sin él, el panel muestra la cédula.
  Tampoco cambia cada día.

### 1.2 Cargar los archivos

Tres formas; las tres usan el mismo importador:

- **Panel → «Cargar archivo»:** elegir el tipo de reporte, el origen (real, sintético o simulado; «real» viene
  elegido) y el archivo. La página trae un botón que abre en Gmail el correo «Envío de reporte» de SICOP, otro a
  Datos abiertos de SICOP y los pasos explicados.
  **Para los carteles del día, el tipo es «pliegos (.zip)»** con el ZIP tal como llega: trae carteles y líneas y
  se carga **una sola vez**. Los tipos «carteles» y «lineas» son solo para un CSV que alguien ya sacó del ZIP; si
  después se sube el ZIP, lo ya cargado sale como «Este archivo ya se importó» y no se duplica. Instituciones va en
  `.csv`; el catálogo, en `.csv` o `.zip`.
  Lo que se sube queda guardado en `INCOMING_DIR`; el siguiente ciclo lo ve como «YA IMPORTADO» y lo pasa a
  `procesados` (no lo importa otra vez).
- **Carpeta de entrada:** dejar los archivos en `INCOMING_DIR` **antes de las 8:00**; el ciclo los importa solo
  (sección 3). 🪟 Windows: `C:\Users\User\sicop-connect\data\incoming` · 🐧 servidor:
  `/var/lib/sicop-connect/incoming`. `doctor` muestra la ruta en uso.
- **Terminal:** `python -m app.cli import --path ARCHIVO --report carteles --origen real` (también `lineas`,
  `catalogo`, `instituciones` y `adjudicaciones`).

Reglas:

- **Orden:** instituciones → carteles → catálogo → líneas → adjudicaciones (el ciclo lo respeta solo). Una línea
  cuyo cartel todavía no se importó queda guardada aparte y entra sola cuando llega su cartel.
- **Origen:** siempre el verdadero. `real` es lo descargado de SICOP; `sintetico` y `simulado`, solo para pruebas.
- **Repetir es seguro:** el mismo archivo (mismo hash) no se importa dos veces, y actualizar un cartel nunca
  borra sus revisiones.
- El resumen muestra filas leídas, aceptadas, rechazadas (con el motivo) y advertencias. Una fila rechazada no
  detiene el resto.

### 1.3 Evaluar

**Subirlo en el panel («Cargar archivo») lo evalúa enseguida** (desde 2026-10-26): al terminar de importar, la
página evalúa todos los carteles con las reglas (`config/hermatix_rules.yaml`), tarda unos 15 s con la base real y
muestra cuántos quedaron en Alta y en Media. **Importar por la terminal (`import`) no evalúa**: después hay que correr

```
python -m app.cli evaluate
```

El ciclo diario evalúa solo. Si el panel dice «Todavía no hay evaluaciones», «Las reglas cambiaron» o «Hay
datos importados después de la última evaluación», hay que correr `evaluate`. Cómo leer su salida y cómo cambiar
una regla: `docs/REGLAS.md`.

El panel muestra la última evaluación **completa**: `evaluate --nro NRO_SICOP` (un solo cartel) sirve para ver
por qué salió así, pero no cambia lo que muestra el panel.

## 2. Revisar

1. **Panel de carteles:** la lista de oportunidades, con búsqueda y filtros por prioridad, plazo, familia,
   institución, tipo de procedimiento y si ya se revisó.
2. Abrir un cartel: muestra la evidencia (las frases que coincidieron), el comprador, las líneas y el plazo.
3. Guardar la decisión: «Interesa», «No interesa» o «Revisar requisitos» mientras se estudia; «Ofertada» o
   «No se oferta» como decisión final. Si no interesa, con el motivo, y un comentario. Queda a nombre del
   usuario que inició sesión. Si se anota la decisión de otra persona, se escribe en el comentario.

- La prioridad dice **encaje con el portafolio de Hermatix**, no si Hermatix puede participar o ganar.
- **Un cartel vencido sale solo del panel** en cuanto pasa su fecha de cierre (decisión de Ivania, 2026-10-26).
  No se borra nada: se ve eligiendo «Vencido» en el filtro de Plazo (y la exportación a Excel hace lo mismo), y
  si está en «Seguimiento» sigue apareciendo allí.
- Un cartel que cierra el fin de semana se trata igual que cualquier otro (decisión de Ivania, 2026-10-16).
- **Exportar a Excel:** el botón del panel de carteles baja el listado con los mismos filtros (todas las
  páginas). Los números SICOP quedan como texto: no se dañan al abrirlos.
- **Competencia:** quién gana qué por familia, con montos por moneda, a partir de las adjudicaciones importadas.
  Los ganadores vienen solo con cédula; el nombre se pone en `config/competidores.yaml`.
- **Seguimiento (gestor de documentos):** en la página del cartel, «Dar seguimiento» (cualquier usuario) lo pone
  en la página «Seguimiento» como «sin encargado». Un administrador abre el expediente y elige el encargado (o lo
  cambia: el anterior queda en el historial). El expediente lo ven solo su encargado y los administradores; los
  demás ven «En seguimiento · <nombre>» en el panel. Detalle: `docs/GESTOR_DOCUMENTOS.md`.

## 3. El ciclo diario

`run-cycle` hace todo en orden: **recoger** `INCOMING_DIR` → **importar** → **evaluar** → **avisar**.

```
python -m app.cli run-cycle --origen real --dry-run    # avisos solo en vista previa (por defecto)
python -m app.cli run-cycle --origen real --send       # envío real
```

- En el servidor lo corre el temporizador `sicop-cycle.timer`, **de lunes a viernes a las 8:00** (hora de Costa
  Rica). **Todavía no está activado** (lección 10): primero en dry-run y después el envío real, siguiendo
  `DESPLIEGUE.md`, 9.6, con autorización de Oscar.
- **En Windows (local):** una tarea del Programador de tareas corre el mismo ciclo, siempre en dry-run, de lunes
  a viernes a las 8:00, con registro en `data\logs\`. Cómo crearla, probarla y borrarla:
  `deploy/windows/README.md`.
- Los archivos importados pasan a `INCOMING_DIR/procesados/<fecha>/`. Uno incompleto, ilegible o no reconocido
  **no se importa**: pasa a `INCOMING_DIR/con_error/<fecha>/` y el ciclo termina en «fallo».
- El ZIP de pliegos y el de adjudicaciones se importan sin descomprimir; el ZIP se mueve entero (a
  `procesados` o, si uno de sus CSV falla, a `con_error`).
- Si no llegó ningún archivo nuevo o la fuente falló, se evalúa igual (los plazos cambian con el día), pero
  **no se avisa**: un correo sin los datos del día daría a entender que no hubo compras. **El ciclo termina en
  «FALLO» y con código `1`**, a propósito, para que se note que ese día no hubo datos. También pasa si los
  archivos del día **ya se cargaron desde el panel**: quedan en `INCOMING_DIR`, pero el ciclo los ve como «YA
  IMPORTADO», no como nuevos (y los pasa a `procesados`). Y si solo llegaron adjudicaciones (se importan, pero no
  traen carteles nuevos). La excepción son los avisos de **cierre próximo** (4.1): el plazo corre igual, así que
  salen aunque falten los datos del día.
- **Los lunes** el ciclo arma además el resumen semanal (4.1), con el mismo modo (dry-run o envío).
- Resultado: `0` = ok · `1` = fallo (queda registrado) · `2` = ya había otro ciclo en curso. En PowerShell, el
  código del último comando se ve con `$LASTEXITCODE`.
- **El número del ciclo** («Ciclo #7») es el de su registro en `source_runs`, donde también cuenta cada
  importación hecha desde el panel o la terminal. Por eso los números saltan: el primer ciclo de una base nueva
  puede ser el #7. No falta nada.
- **En el servidor, mientras la descarga sea manual:** cada día hábil que nadie deje los archivos en
  `INCOMING_DIR` antes de las 8:00, el ciclo sale en «fallo» y systemd marca `sicop-cycle.service` como fallido.
  Ese «fallo» significa **«nadie cargó los datos de hoy»**, no que la app esté rota. Se resuelve cargando los
  archivos (sección 1); no hace falta tocar el servidor.
- Efecto conocido: un cartel cargado el viernes después de las 8:00 que cierra el sábado o el domingo no se
  avisa por correo (el lunes ya venció). Sí aparece en el panel.

### 3.1 Obtención automática (`obtain auto`, lección 4)

**Estado (2026-10-26): lista para activarse en el servidor** (`DESPLIEGUE.md` 9.9, la activa Oscar). En la única
prueba real, SICOP rechazó la descarga hecha por el programa; Oscar decidió **descarga a mano** con recordatorio
(`DECISION_OBTENCION.md` §8, regla 12). En local sigue `SOURCE_MODE=manual`. No se llama «automática» hasta que un
ciclo real lo demuestre.

**Rutina diaria en el servidor (lunes a viernes):**
1. 06:30 y 14:00: la app pide el reporte sola. Nadie hace nada.
2. Llega el correo «SICOP CONNECT · descargar el reporte de las 06:30» (o de las 14:00) a `OBTAIN_ALERT_TO`.
3. Abrir el correo de SICOP «Envío de reporte» (botón «Abrir el correo de SICOP en Gmail» en «Cargar archivo»),
   bajar el ZIP sin abrirlo y subirlo en «Cargar archivo» como «pliegos», origen «real». **El mismo día**: el
   enlace vence. Al subirlo se importa y se evalúa: los carteles nuevos ya se ven en el panel.
4. **08:00: sale el correo de avisos**, con todo lo subido desde el correo anterior (el de las 06:30, si se subió
   antes de las 8:00, y el de las 14:00 del día anterior). Es el único momento en que se envían avisos.

`python -m app.cli obtain auto` es **una vuelta**; en el servidor la repite `sicop-obtain.timer` cada 15 min, de
06:00 a 19:45, de lunes a viernes. En Windows, la tarea «SICOP CONNECT - obtencion» (`deploy/windows/README.md`).
La vuelta **no corre el ciclo ni manda avisos de oportunidades**: eso lo hace el ciclo de las 8:00
(`sicop-cycle.timer`, `run-cycle --send`). Cada vuelta:

1. Con `SOURCE_MODE=manual` no hace nada (no abre SICOP ni lee Gmail).
2. Cada hora de `OBTAIN_REQUEST_HOUR` es un turno (servidor: `06:30,14:00`). Si el turno no tiene solicitud,
   pide el reporte. **Una por turno:** si la del turno falló, no se pide otra hasta el turno siguiente. Si al pedir
   la de las 14:00 sigue esperando el enlace la de las 06:30, esa se cierra como FALLO (con su alerta).
3. Si hay una solicitud abierta, revisa el buzón. Con `OBTAIN_DOWNLOAD=manual` (por defecto), al llegar el enlace
   la solicitud queda `ENLACE_RECIBIDO` y **no se descarga**; con `auto`: descarga → validación → `INCOMING_DIR`.
4. Correos a `OBTAIN_ALERT_TO`, uno por solicitud: el **recordatorio** de descargar y subir, o la **alerta** de
   FALLO con el plan B. Mientras los avisos estén en dry-run, son solo archivos:
   `EXPORTS_DIR\recordatorio-obtencion-<n>.txt` y `EXPORTS_DIR\alerta-obtencion-<n>.txt`. Nunca llevan el enlace
   ni el código.
El ciclo de las 8:00 toma lo que haya en `INCOMING_DIR`. Un ZIP **subido en el panel** ya está importado y
evaluado, pero cuenta como **datos nuevos** para el correo (una sola vez: después pasa a `procesados`).

**Activar:** en `.env`, `SOURCE_MODE=auto`, `OBTAIN_ALERT_TO=` (el buzón de la alerta) y `migrate`; luego crear la
tarea, **sin** pausar la de las 8:00: esa manda los avisos (`deploy/windows/README.md`). **Volver a manual:** `SOURCE_MODE=manual`. No hay que
tocar código ni borrar la tarea; desde la vuelta siguiente no hace nada.

**Qué hacer ante cada FALLO** (aparece en el registro, en la alerta y en `obtain status`):

| Motivo | Qué significa | Qué hacer |
|---|---|---|
| «control no automatizable» (CAPTCHA o bloqueo, con ID de soporte) | SICOP no dejó pasar al programa | Plan B. No reintentar ni «arreglar» el programa para pasar el control. Anotar el ID de soporte para SICOP. |
| «Enlace vencido o SICOP no inició la descarga» | El enlace no entregó el archivo | Plan B con el mismo correo. |
| «El archivo descargado no es válido: …» | Llegó algo que no es el reporte | Revisar el archivo en `RAW_DATA_DIR\descargas`; plan B. |
| «No llegó el correo con el código» / «El enlace no llegó en 12 h» | SICOP no mandó el correo a tiempo | Buscar en Gmail (otra carpeta, otro asunto). Si hace falta el reporte, pedirlo a mano (sección 1.1). |
| «No se pudo abrir Gmail» | El permiso de lectura venció o se revocó | Renovarlo (abajo). |
| «Ciclo #n: …» | Falló el ciclo, no la obtención | Sección 3 y sección 5. |

**Plan B (un clic):** abrir en el buzón de SICOP el correo «Envío de reporte» de hoy, hacer clic en el enlace,
guardar el ZIP sin abrirlo en Excel y subirlo en «Cargar archivo» (se importa y evalúa al subirlo). Los avisos
salen con el correo de las 8:00.

**Renovar el acceso a Gmail (lectura):** `python -m app.cli obtain gmail-auth`, entrando con el buzón de
`SICOP_REQUEST_EMAIL`. Después, `python -m app.cli obtain check-mail` para comprobar. El permiso de enviar avisos
es otro (`google-auth`, sección 4).

**Dónde mirar:**
- `python -m app.cli obtain status`: las últimas solicitudes, con la hora de cada paso, el motivo y la alerta.
- `data\logs\obtencion-AAAA-MM.log`: la salida de cada vuelta de la tarea.
- `EXPORTS_DIR`: capturas de los fallos de la solicitud (`obtencion-fallo-…png`) y las alertas en vista previa.
- `RAW_DATA_DIR\descargas`: los ZIP descargados tal como llegaron y la captura de un fallo de descarga.

### 3.2 Enriquecimiento de carteles (`enrich`, guía de enriquecimiento)

Trae de la consulta pública de SICOP la **ficha** del concurso (estado, fechas, versión, garantías…) y sus
**documentos** (PDF con su texto, ZIP, Word, Excel), unidos al cartel por su Número SICOP. Detalle de los campos:
`docs/DETALLE_CARTEL.md`. Siempre con la ventana del navegador visible y grabando cada consulta.

| Comando | Qué hace |
|---|---|
| `enrich --nro N [--nro N…] [--documentos]` | 1 a 3 carteles a mano |
| `enrich cola` | La cola de hoy (sin consultar SICOP), cuáles caben en el máximo del día y qué se borrará al cierre |
| `enrich run [--max N]` | La corrida automática (la tarea de las 10:00): la cola del día con fichas y documentos |
| `enrich status` | Últimas corridas y consultas (la bitácora) |

**Activar o pausar:** `ENRICH_ENABLED=true` / `false` en `.env`. Con `false`, `enrich run` no consulta nada (la
tarea programada puede seguir activa). La tarea: `deploy/windows/README.md`.

**Qué entra en la cola:** los carteles del panel (encaje Alta, Media o Baja), con plazo abierto (según la ficha si
ya existe), y que nunca se hayan enriquecido, o que los datos abiertos los vieran después de la última ficha, o que
cierren en 3 días o menos. Lo ya consultado hoy no vuelve. Máximo `ENRICH_MAX_PER_DAY` (20) por día, en orden
**Alta → Media → Baja** y, dentro de cada uno, primero lo que cierra antes (decisión de Oscar, 27/10).

**Ante un FALLO de un cartel** (no encontrado, la página cambió, un documento no llegó): queda en `enrich status` y
en el resumen con su motivo; la cola sigue con los demás. Mirar el video y la captura; si SICOP cambió la página,
pedir el ajuste con el prompt «Cuando la ficha de SICOP cambia» de la guía.

**Ante un CAPTCHA, un bloqueo o «No fue posible acceder…»:** se espera `ENRICH_RETRY_WAIT_MINUTES` (15) con el
navegador cerrado y se reintenta **una sola vez** por corrida (decisión de Oscar, 27/10); el CAPTCHA nunca se
resuelve ni se intenta evitar. Si vuelve a salir, la corrida se **detiene** y sale la alerta (a `OBTAIN_ALERT_TO`;
en dry-run, `data\exports\alerta-enriquecimiento-<n>.txt`). Poner `ENRICH_ENABLED=false`, mirar el video y avisar
a Oscar. Si el reintento salió bien, el resumen lo dice.

**Borrado al cierre:** al empezar cada `enrich run` se borran la ficha, los documentos (y su carpeta en
`data\documentos`) y el texto de los carteles cuyo cierre ya pasó (la fecha más tardía entre la ficha y los datos
abiertos, por si se prorrogó), **menos** los que alguien marcó «Interesa» u «Ofertada» o que tienen seguimiento
(decisión de Oscar, 27/10). El cartel, sus revisiones y la bitácora quedan; cada borrado se anota en
`enrich_retiros`. `enrich cola` muestra lo que se borrará en la próxima corrida. Los respaldos anteriores lo
conservan. Para conservar uno, marcarlo «Interesa» **antes** de su cierre.

**Ver un video:** la bitácora dice la carpeta de cada consulta (`AAAA-MM-DD/<nro>/HHMMSS`) dentro de
`RECORDINGS_DIR` (`data\grabaciones`): ahí están `HHMMSS-video.webm` (se abre con el navegador) y una captura por
paso. Se guardan `RECORDINGS_KEEP_DAYS` (30) días; las de una consulta con FALLO o CAPTCHA no se borran.

**Si el equipo de consulta estuvo apagado** (o con la sesión cerrada o la pantalla bloqueada a las 10:00): ese día
no hubo consultas; no se pierde nada, la cola espera. El resumen del día siguiente dice cuántos días hábiles no hubo
corrida. Se puede correr a mano: `enrich run`.

**Resumen diario:** al terminar cada corrida, «N consultados, M FALLO» con lo nuevo de cada cartel (a
`OBTAIN_ALERT_TO`; en dry-run, `data\exports\resumen-enriquecimiento-<n>.txt`).

## 4. Enviar avisos

### 4.1 Qué se avisa

Carteles con prioridad **Alta** o **Media**, con el plazo no vencido, cuya **versión** se vio en los últimos
`NOTIFY_LOOKBACK_DAYS` días (7). Un cartel viejo que cambia vuelve a contar. A cada destinatario le llega **un
correo resumen**. Se vuelve a avisar solo si el cartel cambió (otra versión u otra fecha de cierre). Los
destinatarios se editan en el panel → «Destinatarios» (solo administradores).

Además, en el mismo correo:

- **Cierre próximo:** un cartel cuya última revisión es «Interesa» o «Revisar requisitos» (sin decisión final)
  y que cierra en `NOTIFY_CLOSING_DAYS` días o menos (3), aunque no sea Alta ni Media. Una vez por versión.

Y aparte, **los lunes**, el **resumen semanal** de la semana anterior: nuevas por familia, revisadas, pendientes
sin revisar, cierres de los próximos 7 días y, si hay, adjudicaciones relevantes. Uno por destinatario y semana.

**La revisión no cuenta para los avisos de cartel nuevo:** un cartel marcado «No interesa» igual sale en el correo si cumple lo
anterior. El correo anuncia lo nuevo antes de que alguien lo revise. Para que un falso positivo deje de salir hay
que ajustar la regla (`docs/REGLAS.md`). Ejemplo (2026-10-19): «Cámaras intraorales…» de la CCSS (`20261001749`)
salió como Media por «cámaras» + «transporte».

### 4.2 Comandos

```
python -m app.cli notify --dry-run                     # prepara y escribe la vista previa en EXPORTS_DIR
python -m app.cli notify --send                        # envío real por Gmail
python -m app.cli notify --send --solo CORREO          # solo a un destinatario activo (prueba controlada)
python -m app.cli notify --resumen-semanal --dry-run   # el resumen semanal (el ciclo lo arma solo los lunes)
```

`--send` exige `NOTIFICATIONS_ENABLED=true`, `NOTIFICATIONS_DRY_RUN=false` y los archivos de Google
(`docs/GOOGLE_API.md`). Repetir no duplica avisos.

### 4.3 Estados de un aviso

| Estado | Qué significa | Qué hacer |
|---|---|---|
| preparado | En la cola: sale en el siguiente envío. | Nada. |
| aceptado | Gmail lo recibió. **No** garantiza que llegó a la bandeja. | Nada. |
| fallido | Gmail lo rechazó. | Revisar el motivo y reintentar (4.4). |
| incierto | Sin respuesta clara: puede que sí haya salido. | Revisar Gmail › Enviados (4.4). |

Un fallido o un incierto **nunca se reenvía solo**.

### 4.4 Revisar un aviso fallido o incierto

> Página en `main` desde el 2026-10-19 (PR #2). El servidor la tendrá cuando se actualice a esa versión.

Panel → «Avisos» (solo administradores):

- **Fallido:** «Reintentar» lo vuelve a «preparado» y sale en el siguiente envío. Si Gmail lo rechazó por la
  dirección, conviene corregirla antes en «Destinatarios».
- **Incierto:** primero buscarlo en Gmail › Enviados de la cuenta que envía los avisos.
  - Está en Enviados → «Sí salió»: queda «aceptado» y no se reenvía.
  - No está → marcar «Revisé Gmail › Enviados y no está» y «Reintentar».
- No deja reintentar si el cartel ya cerró, si el destinatario fue quitado o si ya le llegó una versión más
  nueva del cartel. Cada decisión queda en el historial de la página.
- **Resumen semanal** fallido o incierto: aparece como «Resumen semanal AAAA-Wnn». Solo se reintenta en su misma
  semana y sale con `notify --resumen-semanal --send`.

## 5. Diagnosticar

### 5.1 Primer paso: `doctor`

```
python -m app.cli doctor
```

Muestra, sin secretos: de dónde salió la configuración, qué falta, si la base está lista, si los avisos y el
programador están habilitados y si existen los archivos de Google.

**Un «PENDIENTE» no siempre es un problema.** En una instalación de desarrollo, solo con vista previa, estos son
normales:

| Pendiente | Para qué es | ¿Falta de verdad? |
|---|---|---|
| `MAIL_FROM`, `GOOGLE_CLIENT_FILE`, `GOOGLE_TOKEN_FILE` | Enviar avisos reales por Gmail | Solo para `--send` |
| `SESSION_SECRET` | Firmar la sesión del panel | En desarrollo se usa uno temporal; **en el servidor es obligatorio** (la app no arranca sin él) |
| `GOOGLE_READ_TOKEN_FILE`, `SICOP_REQUEST_EMAIL`, `OBTAIN_ALERT_TO` | Obtención automática | Solo con `SOURCE_MODE=auto` |

Lo que sí hay que mirar siempre: que `Base de datos` diga «ok» y que la ruta de `DATABASE_PATH` sea la esperada.

### 5.2 En el servidor

```bash
sudo systemctl status sicop-web.service                     # ¿el panel está corriendo?
sudo journalctl -u sicop-web.service -n 50 --no-pager       # lo último que registró el panel
sudo journalctl -u sicop-cycle.service -n 50 --no-pager     # el último ciclo
sudo systemctl list-timers sicop-cycle.timer                # ¿cuándo corre el próximo ciclo?
curl -f http://127.0.0.1:8000/health                        # el panel responde
```

### 5.3 Mensajes frecuentes

| Mensaje o síntoma | Causa | Qué hacer |
|---|---|---|
| Panel vacío: «Todavía no hay evaluaciones» | Se importó, pero no se evaluó. | `evaluate` (1.3). |
| Panel vacío: «Todavía no hay evaluaciones» y `evaluate` dice 0 carteles | La base no tiene carteles: es nueva o no es la que se esperaba. | Revisar `DATABASE_PATH` con `doctor`; cargar los archivos (1.2) o restaurar el respaldo (6.2). |
| «Hay datos importados después de la última evaluación» | Se cargaron, pero no se evaluaron. | `evaluate` (1.3). |
| «Las reglas cambiaron…» | Se editó el YAML después de la última evaluación. | `evaluate`. |
| «Faltan migraciones… ejecuta migrate» | El código es más nuevo que la base. | `migrate`. |
| «Este archivo ya se importó» | Mismo archivo (mismo hash). | Nada: no se duplicó. |
| Ciclo «fallo · no llegó ningún archivo nuevo» (código 1) | `INCOMING_DIR` vacío (también si se cargó desde el panel). | Cargar los archivos del día. No es una falla de la app. |
| Ciclo «fallo · solo llegaron adjudicaciones» | Se importaron, pero no hay carteles nuevos. | Cargar el ZIP de pliegos del día. |
| Ciclo «fallo» con un archivo en `con_error/` | Archivo incompleto, ilegible o no reconocido. | Descargarlo otra vez de SICOP. |
| «No se importó: no es UTF-8 ni cp1252…» | El archivo está dañado o no es un reporte de SICOP. | Descargarlo otra vez; no abrirlo en Excel. |
| «Ya hay un ciclo en curso» (código 2) | Otro ciclo está corriendo. | Esperar a que termine. |
| No deja entrar después de 5 intentos | Bloqueo de 15 min por correo + IP. | Esperar 15 min. |
| Alguien olvidó su contraseña | — | Un administrador: «Usuarios» o `set-password`. |
| Alguien deja la empresa | — | Un administrador: reasignar sus expedientes en «Seguimiento», quitar su correo de «Destinatarios» y en «Usuarios › Cambiar» usar «Eliminar usuario». No se deshace; sus revisiones se conservan. Para una ausencia temporal, «Desactivar». |

## 6. Recuperar

### 6.1 Respaldo

```
python -m app.cli backup --output CARPETA
```

Copia coherente de la base aunque esté en uso, más un manifiesto `.json` (fecha, commit, esquema, SHA-256,
integridad y filas por tabla). Nunca sobrescribe. La carpeta debe estar en **otro disco** u otro equipo.

- 🪟 Windows: `C:\Users\User\respaldos-sicop\`, fuera de Git; se usa el más reciente de la carpeta. **Esa carpeta
  está en el mismo disco que la base**: después de cada respaldo, comprimir el `.db` y su `.json` en un ZIP y
  subirlo a la carpeta del Drive de Hermatix que indique Oscar (compartida solo con él, sin enlace público).
  No subirlo a una nube personal: tiene datos de la empresa y los usuarios.

  Una línea por vez. La segunda elige sola el respaldo más reciente (escribir el nombre a mano lleva a errores):

  ```powershell
  $r = "C:\Users\User\respaldos-sicop"
  $n = (Get-ChildItem $r -Filter *.db | Sort-Object LastWriteTime | Select-Object -Last 1).BaseName
  Compress-Archive -Path "$r\$n.db", "$r\$n.json" -DestinationPath "$r\$n.zip"
  ```

  `Compress-Archive` nunca sobrescribe: si el ZIP ya existe, avisa y no hace nada. Para restaurarlo, se
  descomprime y se sigue 6.2 (primero se compara la huella).
- 🐧 Servidor: destino, retención y respaldo diario automático, **pendientes con Oscar**. Debe usar `backup`, no
  copiar el `.db` a mano (una copia mientras alguien escribe puede quedar dañada).

### 6.2 Si se daña la base

Restaurar el último respaldo (`DESPLIEGUE.md`, 9.7).

🐧 **Servidor:**

1. Detener el timer y el panel.
2. Comprobar el SHA-256 del `.db` contra el manifiesto.
3. Copiar el `.db` como `DATABASE_PATH` (en el servidor: propietario `sicop`, permisos `600`).
4. Arrancar `sicop-migrate.service` y luego `sicop-web.service`.
5. Abrir una revisión conocida para confirmar.

🪟 **Windows** (probado el 2026-10-19 en una carpeta aparte y el 2026-10-23 en una instalación limpia), dentro de
la carpeta del proyecto y con el entorno activado:

1. **Cerrar el panel** (Ctrl+C en la ventana de `uvicorn`) y esperar a que vuelva el `PS C:\...>`. Si sigue
   abierto, puede estar usando la base: Windows no deja renombrarla («está siendo utilizado por otro proceso»),
   o el panel sigue mostrando la base vieja.
2. Elegir el respaldo y comprobar la huella. Las dos líneas que se imprimen deben ser **iguales**:
   ```powershell
   $r = "C:\Users\User\respaldos-sicop"
   $n = (Get-ChildItem $r -Filter *.db | Sort-Object LastWriteTime | Select-Object -Last 1).BaseName
   (Get-FileHash "$r\$n.db" -Algorithm SHA256).Hash.ToLower()
   (Get-Content "$r\$n.json" -Raw | ConvertFrom-Json).sha256
   ```
3. Guardar aparte la base dañada (no borrarla) y poner la del respaldo:
   ```powershell
   Rename-Item .\data\sicop.db sicop-antes-de-restaurar.db
   Copy-Item "$r\$n.db" .\data\sicop.db
   ```
4. **Comprobar que se restauró:** `Get-ChildItem .\data\*.db` debe mostrar **dos** archivos,
   `sicop-antes-de-restaurar.db` y `sicop.db`, y `sicop.db` con la hora del respaldo. Si solo hay uno, el paso 3 no
   se hizo: repetirlo. (Que una revisión conocida aparezca no basta: si no cambió nada desde el respaldo, la base
   vieja también la tiene.)
5. `python -m app.cli migrate`: con una base ya al día dice «La base ya está al día; no se aplicó nada».
6. Abrir el panel y una revisión conocida.

Para **ensayar** sin tocar la base real: copiar el respaldo a otra carpeta y, en la misma ventana de PowerShell,
`$env:DATABASE_PATH = "CARPETA\sicop.db"` antes de `migrate` (la variable gana sobre `.env`; se pierde al cerrar
la ventana). Borrar la copia al terminar: tiene los usuarios.

Lo hecho después del respaldo se pierde: cargar otra vez los archivos de SICOP de esos días y correr
`evaluate`. Las revisiones de esos días hay que volver a anotarlas.

### 6.3 Otros casos

- **Un ciclo se cortó a la mitad:** el bloqueo se suelta solo y el siguiente ciclo marca el anterior como
  fallo. Los avisos que quedaron «incierto» se revisan a mano (4.4).
- **Volver a una versión anterior del código:** `DESPLIEGUE.md`, 9.8. No revierte migraciones: si el esquema
  cambió, también se restaura la base.

## 7. Simulacros (3, 4 y 5 hechos en Windows; ninguno en el servidor)

La guía pide practicar la recuperación cuando no hay emergencia y anotar el resultado aquí:

| # | Simulacro | Resultado esperado | Fecha y resultado |
|---|---|---|---|
| 1 | Reiniciar el servicio | El panel vuelve y una decisión guardada sigue ahí. | — |
| 2 | Reiniciar el servidor (en una ventana acordada) | El panel arranca solo y el timer sigue programado. | — |
| 3 | Restaurar un respaldo en otra carpeta | Se lee una revisión conocida. | Windows, 2026-10-13 y 2026-10-19 (`sicop_20261019-114809`: huella igual al manifiesto, `migrate` al día, revisiones #1–#5 presentes); 2026-10-23 en la instalación limpia (`sicop_20261023-111021`: huella igual, base restaurada con la hora del respaldo, `migrate` al día, la revisión de `20261002859` presente). Falta en el servidor. |
| 4 | Ciclo con fuente fallida | Queda error o cobertura desactualizada, nunca «cero compras». | Windows, 2026-10-19: ciclo #22 sin archivos → «FALLO · no llegó ningún archivo nuevo… (no significa que no haya compras)», código 1, no avisó. Falta en el servidor. |
| 5 | Repetir el ciclo | No se duplican avisos. | Windows, dry-run, 2026-10-22: el ciclo #28 importó datos nuevos y actualizó 9 evaluaciones con los mismos destinatarios: 0 avisos nuevos; los 6 ya preparados el 21/10 (ciclo #25) no se repitieron. En la base (consulta de solo lectura, 26/10): 24 avisos en la outbox, 24 claves de deduplicación distintas. Archivo repetido: «YA IMPORTADO», sin duplicar (ciclo #16 y en la instalación limpia del 23/10). Falta en el servidor y con envío real. |
