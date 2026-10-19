# SICOP CONNECT

App de Hermatix para importar datos abiertos de SICOP, detectar oportunidades comerciales
con reglas explicables, revisión humana y aviso por correo.

Estado actual: base del proyecto (salud de la app y diagnóstico). Ver `docs/ESTADO_PROYECTO.md`.

## Requisitos

- Python 3.12 o superior
- Windows PowerShell (desarrollo) · Linux + systemd (producción)

## Puesta en marcha (PowerShell)

```powershell
# 1. Crear y activar el entorno virtual
python -m venv .venv
.\.venv\Scripts\Activate.ps1
# Si PowerShell bloquea el script:
#   Set-ExecutionPolicy -Scope CurrentUser RemoteSigned

# 2. Instalar dependencias (incluye las de desarrollo)
python -m pip install -r requirements-dev.txt

# 3. Configuración local
Copy-Item .env.example .env
# Edita .env si hace falta. Nunca lo subas a Git.
```

## Comandos

```powershell
python -m app.cli doctor                 # configuración disponible/pendiente, sin secretos
python -m app.cli migrate                # crea o actualiza el esquema de la base (repetible)
python -m app.cli import --path ARCHIVO --report carteles --origen real   # también lineas, catalogo, instituciones
python -m app.cli evaluate               # aplica config/hermatix_rules.yaml (ver docs/REGLAS.md)
python -m app.cli compra NRO_SICOP       # un cartel con su comprador y sus líneas
python -m pytest                         # pruebas
python -m uvicorn app.main:app --reload  # panel en http://127.0.0.1:8000
```

### Panel web

Con el servidor en marcha, abrir http://127.0.0.1:8000. La lista muestra los candidatos (Alta y Media) de la
última evaluación, ordenados por cierre más próximo, con filtros por prioridad, familia, institución, plazo,
revisión y tipo de procedimiento. El detalle de cada cartel muestra la evidencia resaltada, las líneas, el
comprador y el formulario de revisión (decisión, motivo si «No interesa», comentario y responsable). Las
revisiones no se borran ni se modifican, y se conservan al reimportar datos.

Todavía **sin usuarios ni contraseña** (lección 6): usar solo en la computadora local.

Comprobar la salud de la app con el servidor en marcha:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

## Configuración

Prioridad: variables del proceso > archivo `.env` > valores por defecto de `app/config.py`.
Las variables disponibles están documentadas en `.env.example`.
