\# SICOP CONNECT — instrucciones para Claude Code

App de Hermatix: importar datos abiertos de SICOP, detectar oportunidades

comerciales con reglas explicables, revisión humana y aviso por correo.

Guía completa: SICOP\_CONNECT\_RETO\_4\_SEMANAS.md (leer SOLO la sección indicada).

Estado y siguiente tarea: docs/ESTADO\_PROYECTO.md.

\## Stack

Python 3.12+ · FastAPI · Jinja2 + HTML/CSS · SQLite · pytest. Sin API de IA.

Desarrollo en Windows (PowerShell); producción Linux + systemd.

\## Forma de trabajo

\- Implementa solo la tarea pedida. No adelantes fases ni agregues dependencias sin justificar.

\- Al terminar, ejecuta las pruebas relevantes y muestra la salida real.

\- Responde con un resumen de máx. 8 líneas: archivos, pruebas, pendientes.

&#x20;No reimprimas el código completo.

\- La usuaria está aprendiendo: explica cada concepto nuevo con un ejemplo de 2–3 líneas.

\## Reglas de datos

\- Identificadores SICOP SIEMPRE como texto (8/16/24 dígitos, ceros iniciales).

\- Dinero en Decimal con su moneda; nunca sumar monedas distintas.

\- Importaciones y avisos idempotentes (hash / clave de deduplicación).

\- Nunca borrar revisiones humanas al actualizar datos.

\- Distinguir siempre datos reales, sintéticos y simulados.

\## Prohibido

\- Inventar APIs, campos o resultados de SICOP.

\- Leer .env, secretos o documentos personales (usar .env.example).

\- Enviar correos reales, activar tareas programadas o tocar el servidor sin instrucción

explícita.



