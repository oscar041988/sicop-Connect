# SICOP CONNECT

App de Hermatix para importar datos abiertos de SICOP, detectar oportunidades comerciales
con reglas explicables, revisión humana y aviso por correo.

Estado y siguiente tarea: `docs/ESTADO_PROYECTO.md`. Cómo está construida: `docs/ARQUITECTURA.md`.

## Requisitos

- Python 3.12 o superior (el servidor usa 3.12: conviene desarrollar y probar con esa versión)
- Windows PowerShell (desarrollo) · Linux + systemd (producción)
- Acceso al repositorio privado de GitHub con una llave SSH

## Puesta en marcha (PowerShell)

Un comando por línea: si una línea larga se parte al copiarla, el comando hace otra cosa.

**0. Bajar el código** (la carpeta final se llama como la última palabra; elige una que no exista):

```powershell
cd C:\Users\User
git clone -b desarrollo git@github.com:oscar041988/sicop-Connect.git sicop-connect
cd C:\Users\User\sicop-connect
```

Si `git` no encuentra la llave SSH, agrega `-c core.sshCommand=C:/Windows/System32/OpenSSH/ssh.exe` justo
después de `git`.

**1. Crear y activar el entorno virtual.** Con Python instalado por el «Python Install Manager» de python.org, el
comando es `py`, no `python` (si escribes `python`, Windows ofrece la Microsoft Store: «Python was not found»).
`py list` muestra las versiones instaladas; `py install 3.12` instala la del servidor.

```powershell
py -V:3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Si PowerShell bloquea el script: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`. Con el entorno activado
aparece `(.venv)` al inicio de la línea, y desde ahí `python` sí funciona.

**2. Instalar dependencias:** las versiones exactas del servidor más las herramientas de prueba. No actualices pip
ni ningún paquete aunque lo sugiera: se prueba con las versiones fijas.

```powershell
python -m pip install -r requirements-dev.txt
```

**3. Configuración local.** Edita `.env` solo si hace falta; nunca lo subas a Git.

```powershell
Copy-Item .env.example .env
```

**4. Base y primer usuario del panel.** `create-user` pide correo, nombre y contraseña (al menos 10 caracteres;
no se ve mientras se escribe).

```powershell
python -m app.cli migrate
python -m app.cli create-user --rol admin
```

**5. Comprobar:** `python -m app.cli doctor`. Varios «PENDIENTE» son normales en desarrollo (`docs/OPERACION.md`,
5.1).

## Comandos frecuentes

```powershell
python -m app.cli doctor                 # configuración disponible/pendiente, sin secretos
python -m app.cli migrate                # crea o actualiza el esquema de la base (repetible)
python -m app.cli import --path ARCHIVO --report carteles --origen real
                                         # también lineas, catalogo, instituciones y adjudicaciones (ZIP)
python -m app.cli evaluate               # aplica config/hermatix_rules.yaml (ver docs/REGLAS.md)
python -m app.cli score-rules            # precisión y cobertura de las reglas por familia (docs/REGLAS.md)
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
- Solo administradores: **Usuarios**, **Destinatarios** de los avisos, **Avisos** fallidos o inciertos y
  **Calidad de reglas** (precisión y cobertura por familia).

Comprobar la salud de la app con el servidor en marcha:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

## Configuración

Prioridad: variables del proceso > archivo `.env` > valores por defecto de `app/config.py`.
Las variables disponibles están documentadas en `.env.example`.
