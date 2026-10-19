# Acta de despliegue de SICOP CONNECT — borrador

Primera instalación en el servidor (lección 9, guía 17.2 paso 6). Pasos de referencia: `docs/DESPLIEGUE.md`,
sección 9.

Solo se anota lo que Ivania u Oscar confirmaron. Lo que nadie recuerda queda **«sin registro»**, sin suponer.
Aquí **nunca** van contraseñas, llaves, `SESSION_SECRET`, el contenido de `app.env` ni los JSON de Google.

## Datos de la instalación

| Dato | Valor | Fuente |
|---|---|---|
| Fecha y hora | jueves 15/10/2026, desde las 15:00 aprox. | Ivania (2026-10-19) |
| Presentes | Ivania y Oscar | Ivania |
| Servidor | VPS Ubuntu 24.04 en Hostinger (`DESPLIEGUE.md`, sección 1) | `DESPLIEGUE.md` |
| Servidor compartido | sí: junto con Nexus y otras apps web de la empresa | Ivania (2026-10-19) |
| Dirección del panel | https://sicop.hermatix.com | `ESTADO_PROYECTO.md` |
| Cómo se instaló | **Oscar no ejecutó comandos a mano:** usó un asistente de programación con IA (parecido a Claude Code), le dio las direcciones y la guía, y el asistente hizo la instalación y lo relacionado con GitHub. Qué comandos corrió y en qué orden: ☐ sin registro; la fuente es el historial de esa sesión del asistente. (El 19/10 Ivania había dicho «paquete `git archive` desde la Mac»; lo corrigió el mismo día.) | Ivania (2026-10-19) |
| Sentido de GitHub | **del servidor a GitHub**: el código ya estaba en el servidor y el asistente lo subió a GitHub (la historia nueva del 16/10, con fin de línea CRLF). Es al revés de lo planeado (GitHub → Mac → servidor). Cómo llegó el código al servidor: ☐ sin registro | Ivania (2026-10-19) |
| Secretos en GitHub | revisado el 19/10 (`main`, `diseno-fenova` y toda la historia): **ningún archivo secreto** (`.env`, `app.env`, base, JSON de Google, llaves) ni secretos dentro de archivos; solo valores de prueba inventados | Claude (2026-10-19) |
| Commit instalado | ☐ sin registro: Oscar lo lee con `cat /opt/sicop-connect/app/COMMIT` | — |
| Hash del paquete (SHA-256) | ☐ sin registro: no se recuerda si se comparó en la Mac y en el servidor | Ivania |
| Versión de Python | ☐ sin registro (se necesita 3.12 o más; Oscar dijo que la cumple) | — |
| Base inicial | **no parece ser el respaldo de Windows**: el 19/10 el panel dice «Todavía no hay evaluaciones», y ese mensaje solo sale si la tabla de evaluaciones está vacía (la base de Windows tiene evaluaciones desde la lección 4). Los usuarios sí existen. ☐ Oscar confirma. Para comparar: la base de Windows tiene 4 usuarios, 5 revisiones, 11 215 carteles y 12 avisos en la outbox, y su huella es `f32a31689f3e…` en los respaldos del 13/10, del 16/10 (11:59) y del 19/10 (no cambió desde el 13/10). Si la base del servidor es una copia de esta, `sha256sum` da esa misma huella, hasta que alguien la use. **El respaldo del 16/10 (11:59) se lo pasó Ivania a Oscar, un día después de la instalación (15/10)**: lo probable es que el servidor arrancara con una base nueva y que el respaldo no se colocara, o quedara en otra carpeta. ☐ Oscar busca dónde quedó | Ivania y Claude (2026-10-19) |
| HTTPS | lo configuró Oscar con las herramientas de Hostinger | Ivania |

## Pasos (`DESPLIEGUE.md`, sección 9)

| Paso | Máquina | Responsable | Resultado |
|---|---|---|---|
| 9.1 Publicar el commit revisado | Windows | Ivania | ☐ sin registro: el código salió del repositorio de Oscar |
| 9.2 Empaquetar con `git archive` y copiar | Mac | asistente de IA de Oscar | ☐ sin registro: no se sabe si se usó `git archive` |
| 9.3 Verificar el hash, usuario `sicop`, carpetas, instalar | Servidor | asistente de IA de Oscar | ☐ sin registro |
| 9.4 Configuración privada (`app.env`, sin envíos) | Servidor | asistente de IA de Oscar | ☐ sin registro |
| 9.5 Servicios, migración, `sicop-web` | Servidor | asistente de IA de Oscar | la app funciona (ver abajo); ☐ falta confirmar que es el servicio |
| Proxy con HTTPS | Hostinger | Oscar | hecho: el panel abre con HTTPS (Ivania, 2026-10-16) |
| 9.6 Activar el ciclo diario | Servidor | — | **no se hizo**, como estaba previsto (lección 10) |

## Comprobación de la guía (lección 9)

- ☐ El hash del paquete coincide en la Mac y en el servidor: sin registro.
- ☐ `curl -f http://127.0.0.1:8000/health` responde en el servidor: no se corrió (Ivania cree que no).
- ☑ El panel abre en la dirección real con HTTPS (Ivania, 2026-10-16) y pide inicio de sesión: Ivania entró
  desde su celular (2026-10-19).
- ☐ Una oportunidad real revisada desde otra computadora: **no se pudo**, el panel no tiene carteles evaluados
  (2026-10-19). Falta decidir la base (ver pendientes).
- ☐ Esta acta completa.

## Comandos para completar los ☐ (Oscar, en el servidor)

Ninguno muestra secretos. Se pega aquí solo el resultado que no tenga datos privados.

```bash
cat /opt/sicop-connect/app/COMMIT          # commit instalado
systemctl status sicop-web --no-pager      # ¿«active (running)»? ¿«User=sicop»?
systemctl is-enabled sicop-cycle.timer     # debe decir «disabled» hasta la lección 10
curl -f http://127.0.0.1:8000/health       # comprobación de salud
python3 --version
sudo ss -ltnp | grep ':8000 '              # ¿el puerto 8000 es de SICOP (python) y no de otra app?
```

**Servidor compartido.** Como en el mismo servidor corren Nexus y otras apps, hay que comprobar que el puerto 8000
lo usa SICOP y no otra app: si `curl …/health` contesta algo que no es la respuesta de SICOP, el puerto está
ocupado por otra app. El usuario `sicop` y los permisos `700`/`600` de sus carpetas evitan que las otras apps lean
la base o `app.env`, y que SICOP toque las suyas.

El hash del paquete ya no se puede comparar si se borró `/tmp/sicop-connect-release.tar.gz`. En ese caso se anota
«no se comparó» y, en la próxima actualización (9.8), se compara sin falta.

## Pendientes

| Pendiente | Responsable |
|---|---|
| Completar los ☐ de esta acta con los comandos de arriba | Oscar, con Ivania |
| Pedir el historial de la sesión del asistente de IA que hizo la instalación (sin contraseñas ni llaves) para reconstruir los pasos | Oscar |
| Como se subió a GitHub desde el servidor: en qué carpeta está ese repositorio y con qué permiso entra el servidor a GitHub (llave o token, y de qué cuenta). Un permiso para escribir en GitHub guardado en un servidor compartido es un riesgo: si no se va a usar, quitarlo | Oscar |
| Base del servidor sin evaluaciones: restaurar el respaldo de Windows (lo acordado el 13/10) o importar archivos reales en el servidor y evaluar | Oscar con Ivania |
| Revisar una oportunidad real desde otra computadora y anotarla | Ivania |
| Confirmar que el proxy de Hostinger pasa la IP real del visitante (límite de intentos de login) | Oscar |
| Confirmar que el puerto 8000 es solo de SICOP (servidor compartido) | Oscar |
| Que los respaldos del servidor incluyan `/var/lib/sicop-connect/sicop.db` (con `app.cli backup`, no copiando el archivo) | Oscar |
| Pasar al servidor los dos JSON de Google (`DESPLIEGUE.md`, 9.4) | Oscar |
| Respaldos en el servidor: destino, retención, diario | Oscar (2026-10-19) |
| Repositorio de GitHub a privado | Oscar (2026-10-19) |
| Activar el ciclo diario, primero en dry-run | lección 10, aprobado por Oscar (2026-10-19) |
