# Guía de uso de SICOP CONNECT

Todo el proceso, de principio a fin: desde que un cartel sale en SICOP hasta que Hermatix descarga su oferta para
firmarla. Cada paso remite a la **misión de ayuda** que lo explica con capturas (en la app: «¿Cómo se usa?», en el
pie de cada página, o el botón «?» abajo a la derecha).

Actualizada el 2026-11-10. Si un botón cambió de nombre, vale lo que dice la misión de ayuda.

---

## El proceso en una mirada

```
SICOP ──► 1. Llegan los carteles (8:00) ──► 2. Correo diario ──► 3. Panel: ver y filtrar
                                                                        │
      8. Expediente y etapa ◄── 7. Asistente: ¿podemos participar? ◄── 4–6. Leer el cartel,
             │                                                             resumen con IA, revisión
             ▼
      9. Botón «Oferta»: el PDF completo ──► una persona firma y sube a SICOP
```

| Paso | Qué pasa | Quién |
|---|---|---|
| 1 | La app trae los carteles de SICOP y los evalúa | Automático (o un administrador, a mano) |
| 2 | Llega el correo con los carteles nuevos | Automático, 8:00 de lunes a viernes |
| 3 | Se ven y se filtran los carteles en el panel | Todo el equipo |
| 4 | Se lee el cartel y su resumen con IA | Todo el equipo |
| 5 | Se decide si interesa | Todo el equipo |
| 6 | Se le da seguimiento y se asigna encargado | Equipo · administrador |
| 7 | El asistente dice si Hermatix cumple los requisitos | Encargado o administrador |
| 8 | Se trabaja el expediente: archivos, notas y etapa | Encargado o administrador |
| 9 | El botón «Oferta» arma la oferta completa en PDF («Oferta en Word»: la misma, en .docx) | Encargado o administrador |
| 10 | Una persona firma con firma digital y sube la oferta a SICOP | Fuera de la app |

**Dos niveles de usuario:**
- **Administrador:** todo, más «Usuarios», «Destinatarios», «Avisos», «Calidad de reglas», «Bitácora de
  consultas», asignar encargados y cargar el perfil de Hermatix.
- **Encargado:** ve los carteles, los revisa y les da seguimiento. Abre el expediente, el asistente y las ofertas
  **solo de los carteles que tiene a cargo**.

---

## 0. Entrar a la app

*Misión 1 · ¿Cómo entro a la app?*

1. Abre la dirección de la app en el navegador. En la PC de desarrollo es **http://127.0.0.1:8000**. Para que
   funcione, antes hay que abrir el panel en PowerShell (ver el anexo A).
2. Escribe tu correo y tu contraseña y haz clic en «Entrar».
3. Llegas al **Panel de carteles**.

---

## 1. Llegan los carteles de SICOP

Pasa solo, de lunes a viernes antes de las 8:00: la app pide el reporte a SICOP, lo importa y evalúa cada cartel
con las reglas de Hermatix (`config/hermatix_rules.yaml`). Cada cartel queda con su **prioridad**:

- **Alta:** se parece mucho a lo que vende Hermatix.
- **Media:** se parece un poco.
- **Baja:** no se muestra en el panel.

**Si la carga automática falló** (misión 12 · ¿Cómo cargo un reporte de SICOP?):
1. Menú «Cargar archivo» → «Abrir el correo de SICOP en Gmail».
2. Abre el correo «Envío de reporte» de hoy y haz clic en «URL de descarga». Se baja un ZIP. No lo abras ni le
   cambies el nombre.
3. En la app: «Tipo de reporte» = **pliegos (.zip)**, «Origen de los datos» = **real**.
4. Elige el ZIP y haz clic en «Subir e importar». Espera cerca de medio minuto.
5. Lee «Resumen de la importación» y «Evaluación».

Subir el mismo ZIP dos veces no duplica nada: la app lo reconoce.

---

## 2. El correo diario

*Misión 19 · ¿Cómo leo el correo diario?*

- Llega cerca de las **8:00, de lunes a viernes**, con el asunto que empieza con «SICOP ·».
- Trae cada cartel con su prioridad, su cierre y, si ya está, el **resumen con IA**. Los resúmenes se preparan
  después de las 10:00; si dice «todavía no está», míralo más tarde en la app.
- «Ver en el panel» abre el cartel en la app.
- Quién lo recibe lo elige un administrador en «Destinatarios» (misión 15).

---

## 3. Ver y filtrar los carteles

*Misiones 2 y 3 · carteles nuevos · buscar y filtrar*

1. Arriba de la lista: «Todos», «Sin revisar», «Interesa»… **«Sin revisar»** muestra lo que nadie ha decidido.
2. Cada fila: título, institución, tipo, etiqueta **«Nuevo»** (solo el día que llega), familia, **monto
   estimado**, **cierre de ofertas** (en naranja si faltan 7 días o menos) y prioridad.
3. «Ver más» abre el número SICOP, las palabras clave detectadas y el servicio de Hermatix.
4. El buscador encuentra por número SICOP o por palabras. «Más filtros»: prioridad, familia, institución,
   plazo, revisión y tipo de procedimiento.
5. «Exportar a Excel» baja la lista que estás viendo.
6. Haz clic en una fila para abrir el cartel.

Los carteles salen ordenados por cierre: primero los que cierran antes. Los vencidos no salen.

---

## 4. Leer el cartel

*Misiones 4 a 7*

**Arriba** (misión 4): institución, título con las palabras resaltadas, número SICOP, «¿Podemos participar?» y
cuatro cifras: monto estimado, cierre, encaje (prioridad y familia) y duración del contrato.

**Enlaces de arriba:** «Reporte PDF», «Ver en SICOP ↗» y, si el cartel está en seguimiento y te toca, «Abrir
expediente», «Expediente ZIP» y el botón **«Oferta»** (paso 9).

**Pestañas:**
- **Resumen ejecutivo con IA** (misión 5): qué piden, garantías y plazos, y una recomendación preliminar con
  citas al pliego [DOC n · pág. p]. La decisión es de una persona.
- **Información de SICOP y documentos** (misión 6): los datos del cartel y los archivos del pliego.
- **Por qué aparece, líneas y cobertura** (misión 7): qué regla lo encontró y qué compran, línea por línea.

**Reporte de cartel en PDF** (misión 25): hasta 3 páginas con los datos de SICOP, la recomendación, los
requerimientos con «¿Cumple?» y «Por qué se recomienda». Sirve para compartirlo o imprimirlo.

---

## 5. Decidir si interesa

*Misión 8 · ¿Cómo marco si un cartel interesa o no?*

1. Al final del cartel, en **«Revisión»**, elige la decisión:
   «Interesa» · «No interesa» · «Revisar requisitos» · «Ofertada» · «No se oferta».
2. Con «No interesa», elige el **motivo** (portafolio, plazo, requisitos, presupuesto u otro).
3. Escribe un comentario, por ejemplo «Piden 3 años de experiencia y tenemos 2».
4. Haz clic en «Guardar revisión».

La revisión queda a tu nombre en el **Historial**. Las revisiones **nunca se borran**, ni al actualizar los datos
de SICOP: si te equivocas, guarda otra y la nueva queda como «(vigente)».

---

## 6. Dar seguimiento y asignar encargado

*Misiones 9 y 14*

1. Arriba del cartel, haz clic en **«Dar seguimiento»**. Queda en la etapa «Preparando» y pasa a la página
   «Seguimiento» (menú de arriba).
2. Un **administrador** abre el expediente → «Encargado» → «Asignar el encargado» → «Guardar».
3. Al encargado le llega un correo en el próximo envío de las 8:00.

Solo el encargado y los administradores abren el expediente, el asistente y las ofertas de ese cartel.

---

## 7. ¿Podemos participar? El asistente de elegibilidad

*Misiones 21, 23 y 24*

**Antes, una sola vez: el perfil de Hermatix** (misión 21). Menú «Perfil». Ahí se guardan la experiencia, los
permisos, las pólizas y sus documentos, con su vencimiento. Cargar o cambiar datos es para administradores; lo
anterior no se borra, queda en el historial de versiones.

**El asistente** (misión 23). Necesita el resumen con IA y que el cartel esté en seguimiento.
1. En el cartel, en «Asistente de elegibilidad», haz clic en **«Empezar el asistente»**. La primera vez, la IA
   saca los requisitos del pliego. Tarda un poco.
2. Primero vienen los **excluyentes** («Revisión rápida»): si uno no se cumple, Hermatix queda fuera.
3. Cada pregunta trae su cita del pliego y, si existe, lo que ya dice **el perfil**. Si está bien, haz clic en «Sí,
   es correcto». Si no, responde y haz clic en «Guardar respuesta».
4. Si no sabes: «Todavía no lo sé». Si no existe: «Hermatix no lo tiene». Si existe pero lo subes después: «Lo
   tiene · subo el archivo después».

**El resultado** (misión 24):
1. Haz clic en **«Calcular el resultado»**. Sale uno de cuatro: «Sí, pueden participar», «Pueden participar si
   completan lo que falta», «No cumplen un requisito excluyente» o «Falta información».
2. En «Cómo va cada requisito», decide los que dicen **«Revisar»** con «Cumple» o «No cumple» y calcula de nuevo.
3. «Ver constancia» → «Descargar PDF». Cada cálculo deja una constancia nueva.

Todos los requisitos se presentan: la app no esconde ninguno. El resultado orienta; **la decisión de participar
es de una persona**.

---

## 8. El expediente

*Misión 10 · ¿Cómo trabajo el expediente?*

En «Seguimiento» → «Abrir expediente»:
- **Etapa:** «Preparando» → «Enviada» → «Ganada» o «Perdida». Cámbiala cuando la oferta avance.
- **Archivos:** «Subir un archivo» → «Subir». Cada archivo queda con tu nombre y la fecha.
- **Notas:** por ejemplo «Llamé a la institución, responden el lunes» → «Guardar nota».
- **«Descargar todo el expediente (ZIP)»:** los archivos, las notas y el historial, para pasárselo a otra persona.

Nada se borra: archivos, notas, etapas y encargados quedan en el historial.

---

## 9. Preparar la oferta

En el cartel, el botón **«Oferta»** (solo el encargado y los administradores, porque trae precios). No hay
formulario: un clic y en unos segundos se descarga la oferta completa en un solo PDF, con la forma de la oferta
ganadora de NAVSAT y el membrete de Hermatix. Una copia queda en `EXPORTS_DIR/ofertas/<procedimiento>/`.

Al lado, **«Oferta en Word»** descarga **el mismo documento en Word (.docx)**, por si hay que retocar algo a mano
(pedido de Oscar, 2026-11-11). Trae lo mismo y en el mismo orden; lo que está en rojo en el PDF también lo está en el
Word. Los documentos adjuntos van como imágenes de cada página: para subir a SICOP, el original sigue siendo el que
va dentro del PDF.

> **La app formula la oferta; una persona la revisa, la firma con firma digital y la sube a SICOP.**
> La app no inventa precios ni sube nada a SICOP.

**Antes del primer uso (una sola vez, Oscar):**
- `config/tarifario.yaml`: el precio de cada producto de Hermatix, su moneda, si es mensual o único, el IVA y los 4
  porcentajes del desglose (suman 100).
- `config/oferta.yaml`: nombre, cédula y calidades del representante legal que firma.

**Antes de presionar «Oferta» (en cada cartel):**
- El cartel tiene que tener sus **documentos de SICOP** (los trae el enriquecimiento de las 10:00). Sin el pliego,
  la app avisa «Falta el pliego».
- Conviene **responder el asistente de elegibilidad** (paso 7) y subir ahí los documentos que pide el pliego: esos
  archivos son los anexos de la oferta.

**El asistente como chat** (si está encendido, `ASSISTANT_CHAT=true`): en lugar de una pregunta a la vez con su
formulario, el asistente conversa. Conteste con sus palabras («sí, tenemos 14 años») y suba los documentos en el
mismo chat. La IA propone las respuestas y **la app las guarda y lo confirma** debajo («Guardado · …»); si algo no
se pudo guardar, lo dice («un documento necesita el archivo»). Cuando todos los requisitos tienen respuesta, sale
**«Ya está lista la oferta»** con los botones para pedirla en PDF o en Word.

### 9.1 Qué trae el PDF, en orden

1. **Portada:** institución, «OFERTA», tipo y número de procedimiento, objeto, oferente y cédula jurídica.
2. **El pliego, sección por sección,** copiado tal cual. Al final de cada sección: «Respuesta Sección 01 – Llamado a
   Cotizar · Entendemos, aceptamos y cumplimos con lo requerido» (o «Entendemos y aceptamos lo indicado» cuando la
   sección solo informa).
3. **Listado de Anexos:** 1 Oferta Económica · 2 Documentación Legal · 3 Propuesta Técnica · 4 Certificaciones.
4. **Anexo 1.1, oferta económica:** carta, tabla de precios con el monto en letras, condiciones, desglose y fórmula
   de reajuste (diseño de Tarrazú), con los precios del tarifario.
5. **Los anexos:** cada documento del asistente con su página de título («Anexo 2.1: Patente municipal»).

### 9.2 Lo que sale en rojo (y no se firma así)

Si algo falta, la portada dice **«BORRADOR: hay N puntos sin resolver. No firmar ni subir a SICOP todavía»** y la
lista. Puede ser:
- **una sección con un requisito que no cumple, falta o hay que revisar** según el asistente: esa sección no dice
  «cumplimos», dice en rojo qué falta. Se arregla respondiendo el asistente y volviendo a presionar «Oferta»;
- **«PRECIO PENDIENTE»:** el producto del cartel no tiene tarifa en `config/tarifario.yaml`;
- **un anexo «PENDIENTE»:** no se subió el archivo en el asistente;
- **la ficha técnica del equipo:** pendiente hasta que Oscar decida cómo se elige en cada cartel;
- **el representante legal:** faltan sus datos en `config/oferta.yaml`.

Volver a presionar «Oferta» con el mismo pliego no gasta IA: la app recuerda las secciones.

### 9.3 Antes de subir a SICOP

- [ ] La portada **no** dice «BORRADOR».
- [ ] Revisar el PDF contra el pliego: montos, monto en letras, condiciones y anexos.
- [ ] Firmarlo con firma digital.
- [ ] Subirlo a SICOP junto con lo que pida el pliego y no esté en la oferta.
- [ ] En el expediente, cambiar la etapa a **«Enviada»** y en la revisión marcar **«Ofertada»**.

---

## 10. Después del concurso

- En el expediente, marca la etapa **«Ganada»** o **«Perdida»**.
- **Competencia** (menú; misión 11): quién gana qué, según las adjudicaciones de SICOP.

---

## Administración (solo administradores)

| Página | Para qué | Misión |
|---|---|---|
| Usuarios | Crear usuarios y cambiar su nivel o estado | 13 |
| Destinatarios | Quién recibe el correo diario | 15 |
| Avisos | Correos que no salieron o quedaron inciertos | 16 |
| Calidad de reglas | Qué tan bien encuentran carteles las reglas | 17 |
| Bitácora de consultas | Qué consultó la app en SICOP | 18 |

---

## Si algo no funciona

*Misión 20*

1. Recarga con **Ctrl + F5**.
2. Cierra la pestaña y abre la app de nuevo. Si te sacó, vuelve a entrar.
3. ¿No encuentras un cartel? Búscalo por su número SICOP. En «Más filtros», elige «Todas» en «Prioridad».
4. ¿Un dato distinto al de SICOP? Vale lo de SICOP: avísale a quien administra la app.
5. Si nada funciona, toma una captura de pantalla y mándala con lo que estabas haciendo.

---

## Anexo A. Abrir el panel en la PC (desarrollo)

En PowerShell:

```powershell
cd C:\Users\User\sicop-connect
.\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --reload
```

Abre **http://127.0.0.1:8000**. Para cerrarlo: **Ctrl + C** en PowerShell. Si llegó una migración nueva, haz el
respaldo y `python -m app.cli migrate` con el panel cerrado.

## Anexo B. Comandos útiles

```powershell
python -m app.cli doctor                         # revisa la configuración, sin mostrar secretos
python -m app.cli backup --output CARPETA        # respaldo de la base
python -m app.cli migrate                        # actualiza la base (con el panel cerrado)
python -m app.cli oferta economica --datos OFERTA.yaml   # oferta económica desde un archivo
python -m app.cli --help                         # todos los comandos
```

El uso diario completo está en `docs/OPERACION.md`; la instalación en el servidor, en `docs/DESPLIEGUE.md`.

## Reglas que la app siempre cumple

- Distingue los datos **reales** (de SICOP) de los **sintéticos** y **simulados** (pruebas).
- No inventa datos de SICOP. Si el pliego no trae algo, dice «no encontrado».
- No borra revisiones, notas, archivos ni historiales.
- El dinero va siempre con su moneda, y nunca suma monedas distintas.
- La IA resume y explica. **Las decisiones las toma una persona.**
