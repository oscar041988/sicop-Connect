# Lección 10 · Hito 2 — hoja de la sesión con Oscar y acta

Preparada el 2026-10-20 (Ivania con Claude), a partir de la guía 17.5 y de `docs/DESPLIEGUE.md` 9.6.
Se ejecuta **solo con Oscar presente**. Claude no se conecta al servidor.

- Ya hecho antes de la sesión (2026-10-20): los JSON de Google están en el servidor y `notify --send` desde el
  servidor entregó el correo. ☑ Correo real recibido desde el servidor.
- Ya hecho antes de la sesión (2026-10-21): ☑ **destinatarios confirmados por Oscar**: `aumana@`, `calvarez@` y
  `priaraya@`, los tres que estaban activos. Sin cambios en la lista.
- 🍎 MAC = la terminal de la Mac antes de `ssh` · 🐧 SERVIDOR = la terminal después de `ssh`.
  **Antes de cada comando, decir en voz alta en qué máquina se está.**
- En el acta se anotan el resultado y lo que cambió. **Nunca** se anotan contraseñas, llaves, `SESSION_SECRET`
  ni el contenido de los JSON.
- Los comandos de la CLI en el servidor siempre usan el patrón de `systemd-run` (9.5), que aquí se escribe
  `CLI …`:
  ```bash
  sudo systemd-run --uid=sicop --pty --wait \
    -p EnvironmentFile=/etc/sicop-connect/app.env \
    -p WorkingDirectory=/opt/sicop-connect \
    /opt/sicop-connect/.venv/bin/python -m app.cli doctor     # «doctor» se cambia por el comando
  ```

Fecha de la sesión: ______ · Presentes: ______ · Hora de inicio: ______

---

## Paso 0 · 🐧 SERVIDOR — ¿dónde estamos? (5 min)

```bash
hostname && whoami
cat /opt/sicop-connect/app/COMMIT                 # qué versión del código hay instalada
timedatectl                                       # zona horaria (el timer no depende de ella, pero se anota)
ls -l /etc/systemd/system/sicop-*                 # deben estar las 4 unidades
systemctl status sicop-web.service --no-pager     # «active (running)»
systemctl is-enabled sicop-cycle.timer            # todavía debe decir «disabled»
grep ExecStart /etc/systemd/system/sicop-cycle.service   # todavía debe terminar en --dry-run
CLI doctor
```

| Dato | Resultado |
|---|---|
| Commit instalado | |
| Zona horaria del servidor | |
| `sicop-web` | |
| Timer (esperado: `disabled`) | |
| `ExecStart` (esperado: `--dry-run`) | |
| `doctor`: pendientes que muestra | |

Si el timer ya estuviera habilitado o el `ExecStart` ya dijera `--send`: **parar** y anotar quién lo cambió y
cuándo antes de seguir.

---

## Paso 1 · 🐧 SERVIDOR — ciclo en dry-run, a mano (guía 17.5, punto 1)

**Para que el ciclo tenga algo que procesar** hace falta un archivo nuevo de SICOP en `INCOMING_DIR`. Subirlo
desde el panel **no sirve** para esta prueba: el panel lo importa enseguida y el ciclo ya no lo ve como nuevo.

**¿ZIP o CSV?** Depende de la versión instalada (commit del paso 0). Desde la rama `zip-pliegos` (`41cf4db`), el
ciclo acepta el ZIP de «Detalle pliego de condiciones» tal como llega; antes, solo los dos CSV.

1. Descargar hoy de SICOP el ZIP de «Detalle pliego de condiciones», **sin abrir los CSV en Excel**.
2. Elegir el camino y anotarlo en la tabla:

   **A · El servidor ya tiene `zip-pliegos`:** se copia el ZIP tal cual.
   - 🍎 MAC: `scp "ARCHIVO.zip" USUARIO_SSH@HOST_SERVIDOR:/tmp/`
   - 🐧 SERVIDOR:
     ```bash
     sudo install -o sicop -g sicop -m 640 "/tmp/ARCHIVO.zip" /var/lib/sicop-connect/incoming/
     rm "/tmp/ARCHIVO.zip"
     ```

   **B · El servidor todavía no tiene `zip-pliegos`:** se descomprime y van los dos CSV,
   `Detalle de pliegos de condiciones.csv` y `Detalles lineas.csv`. No importa el orden: el ciclo reconoce cada
   reporte por su encabezado e importa los carteles antes que las líneas.
   - 🍎 MAC: `scp "Detalle de pliegos de condiciones.csv" "Detalles lineas.csv" USUARIO_SSH@HOST_SERVIDOR:/tmp/`
   - 🐧 SERVIDOR:
     ```bash
     sudo install -o sicop -g sicop -m 640 "/tmp/Detalle de pliegos de condiciones.csv" "/tmp/Detalles lineas.csv" \
          /var/lib/sicop-connect/incoming/
     rm "/tmp/Detalle de pliegos de condiciones.csv" "/tmp/Detalles lineas.csv"
     ```
3. **Esperar al menos 60 segundos** después de colocarlos (si no, quedan «EN ESPERA»).
4. Correr el ciclo y leer su salida:
   ```bash
   sudo systemctl start sicop-cycle.service
   systemctl show sicop-cycle.service -p ExecMainStatus     # 0 = ok · 1 = fallo · 2 = otro ciclo en curso
   sudo journalctl -u sicop-cycle.service -n 50 --no-pager
   ls -lt /var/lib/sicop-connect/exports | head             # carpeta avisos_<fecha> con la vista previa
   ```
   `inactive` al terminar es normal (es un servicio *oneshot*): lo que importa es el código de salida.

Qué debe decir el registro:
- `Ciclo #N · DRY-RUN · no se envía nada · origen de los datos: real`
- `IMPORTADO (carteles) …` y `IMPORTADO (lineas) …`, con aceptadas y rechazadas, y la línea `Cobertura: …`.
  Con el camino A llevan el nombre del ZIP delante (`ARCHIVO.zip › Detalle de pliegos de condiciones.csv`) y
  el ZIP pasa entero a `incoming/procesados/<fecha>/`.
- `Evaluación: …` y `Preparados esperando envío: …` (o «Nada que avisar»)
- `Ciclo #N: OK.`

| Dato | Resultado |
|---|---|
| Camino usado (A: ZIP · B: CSV) | |
| Archivo y hora en que se colocó | |
| Ciclo # y código de salida | |
| Importación # · aceptadas · rechazadas | |
| Cobertura (fechas de publicación) | |
| Avisos preparados (cuántos, para quién) | |
| Vista previa revisada (sí/no, quién) | |

☐ Ciclo en dry-run OK, sin envíos.

---

## Paso 2 · 🐧 SERVIDOR — pasar a envío real (guía 17.5, puntos 2–5)

**Solo con autorización de Oscar en ese momento.** Autorizó: ______ Hora: ______

1. `app.env`: la prueba con `notify --send` ya funcionó, así que deberían estar `NOTIFICATIONS_ENABLED=true`,
   `NOTIFICATIONS_DRY_RUN=false`, `MAIL_PROVIDER=gmail_api` y `MAIL_FROM`. El administrador lo confirma y pone
   `SCHEDULER_ENABLED=true` (es solo informativo: lo muestra `doctor`; lo que de verdad programa es el timer).
   `CLI doctor` → anotar que no muestra pendientes de correo.
2. Cambiar el ciclo a envío real (lo hace el administrador):
   ```bash
   sudo nano /etc/systemd/system/sicop-cycle.service       # en ExecStart: --dry-run → --send
   grep ExecStart /etc/systemd/system/sicop-cycle.service  # comprobar
   sudo systemctl daemon-reload
   ```
3. Ciclo supervisado:
   ```bash
   sudo systemctl start sicop-cycle.service
   systemctl show sicop-cycle.service -p ExecMainStatus
   sudo journalctl -u sicop-cycle.service -n 50 --no-pager
   ```
   Debe decir `ENVÍO REAL` y, por destinatario, `ACEPTADO`. Si dice `INCIERTO` o `FALLIDO`: **no repetir**;
   revisar Gmail › Enviados y anotar el detalle.
4. **Verificar en la bandeja** de cada destinatario (aceptado ≠ recibido): llegó, «Hola, equipo», no está en
   «no deseado» y el enlace abre el panel real (no `127.0.0.1`).

Ojo: si el paso 1 ya preparó esos avisos y nada cambió, este ciclo puede decir «Nada que avisar». Eso es correcto
(la deduplicación funciona) y no se fuerza un correo. El correo real ya quedó demostrado con `notify --send`.

| Dato | Resultado |
|---|---|
| Ciclo # y código de salida | |
| Estado por destinatario | |
| Recibido en la bandeja (quién lo confirmó) | |
| Enlace del correo abre el panel real | |

☐ Ciclo real supervisado OK.

---

## Paso 3 · 🐧 SERVIDOR — habilitar el horario (guía 17.5, punto 6)

```bash
sudo systemctl enable --now sicop-cycle.timer
systemctl list-timers sicop-cycle.timer --no-pager
```

`NEXT` debe ser el próximo día de lunes a viernes a las **08:00 de Costa Rica**. Si el servidor está en UTC, se
verá como 14:00 UTC (Costa Rica = UTC−6, sin horario de verano).

| Dato | Resultado |
|---|---|
| `NEXT` que muestra | |
| ¿Corresponde a lun–vie 08:00 CR? | |

☐ Timer activo con próxima ejecución verificada.

**Desde aquí, cada día hábil alguien debe dejar el archivo de SICOP en `incoming/` antes de las 8:00.**
Responsable: ______ (si nadie lo deja, el ciclo queda en «fallo · no llegó ningún archivo nuevo» y no avisa).

---

## Paso 4 · 🐧 SERVIDOR — reinicio sin pérdida de datos (guía, lección 10, paso 3)

1. Antes: abrir en el panel una revisión conocida y anotarla (Número SICOP, decisión, quién).
2. Reiniciar:
   ```bash
   sudo systemctl restart sicop-web.service
   systemctl status sicop-web.service --no-pager
   curl -f http://127.0.0.1:8000/health
   ```
3. Después: volver a entrar al panel (por HTTPS, desde otra computadora) y abrir la misma revisión.
4. Opcional, solo si Oscar lo autoriza: reiniciar el servidor entero (`sudo reboot`) y comprobar que
   `sicop-web` arranca solo y que `list-timers` sigue mostrando el próximo ciclo.

| Dato | Resultado |
|---|---|
| Revisión de referencia | |
| `/health` después del reinicio | |
| La revisión sigue ahí (sí/no) | |
| Reinicio del servidor (hecho / no autorizado) | |

☐ Reinicio sin pérdida de datos.

---

## Cosas que se anotan para después

- El cambio a `--send` se hizo en la copia instalada (`/etc/systemd/system/`). En el repositorio sigue
  `--dry-run`. **Al actualizar (lección 15, 9.8) no copiar las unidades encima sin volver a poner `--send`**:
  el ciclo volvería a dry-run sin avisar a nadie.
- Lo que no salió como se esperaba:

## Cierre

- ☑ Panel protegido en el servidor con datos reales (lección 9).
- ☑ Correo real recibido desde el servidor (2026-10-20, `notify --send`).
- ☐ Timer activo con próxima ejecución verificada.
- ☐ Reinicio sin pérdida de datos.
- ☐ Reto de comprensión de la semana 2 (guía 20.3): mostrar por qué un segundo ciclo no reenvía el mismo aviso
  y localizar su registro en la outbox.
- Revisión semanal 2: Oscar elige las ampliaciones (`docs/AMPLIACIONES.md`). Decisión: ______

Hora de fin: ______ · Firmas / visto bueno: ______
