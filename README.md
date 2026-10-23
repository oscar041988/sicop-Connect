# SICOP CONNECT

App de Hermatix para importar datos abiertos de SICOP, detectar oportunidades comerciales
con reglas explicables, revisión humana y aviso por correo.

Estado y siguiente tarea: `docs/ESTADO_PROYECTO.md`. Cómo está construida: `docs/ARQUITECTURA.md`.

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

# 2. Instalar dependencias: las versiones exactas del servidor más las herramientas de prueba
python -m pip install -r requirements-dev.txt

# 3. Configuración local
Copy-Item .env.example .env
# Edita .env si hace falta. Nunca lo subas a Git.

# 4. Base y primer usuario del panel
python -m app.cli migrate
python -m app.cli create-user --rol admin   # pide correo, nombre y contraseña (no se muestra)
```

## Comandos frecuentes

```powershell
python -m app.cli doctor                 # configuración disponible/pendiente, sin secretos
python -m app.cli migrate                # crea o actualiza el esquema de la base (repetible)
python -m app.cli import --path ARCHIVO --report carteles --origen real
                                         # también lineas, catalogo, instituciones y adjudicaciones (ZIP)
python -m app.cli evaluate               # aplica config/hermatix_rules.yaml (ver docs/REGLAS.md)
python -m app.cli compra NRO_SICOP       # un cartel con su comprador y sus líneas
python -m app.cli run-cycle --origen real --dry-run   # recoger → importar → evaluar → avisar (vista previa)
python -m app.cli notify --dry-run       # prepara los avisos y escribe la vista previa
python -m app.cli backup --output CARPETA            # respaldo consistente con manifiesto
python -m pytest                         # pruebas
python -m uvicorn app.main:app --reload  # panel en http://127.0.0.1:8000 (solo en desarrollo)
```

`python -m app.cli --help` lista todos los comandos (usuarios, Gmail, obtención automática…). El uso diario
está en `docs/OPERACION.md` y la instalación en el servidor en `docs/DESPLIEGUE.md`.

### Panel web

Con el servidor en marcha, abrir http://127.0.0.1:8000 e iniciar sesión. Tiene:

- **Panel de carteles:** los candidatos (Alta y Media) de la última evaluación, ordenados por cierre más próximo,
  con búsqueda y filtros por prioridad, familia, institución, plazo, revisión y tipo de procedimiento, y el botón
  «Exportar a Excel».
- **Detalle de cada cartel:** evidencia resaltada, líneas, comprador y el formulario de revisión. La revisión
  queda a nombre del usuario de la sesión; las revisiones no se borran ni se modifican y se conservan al
  reimportar datos.
- **Cargar archivo** (ZIP o CSV de SICOP) y **Competencia** (quién gana qué, a partir de las adjudicaciones).
- Solo administradores: **Usuarios**, **Destinatarios** de los avisos y **Avisos** fallidos o inciertos.

Comprobar la salud de la app con el servidor en marcha:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

## Configuración

Prioridad: variables del proceso > archivo `.env` > valores por defecto de `app/config.py`.
Las variables disponibles están documentadas en `.env.example`.
