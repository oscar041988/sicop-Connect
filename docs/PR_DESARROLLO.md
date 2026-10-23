# Pull request de `desarrollo` → `main`

> Texto para pegar en GitHub al abrir el PR (título y cuerpo). Actualizado el 2026-10-23, con `desarrollo` en
> el commit que agrega este texto.

**Título:** Rama desarrollo: obtención automática (no activada), Competencia, cierre próximo y resumen, Excel,
revisión general y documentación

---

## Qué trae esta rama

`desarrollo` junta todo el trabajo en local desde el 19/10: **57 commits** sobre `main`, sin conflictos.
**Reemplaza a estas ramas**, que ya están adentro: `acta-despliegue`, `leccion-10`, `obtencion-automatica`,
`doctor-sin-mail-to`, `regla-camaras-intraorales`, `panel-aviso-sin-evaluar` y `zip-pliegos`. Si alguna tiene un
PR abierto, se puede cerrar sin unir. (`diseno-fenova` no tiene nada que no esté en `main`.)

### Ampliaciones (semana 3)
- **A2 · Competencia:** importa el ZIP «Adjudicaciones en firme» (reportes 6, 6.1 y 6.2) y muestra, por familia,
  quién gana, cuántas veces, con qué instituciones y el monto por moneda. El ganador viene solo con cédula: los
  nombres se ponen en `config/competidores.yaml`.
- **A4 · Cierre próximo y resumen semanal:** aviso para lo marcado «Interesa» o «Revisar requisitos» que cierra
  en 3 días o menos; resumen de la semana anterior los lunes. Decisiones finales nuevas: «Ofertada» y «No se oferta».
- **A5 · Exportar a Excel** el listado filtrado, con los números SICOP como texto.

### Obtención automática (aprobada el 21/10) · construida, **no activada**
- Lecciones 1 a 4: lector de Gmail de solo lectura, solicitud con navegador (Playwright), espera, descarga y
  validación, y `obtain auto` (una vuelta cada 15 min, con alerta de FALLO y plan B).
- En la prueba real del 22/10, **SICOP bloqueó la descarga hecha por el programa**; se reporta como FALLO «control
  no automatizable», sin reintento. Consulta enviada a soporte de SICOP el 22/10.
- Con `SOURCE_MODE=manual` (por defecto) no hace nada.

### Revisión general del 23/10
- La versión de reglas del panel y de los avisos es la de la última evaluación **completa** (antes, `evaluate --nro`
  con otro YAML dejaba el panel con un solo cartel).
- El resumen semanal fallido aparece en «Avisos».
- Un CSV dañado da un mensaje claro en vez de error 500.
- Las líneas que llegan antes que su cartel se recuperan solas.
- Tope a la lista de bloqueos de login; evaluar 10 000 carteles pasó de 21 s a 5 s.
- El ciclo importa también el ZIP de adjudicaciones.

### Otros
- ZIP de pliegos tal como llega, en el ciclo y en el panel · exclusión «intraoral» · aviso de datos sin evaluar ·
  `doctor` sin `MAIL_TO` · tarea programada de Windows (siempre dry-run).
- Documentación verificada contra el código y **`docs/ARQUITECTURA.md`** nuevo.

## Qué cambia al actualizar el servidor (`docs/DESPLIEGUE.md`, 9.8)
- [ ] Respaldo antes de empezar.
- [ ] `pip install -r requirements.lock.txt`: se suman `openpyxl`, `playwright`, `greenlet` y `pyee`.
- [ ] `migrate`: migraciones **0008 a 0013**.
- [ ] `evaluate` después de `migrate` (desde la 0008 el panel pide una evaluación completa).
- [ ] Verificar en producción: Competencia (importar el ZIP de adjudicaciones), Excel, cierre próximo y resumen
      (en dry-run).
- [ ] Solo si se activa la obtención automática: `playwright install chromium` (no probado en Ubuntu).

## Para decidir (Oscar)
- [ ] Un día en que **solo** llegan adjudicaciones se importan, pero no se avisa y el ciclo queda en «fallo»
      (no traen carteles nuevos). ¿De acuerdo?
- [ ] Aviso de cierre próximo a **3 días**, y el contenido del resumen semanal.
- [ ] Nombres de las cédulas ganadoras en `config/competidores.yaml`.
- [ ] Hora del ciclo y obtención automática: dependen de la respuesta de SICOP sobre la descarga.
- [ ] Aceptar `docs/DECISION_OBTENCION.md`.

## Pruebas
- **483 passed** en un entorno nuevo creado con `requirements-dev.txt` (Windows, Python 3.14, 23/10). Lo de SICOP
  y Gmail se prueba con páginas y correos **SIMULADOS**, sin salir a internet.
- *Pendiente:* correr las pruebas con Python 3.12, el del servidor.

## Importante
- Ningún correo real se envía: avisos en dry-run.
- `Guia_Obtencion_Automatica_SICOP.docx` no se subió a propósito: una captura muestra un enlace real de descarga.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
