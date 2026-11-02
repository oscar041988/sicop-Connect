# Misiones de la ayuda

Ordenadas como se recorre la app: primero el panel, luego el cartel de arriba abajo, después seguimiento,
competencia y administración. Cada misión empieza en la página donde terminó la anterior.
Orden nuevo aprobado por Ivania el 2026-11-02 (reemplaza la lista del 2026-10-30); falta la aprobación de Oscar.
Cada misión está en `docs/ayuda/misiones/` con la plantilla de `PLANTILLA_MISION.md`.

## A. Panel de carteles

| # | Misión | Empieza en → termina en | Archivo | Estado |
|---|---|---|---|---|
| 1 | ¿Cómo entro a la app? | Iniciar sesión → Panel | `01-entrar.md` | Probada (2026-10-30) |
| 2 | ¿Cómo veo los carteles nuevos? | Panel → Panel | `02-carteles-nuevos.md` | Probada (2026-10-30); ampliada (2026-11-02), falta probarla otra vez |
| 3 | ¿Cómo busco y filtro carteles? | Panel → Cartel (arriba) | `03-buscar-y-filtrar.md` | Borrador (2026-11-02) |

## B. Página del cartel, de arriba abajo

| # | Misión | Empieza en → termina en | Archivo | Estado |
|---|---|---|---|---|
| 4 | ¿Cómo leo la parte de arriba de un cartel? | Cartel: prioridad, plazo, datos | `04-arriba-del-cartel.md` | Borrador (2026-11-02) |
| 5 | ¿Cómo leo y descargo el resumen con IA? | Cartel: «Resumen ejecutivo» | `05-resumen-ia.md` | Borrador (2026-11-02) |
| 6 | ¿Cómo veo la información de SICOP y los documentos? | Cartel: «Información de SICOP», «Documentos» | `06-documentos.md` | Borrador (2026-11-02) |
| 7 | ¿Por qué aparece el cartel y qué compran? | Cartel: «Por qué aparece», «Líneas», «Cobertura» | `07-por-que-aparece.md` | Borrador (2026-11-02) |
| 8 | ¿Cómo marco si un cartel interesa o no? | Cartel: «Revisión» (al final) | `08-revision.md` | Borrador (2026-11-02) |

## C. Seguimiento

| # | Misión | Empieza en → termina en | Archivo | Estado |
|---|---|---|---|---|
| 9 | ¿Cómo le doy seguimiento a un cartel? | Cartel (sube al inicio) → Seguimiento | `09-seguimiento.md` | Borrador (2026-11-02) |
| 10 | ¿Cómo trabajo el expediente? | Seguimiento → Expediente | `10-expediente.md` | Borrador (2026-11-02) |

## D. Otras páginas

| # | Misión | Empieza en → termina en | Archivo | Estado |
|---|---|---|---|---|
| 11 | ¿Cómo veo quién gana los concursos? | Menú → Competencia | `11-competencia.md` | Borrador (2026-11-02) |

## E. Administración (solo administradores, salvo «Cargar archivo»)

| # | Misión | Empieza en → termina en | Archivo | Estado |
|---|---|---|---|---|
| 12 | ¿Cómo cargo un reporte de SICOP? | Menú → Cargar archivo → Panel | `12-cargar-archivo.md` | Borrador (2026-11-02) |
| 13 | ¿Cómo creo y cambio usuarios? | Administración → Usuarios | `13-usuarios.md` | Borrador (2026-11-02) |
| 14 | ¿Cómo asigno el encargado de un cartel? | Seguimiento → Expediente | `14-encargado.md` | Borrador (2026-11-02) |
| 15 | ¿Cómo elijo quién recibe el correo diario? | Administración → Destinatarios | `15-destinatarios.md` | Borrador (2026-11-02) |
| 16 | ¿Qué hago con un aviso que no salió? | Administración → Avisos | `16-avisos.md` | Borrador (2026-11-02) |
| 17 | ¿Qué tan bien encuentra carteles la app? | Administración → Calidad de reglas | `17-calidad.md` | Borrador (2026-11-02) |
| 18 | ¿Cómo reviso lo que la app consultó en SICOP? | Administración → Bitácora de consultas | `18-bitacora.md` | Borrador (2026-11-02) |

## F. Fuera de la app y ayuda general

| # | Misión | Empieza en → termina en | Archivo | Estado |
|---|---|---|---|---|
| 19 | ¿Cómo leo el correo diario? | Correo → Cartel | `19-correo.md` | Borrador (2026-11-02) |
| 20 | ¿Qué hago si algo no funciona? | Cualquiera | `20-problemas.md` | Borrador (2026-11-02) |

## Dónde se ve la ayuda en la app

- `/ayuda` («¿Cómo se usa?», «Ayuda» en el menú de arriba y enlace en el pie): tarjetas por bloque en el orden de esta lista,
  buscador y glosario. Las misiones 13 a 18 solo las ven los administradores (`config/ayuda.yaml`).
- `/ayuda/<misión>`: la misión con sus capturas. Se lee de su archivo: para cambiarla, edita el `.md`.
- Botón «?» abajo a la derecha de cada pantalla: abre la misión de esa pantalla (mapa en `config/ayuda.yaml`).
- Algunas palabras del panel muestran su explicación de `GLOSARIO.md` al pasar el mouse.

## Capturas

Cada marcador `[captura: …]` tiene su imagen, hecha con datos de EJEMPLO (nunca reales):

```
python -m app.cli ayuda capturas                      # todas (rehace la base de ejemplo)
python -m app.cli ayuda capturas --mision 08-revision # solo una misión
```

Quedan en `app/web/static/ayuda/<misión>/<paso>.png` con su texto alternativo en `indice.json` (no van a Git).
Si un botón cambió de nombre, el comando dice la misión, el paso y lo que no encontró: corrige la misión, o
`app/ayuda/pantallas.py` si el marcador no dice el botón entre «».

## Para después (todavía no existen en la app)

- ¿Cómo leo y descargo el Reporte de cartel de 2 páginas? (lección 4 de la IA).
- ¿Cómo uso el asistente para saber si podemos participar?

## Antes de empezar (pendiente con Oscar)

- Quiénes usarán la app y qué tan cómodos están con la tecnología: _(anotar aquí)_.
- 2 o 3 personas que no conozcan la app para las pruebas, con fechas: _(anotar aquí)_.
- ¿Quiere el recorrido de bienvenida? (se decide en la lección 3): _(anotar aquí)_.
