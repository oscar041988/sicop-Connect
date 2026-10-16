# Operación de SICOP CONNECT — borrador

Cómo se usa la app en el día a día: importar, revisar, enviar avisos, diagnosticar y recuperar (entregable E6
de la guía). La instalación, la actualización y la reversión están en `docs/DESPLIEGUE.md`.

Estado: **borrador** (2026-10-16). Falta probarlo literalmente, paso por paso, y anotar los resultados de los
simulacros (sección 7).

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

### 1.2 Cargar los archivos

Tres formas; las tres usan el mismo importador:

- **Panel → «Cargar archivo»:** elegir el tipo de reporte, el origen (real, sintético o simulado) y el archivo.
  Los carteles y las líneas van en `.csv`; el catálogo, en `.csv` o `.zip`.
- **Carpeta de entrada:** dejar los archivos en `INCOMING_DIR` (en el servidor, `/var/lib/sicop-connect/incoming`)
  **antes de las 8:00**; el ciclo los importa solo (sección 3).
- **Terminal:** `python -m app.cli import --path ARCHIVO --report carteles --origen real`.

Reglas:

- **Orden:** instituciones → carteles → catálogo → líneas. Una línea cuyo cartel no se importó queda guardada,
  pero no entra a las líneas hasta importar un archivo de líneas nuevo después del cartel.
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

El ciclo diario evalúa solo. Si el panel dice «Todavía no hay evaluaciones» o «Las reglas cambiaron», hay que
correr `evaluate`. Cómo leer su salida y cómo cambiar una regla: `docs/REGLAS.md`.

## 2. Revisar

1. **Panel de carteles:** la lista de oportunidades, con búsqueda y filtros por prioridad, plazo, familia,
   institución, tipo de procedimiento y si ya se revisó.
2. Abrir un cartel: muestra la evidencia (las frases que coincidieron), el comprador, las líneas y el plazo.
3. Guardar la decisión: «Interesa», «No interesa» o «Revisar requisitos»; si no interesa, con el motivo, y un
   comentario. Queda a nombre del usuario que inició sesión.
   Si se anota la decisión de otra persona, se escribe en el comentario.

- La prioridad dice **encaje con el portafolio de Hermatix**, no si Hermatix puede participar o ganar.
- Un cartel que cierra el fin de semana se trata igual que cualquier otro (decisión de Ivania, 2026-10-16).

## 3. El ciclo diario

`run-cycle` hace todo en orden: **recoger** `INCOMING_DIR` → **importar** → **evaluar** → **avisar**.

```
python -m app.cli run-cycle --origen real --dry-run    # avisos solo en vista previa (por defecto)
python -m app.cli run-cycle --origen real --send       # envío real
```

- En el servidor lo corre el temporizador `sicop-cycle.timer`, **de lunes a viernes a las 8:00** (hora de Costa
  Rica). Hoy está en dry-run; el envío real se activa siguiendo `DESPLIEGUE.md`, 9.6, con autorización de Oscar.
- Los archivos importados pasan a `INCOMING_DIR/procesados/<fecha>/`. Uno incompleto, ilegible o no reconocido
  **no se importa**: pasa a `INCOMING_DIR/con_error/<fecha>/` y el ciclo termina en «fallo».
- Si no llegó ningún archivo nuevo o la fuente falló, se evalúa igual (los plazos cambian con el día), pero
  **no se avisa**: un correo sin los datos del día daría a entender que no hubo compras.
- Resultado: `0` = ok · `1` = fallo (queda registrado) · `2` = ya había otro ciclo en curso.
- Efecto conocido: un cartel cargado el viernes después de las 8:00 que cierra el sábado o el domingo no se
  avisa por correo (el lunes ya venció). Sí aparece en el panel.

## 4. Enviar avisos

### 4.1 Qué se avisa

Carteles con prioridad **Alta** o **Media**, con el plazo no vencido, vistos por primera vez en los últimos
`NOTIFY_LOOKBACK_DAYS` días. A cada destinatario le llega **un correo resumen**. Se vuelve a avisar solo si el
cartel cambió (otra versión u otra fecha de cierre). Los destinatarios se editan en el panel → «Destinatarios»
(solo administradores).

### 4.2 Comandos

```
python -m app.cli notify --dry-run                     # prepara y escribe la vista previa en EXPORTS_DIR
python -m app.cli notify --send                        # envío real por Gmail
python -m app.cli notify --send --solo CORREO          # solo a un destinatario activo (prueba controlada)
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

> Página en la rama `reintento-avisos`, todavía sin unir a `main` (2026-10-16).

Panel → «Avisos» (solo administradores):

- **Fallido:** «Reintentar» lo vuelve a «preparado» y sale en el siguiente envío. Si Gmail lo rechazó por la
  dirección, conviene corregirla antes en «Destinatarios».
- **Incierto:** primero buscarlo en Gmail › Enviados de la cuenta que envía los avisos.
  - Está en Enviados → «Sí salió»: queda «aceptado» y no se reenvía.
  - No está → marcar «Revisé Gmail › Enviados y no está» y «Reintentar».
- No deja reintentar si el cartel ya cerró, si el destinatario fue quitado o si ya le llegó una versión más
  nueva del cartel. Cada decisión queda en el historial de la página.

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
| «Las reglas cambiaron…» | Se editó el YAML después de la última evaluación. | `evaluate`. |
| «Faltan migraciones… ejecuta migrate» | El código es más nuevo que la base. | `migrate`. |
| «Este archivo ya se importó» | Mismo archivo (mismo hash). | Nada: no se duplicó. |
| Ciclo «fallo · no llegó ningún archivo nuevo» | `INCOMING_DIR` vacío. | Cargar los archivos del día. |
| Ciclo «fallo» con un archivo en `con_error/` | Archivo incompleto, ilegible o no reconocido. | Descargarlo otra vez de SICOP. |
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

- 🪟 Windows: `C:\Users\User\respaldos-sicop\`, fuera de Git. Último: `sicop_20261016-115938`.
- 🐧 Servidor: destino, retención y respaldo diario automático, **pendientes con Oscar**.

### 6.2 Si se daña la base

Restaurar el último respaldo (`DESPLIEGUE.md`, 9.7):

1. Detener el timer y el panel.
2. Comprobar el SHA-256 del `.db` contra el manifiesto.
3. Copiar el `.db` como `DATABASE_PATH` (en el servidor: propietario `sicop`, permisos `600`).
4. Arrancar `sicop-migrate.service` y luego `sicop-web.service`.
5. Abrir una revisión conocida para confirmar.

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
| 3 | Restaurar un respaldo en otra carpeta | Se lee una revisión conocida. | Ensayado en Windows el 2026-10-13 (`DESPLIEGUE.md`, 9.7); falta en el servidor. |
| 4 | Ciclo con fuente fallida | Queda error o cobertura desactualizada, nunca «cero compras». | — |
| 5 | Repetir el ciclo | No se duplican avisos. | — |
