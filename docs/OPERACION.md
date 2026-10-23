# Operación de SICOP CONNECT — borrador

Cómo se usa la app en el día a día: importar, revisar, enviar avisos, diagnosticar y recuperar (entregable E6
de la guía). La instalación, la actualización y la reversión están en `docs/DESPLIEGUE.md`.

Estado: **borrador** (2026-10-16). Secciones 1 a 6 probadas paso por paso en Windows con datos reales
(2026-10-19, Ivania con Claude) y corregidas con lo encontrado. Revisado contra el código de `desarrollo` el
2026-10-23 (ZIP sin descomprimir, adjudicaciones, A4, A5, aviso de datos sin evaluar). Falta probar en el
servidor las partes 🐧 y terminar los simulacros (sección 7).

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

### 1.2 Cargar los archivos

Tres formas; las tres usan el mismo importador:

- **Panel → «Cargar archivo»:** elegir el tipo de reporte, el origen (real, sintético o simulado) y el archivo.
  «pliegos» es el ZIP del portal (carteles y líneas juntos); carteles, líneas e instituciones van en `.csv`; el
  catálogo, en `.csv` o `.zip`.
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

**Cargar un archivo no lo evalúa.** El panel solo muestra los carteles evaluados con las reglas
(`config/hermatix_rules.yaml`). Después de cargar a mano:

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
- Un cartel que cierra el fin de semana se trata igual que cualquier otro (decisión de Ivania, 2026-10-16).
- **Exportar a Excel:** el botón del panel de carteles baja el listado con los mismos filtros (todas las
  páginas). Los números SICOP quedan como texto: no se dañan al abrirlos.
- **Competencia:** quién gana qué por familia, con montos por moneda, a partir de las adjudicaciones importadas.
  Los ganadores vienen solo con cédula; el nombre se pone en `config/competidores.yaml`.

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
  archivos se cargaron desde el panel (el ciclo solo mira `INCOMING_DIR`) y si solo llegaron adjudicaciones
  (se importan, pero no traen carteles nuevos). La excepción son los avisos de **cierre próximo** (4.1): el
  plazo corre igual, así que salen aunque falten los datos del día.
- **Los lunes** el ciclo arma además el resumen semanal (4.1), con el mismo modo (dry-run o envío).
- Resultado: `0` = ok · `1` = fallo (queda registrado) · `2` = ya había otro ciclo en curso. En PowerShell, el
  código del último comando se ve con `$LASTEXITCODE`.
- **En el servidor, mientras la descarga sea manual:** cada día hábil que nadie deje los archivos en
  `INCOMING_DIR` antes de las 8:00, el ciclo sale en «fallo» y systemd marca `sicop-cycle.service` como fallido.
  Ese «fallo» significa **«nadie cargó los datos de hoy»**, no que la app esté rota. Se resuelve cargando los
  archivos (sección 1); no hace falta tocar el servidor.
- Efecto conocido: un cartel cargado el viernes después de las 8:00 que cierra el sábado o el domingo no se
  avisa por correo (el lunes ya venció). Sí aparece en el panel.

### 3.1 Obtención automática (`obtain auto`, lección 4)

**Estado (2026-10-22): construida y probada con datos SIMULADOS; no activada.** En la única prueba real, SICOP
rechazó la descarga hecha por el programa (`DECISION_OBTENCION.md` §8): mientras eso no se resuelva con soporte de
SICOP, la descarga cae en el plan B de abajo. No se llama «automática» hasta que un ciclo real lo demuestre.

`python -m app.cli obtain auto` es **una vuelta**; la tarea «SICOP CONNECT - obtencion» la repite cada 15 min, de
07:00 a 20:00, de lunes a viernes (`deploy/windows/README.md`). Cada vuelta:

1. Con `SOURCE_MODE=manual` no hace nada (no abre SICOP ni lee Gmail).
2. Desde `OBTAIN_REQUEST_HOUR` (07:00), si hoy no hay solicitud, pide el reporte. **Una por día:** si la de hoy
   falló, no se pide otra sola.
3. Si hay una solicitud abierta, revisa el buzón: enlace → descarga → validación → el ZIP queda en `INCOMING_DIR`.
4. Si una solicitud falló, manda **una** alerta a `OBTAIN_ALERT_TO` con el motivo y el plan B. Mientras los avisos
   estén en dry-run (`NOTIFICATIONS_DRY_RUN=true`), la alerta es solo un archivo:
   `EXPORTS_DIR\alerta-obtencion-<n>.txt`. La alerta nunca lleva el enlace ni el código.
5. Si hay un archivo listo en `INCOMING_DIR` (el de la descarga automática o uno dejado a mano), corre el ciclo
   **en dry-run**. En `source_runs` queda con modo `auto`. Un archivo recién copiado espera a la vuelta siguiente.

**Activar:** en `.env`, `SOURCE_MODE=auto`, `OBTAIN_ALERT_TO=` (el buzón de la alerta) y `migrate`; luego crear la
tarea y pausar la de las 8:00 (`deploy/windows/README.md`). **Volver a manual:** `SOURCE_MODE=manual`. No hay que
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
guardar el ZIP y dejarlo en `INCOMING_DIR` sin abrirlo en Excel. La vuelta siguiente (≤ 15 min) lo importa,
evalúa y prepara los avisos.

**Renovar el acceso a Gmail (lectura):** `python -m app.cli obtain gmail-auth`, entrando con el buzón de
`SICOP_REQUEST_EMAIL`. Después, `python -m app.cli obtain check-mail` para comprobar. El permiso de enviar avisos
es otro (`google-auth`, sección 4).

**Dónde mirar:**
- `python -m app.cli obtain status`: las últimas solicitudes, con la hora de cada paso, el motivo y la alerta.
- `data\logs\obtencion-AAAA-MM.log`: la salida de cada vuelta de la tarea.
- `EXPORTS_DIR`: capturas de los fallos de la solicitud (`obtencion-fallo-…png`) y las alertas en vista previa.
- `RAW_DATA_DIR\descargas`: los ZIP descargados tal como llegaron y la captura de un fallo de descarga.

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

  ```powershell
  $n = "sicop_AAAAMMDD-HHMMSS"   # el nombre que imprimió backup
  Compress-Archive -Path "C:\Users\User\respaldos-sicop\$n.db", "C:\Users\User\respaldos-sicop\$n.json" `
    -DestinationPath "C:\Users\User\respaldos-sicop\$n.zip"
  ```

  Para restaurarlo, se descomprime y se sigue 6.2 (primero se compara la huella).
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

🪟 **Windows** (probado el 2026-10-19 en una carpeta aparte):

1. Cerrar el panel (Ctrl+C en la ventana de `uvicorn`).
2. Comprobar la huella: `(Get-FileHash ARCHIVO.db -Algorithm SHA256).Hash.ToLower()` debe ser igual al `sha256`
   del `.json`.
3. Guardar aparte la base dañada (no borrarla) y copiar el `.db` del respaldo como `data\sicop.db`.
4. `.venv\Scripts\python -m app.cli migrate`.
5. Abrir el panel y una revisión conocida.

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

## 7. Simulacros (pendiente)

La guía pide practicar la recuperación cuando no hay emergencia y anotar el resultado aquí:

| # | Simulacro | Resultado esperado | Fecha y resultado |
|---|---|---|---|
| 1 | Reiniciar el servicio | El panel vuelve y una decisión guardada sigue ahí. | — |
| 2 | Reiniciar el servidor (en una ventana acordada) | El panel arranca solo y el timer sigue programado. | — |
| 3 | Restaurar un respaldo en otra carpeta | Se lee una revisión conocida. | Windows, 2026-10-13 y 2026-10-19 (`sicop_20261019-114809`: huella igual al manifiesto, `migrate` al día, revisiones #1–#5 presentes). Falta en el servidor. |
| 4 | Ciclo con fuente fallida | Queda error o cobertura desactualizada, nunca «cero compras». | Windows, 2026-10-19: ciclo #22 sin archivos → «FALLO · no llegó ningún archivo nuevo… (no significa que no haya compras)», código 1, no avisó. Falta en el servidor. |
| 5 | Repetir el ciclo | No se duplican avisos. | — |
