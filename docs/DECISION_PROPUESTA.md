# Decisión: que la app arme la oferta de un cartel para presentarla en SICOP

**APROBADO por Oscar (comunicado por Ivania el 2026-11-09).** Redactado por Ivania con Claude el mismo día.
Lo marcado **[por decidir · Oscar]** en la sección 6 sigue abierto: se llena cuando él lo diga. Lo que no depende de
esas decisiones (la parte económica, que la app calcula sin IA) se puede construir ya.

## 1. Problema

Hoy SICOP CONNECT encuentra los carteles, los resume, arma la lista de verificación, dice si Hermatix puede
participar y guarda los documentos en el expediente. Pero la oferta todavía se arma a mano: buscar cada documento,
responder punto por punto las especificaciones, llenar los formularios y la tabla de precios. Es lento, y un
requisito olvidado deja la oferta fuera del concurso aunque tenga el mejor precio.

Pedido de Oscar (comunicado por Ivania, 2026-11-09): que la app arme la propuesta y que se pueda presentar en SICOP
para concursar.

## 2. Lo que la app NO puede hacer (límites, no opciones)

1. **Asegurar que se ganen todos los concursos.** En SICOP gana la oferta con más puntaje según el sistema de
   evaluación del cartel, y casi siempre el precio pesa mucho. Los precios de la competencia no se conocen antes
   del cierre. La meta realista está en la sección 3.
2. **Presentar la oferta en SICOP por sí sola.** La oferta la sube y la firma con **firma digital** la persona
   autorizada de Hermatix. No se conoce una API de SICOP para presentar ofertas, y las reglas del proyecto prohíben
   inventarla (`CLAUDE.md`, «Prohibido»). La app entrega el paquete listo y la persona lo revisa, lo firma y lo
   sube.
3. **Decidir el precio.** La app puede proponer un precio con las reglas de Hermatix (sección 4), pero el precio
   final siempre lo aprueba una persona.
4. **Declarar algo que Hermatix no tiene.** Si falta un documento o un dato, la app lo marca como faltante; nunca
   lo rellena ni lo supone.

## 3. Qué se propone

**Meta realista:**
- **Cero ofertas descalificadas por forma** (admisibilidad): ningún requisito faltante, ningún documento vencido
  y ningún formulario sin firmar.
- **El puntaje máximo posible en todo lo que no es precio:** experiencia, plazo de entrega, garantía y
  certificaciones, según la tabla de evaluación de cada cartel.
- **Menos horas por oferta**, medidas antes y después.

**Lo que ya existe y se reutiliza:**

| Pieza que ya existe | Cómo sirve para la oferta |
|---|---|
| Enriquecimiento (ficha y documentos de SICOP) | El pliego, las especificaciones, los anexos y las enmiendas de cada cartel |
| Reporte de cartel con IA | Qué piden, plazos y garantías, con la cita al documento y la página |
| Lista de verificación y asistente de elegibilidad | Requisito por requisito: qué tiene Hermatix y qué falta |
| Perfil de Hermatix | Los documentos de la empresa con su vencimiento |
| Gestor de documentos (expediente, encargado, etapas) | Dónde se arma la oferta y quién la tiene a cargo; etapas «preparando · enviada · ganada · perdida» |
| Página «Competencia» (adjudicaciones) | A quién se le adjudicó, y por cuánto, en carteles parecidos |

**Alcance (Ivania, 2026-11-09): la app formula los archivos de la oferta; una persona los sube a SICOP.** Nada
se presenta desde la app. Con lo aprendido en Tarrazú (sección 9), los archivos que formularía son:

| Archivo | Qué lleva | Cómo se arma |
|---|---|---|
| Carta de presentación | Empresa, representante, procedimiento, declaración del Registro de Proveedores (art. 29 LGCP) | Plantilla de Hermatix + datos del cartel |
| Oferta económica | Tabla de precios (línea, cantidad, unitario, mensual o total, IVA), **monto en letras**, «Última línea» | La app calcula; el precio lo aprueba una persona |
| Desglose del precio | Rubros en montos y porcentajes que cuadran (mano de obra, insumos o equipos, gastos, utilidad) | La app calcula |
| Fórmula de reajuste | La fórmula con los porcentajes del desglose | Plantilla + los porcentajes |
| Condiciones generales | Garantía, entrega, forma de pago, validez, aceptación del pliego | Plantilla + lo que pide el pliego |
| Respuesta técnica (matriz de cumplimiento) | Cada especificación del pliego ↔ lo que ofrece Hermatix ↔ la ficha que lo prueba | Etapa 2; las fichas de los productos |
| Índice de documentos | Qué documento de admisibilidad va (perfil, autenticado por notario o no) y si está vigente | Lista de verificación + perfil |

**Lo nuevo, por etapas** (cada una se aprueba y se prueba antes de la siguiente):

1. **Paquete de documentos:** la app junta lo que pide el cartel y ya está en el perfil (personería, CCSS,
   declaraciones, certificaciones), avisa qué falta o qué vence antes del cierre y arma una carpeta ordenada
   según el pliego.
2. **Respuesta técnica:** una tabla «el cartel pide · Hermatix ofrece · documento que lo prueba» para cada
   especificación técnica, con las fichas de los productos. Lo que no se pueda cumplir queda marcado y no se
   esconde.
3. **Puntaje esperado:** con la tabla de evaluación del cartel, la app calcula cuántos puntos sacaría la oferta
   en cada factor y muestra dónde se pueden ganar más (por ejemplo, ofrecer un plazo de entrega más corto).
4. **Tabla de precios (borrador):** con los costos y márgenes de Hermatix y los precios adjudicados en carteles
   parecidos. La aprueba una persona.
5. **Revisión final y entrega:** una lista para revisar antes de subir a SICOP, quién firma y el paquete
   descargable (los archivos de la tabla de arriba). **La persona** los sube a SICOP. Después del concurso se registra el resultado (ganada o perdida y el puntaje) para aprender.

## 4. Lo que se necesita para empezar

| Qué | Para qué | ¿Ya está? | Quién lo entrega |
|---|---|---|---|
| **Una o dos ofertas reales ya presentadas en SICOP**, con capturas de cada pantalla del formulario de oferta. Hermatix no ha perdido concursos (Ivania, 2026-11-09): para comparar sirven otras ganadas o las ofertas públicas de otras empresas en concursos de sus familias | Conocer los campos y adjuntos que pide SICOP sin inventarlos | **Parcial:** pliego y oferta económica de una ganada (Tarrazú, 2025; sección 9). Faltan la oferta técnica y las capturas | Oscar |
| **El acta de adjudicación de esas ofertas**, con el puntaje de cada oferente | Saber por qué se ganó o se perdió | Parcial (hay adjudicaciones en «Competencia») | **[por decidir · Oscar]** |
| **Documentos legales**: personería jurídica, cédula jurídica, CCSS y FODESAF al día, declaraciones juradas que siempre se piden | Adjuntarlos sin buscarlos | Parcial (están en el «Perfil») | **[por decidir · Oscar]** |
| **Fichas técnicas** de cada producto (FleetMatix, Fenova IA, PassengerIQ, MoveOn, SmartTags, FleetRun, Osmia IoT, BodyCams) y las certificaciones de los fabricantes | La respuesta técnica (etapa 2) | No | **[por decidir · Oscar]** |
| **Experiencia comprobable**: contratos anteriores con cartas de referencia o constancias | Puntos de experiencia | Parcial | **[por decidir · Oscar]** |
| **Hojas de vida del personal técnico** (con su permiso) | Requisito frecuente en los servicios | No | **[por decidir · Oscar]** |
| **Reglas de precio**: costos, margen mínimo, IVA, tipo de cambio y quién aprueba el precio final | La tabla de precios (etapa 4) | No | **[por decidir · Oscar]** |
| **Plantillas de Hermatix**: carta de presentación, oferta técnica, garantías | Que todas las ofertas tengan el mismo formato | No | **[por decidir · Oscar]** |

## 5. Reglas propuestas

1. **La app arma y una persona decide.** Nada sale de la app hacia SICOP sin la revisión y la firma de la persona
   autorizada.
2. **Nunca se inventa.** Cada afirmación de la oferta apunta a un documento de Hermatix; lo que no tiene
   respaldo queda como faltante.
3. **El precio lo aprueba una persona**, y queda registrado quién lo aprobó y cuándo.
4. **Los números y las fechas los calcula la app**, no la IA: puntajes, vencimientos y montos (como en
   `DECISION_IA.md` §4).
5. **Los documentos de Hermatix son confidenciales:** fuera de Git, en el respaldo, con permisos y con registro de
   cada acceso, como el perfil.
6. **Se distinguen los datos:** reales, sintéticos (pruebas) y simulados (`CLAUDE.md`).
7. **Pruebas siempre con datos sintéticos y con IA simulada**, sin gastar dinero.
8. **Con la ampliación apagada, la app funciona igual que hoy.**

## 6. Para decidir con Oscar

| Tema | Decisión |
|---|---|
| ¿Se aprueba la ampliación y en qué orden van las etapas de la sección 3? | **[por decidir · Oscar]** |
| ¿Con qué tipo de cartel se empieza? Propuesta: **una sola familia** (por ejemplo GPS para flotas, la más frecuente), no todas a la vez | **[por decidir · Oscar]** |
| **Uso de IA para redactar la oferta.** `DECISION_IA.md` solo la permite para el reporte y el asistente; hace falta una aprobación nueva, como sección nueva de ese documento | **[por decidir · Oscar]** |
| **¿Se envía a la IA el texto de los documentos de Hermatix?** El 2026-11-04 Oscar decidió que no para el asistente (`ASSISTANT_SEND_DOCUMENTS=false`). Sin ellos, la IA redacta solo con el cartel y los datos escritos | **[por decidir · Oscar]** |
| **Quién revisa y quién firma** cada oferta en SICOP | **[por decidir · Oscar]** |
| **Con cuántos días de anticipación** al cierre tiene que estar lista la oferta para revisarla | **[por decidir · Oscar]** |
| **Quién aprueba el precio** y con qué margen mínimo | **[por decidir · Oscar]** |
| Presupuesto de IA para esta ampliación (hoy el tope diario de la app es 1.00 USD) | **[por decidir · Oscar]** |
| ¿Dónde se guardan los documentos de la oferta? Propuesta: en el servidor, como los del perfil (decisión del 2026-11-04) | **[por decidir · Oscar]** |

## 7. Riesgos

- **Una oferta con un error que nadie revisó.** Mitigación: regla 1 y la lista de revisión final (etapa 5).
- **Documentos confidenciales expuestos.** Mitigación: regla 5; nada en Git ni en un chat.
- **Cambios en SICOP** (formularios nuevos). Mitigación: la app no llena SICOP directamente; solo cambia el
  paquete.
- **Esperar de la app más de lo que puede dar** («ganar todos»). Mitigación: medir con la meta realista de la
  sección 3.

## 8. Aceptación

- [x] Oscar aprueba la ampliación (2026-11-09, comunicado por Ivania). Falta que decida los puntos abiertos de la
      sección 6.
- [x] Oferta de ejemplo: la ganadora de Tarrazú (sección 9). Para construir no hacen falta los documentos de la
      empresa (son adjuntos: la app solo los lista y revisa su vigencia).
- [ ] Si se aprueba la IA para la oferta: `DECISION_IA.md` con su sección nueva y `CLAUDE.md` actualizado.

## 9. Lo aprendido de una oferta ganadora (Tarrazú, 2025)

Leída con autorización de Oscar (2026-11-09, comunicada por Ivania): el pliego y la oferta económica de la
Licitación Reducida **2025LD-000058-0002900001** (Municipalidad de Tarrazú, videovigilancia con IA para la flotilla;
familia videotelemática), que ganó Hermatix. El análisis completo, con precios, está **solo en local**
(`data/ofertas/analisis_oferta_tarrazu.md`): los precios y el margen no van a Git.

**Qué pidió el pliego** (y la app tendría que convertir en lista de verificación de la etapa 1):
- Documentos **autenticados por notario**: certificación de la empresa, 2 cartas de referencia (5 años de
  experiencia) y títulos y CV de 2 técnicos. Además patente, permiso sanitario y certificado RAEE.
- Por equipo: marca, modelo, año (≤ 2 años), fabricante, distribuidor y **catálogos originales** de fábrica.
- Precio en números **y letras**, tributos desglosados y **presupuesto detallado** en montos y porcentajes.
- Evaluación: precio 50 · calidad técnica 25 (matriz de cumplimiento) · plataforma 10 · soporte 10 · posventa 5 ·
  desempate PYME +5.

**Cómo es la oferta económica de Hermatix:** carta de presentación con la declaración del Registro de Proveedores
(art. 29 LGCP) · tabla de precios (línea, cantidad, precio unitario mensual, mensual, anual, IVA, total en letras,
«Última línea») · condiciones generales (garantía, entrega, pago, validez, aceptación del pliego) · descripción del
equipo y de las funciones ADAS y DSM · desglose del precio en 4 rubros (montos y porcentajes) · **fórmula de
reajuste de precios** (con los mismos porcentajes y los índices de mano de obra, insumos y gastos) · firma. No trae la
respuesta punto por punto ni los documentos de admisibilidad: fueron en otros archivos de la oferta en SICOP.

**Lo que esto le dice a la app:**
1. **La app puede armar sola** (sin IA, la app calcula): la tabla de precios con el **monto en letras**, el desglose
   con montos y porcentajes que cuadran, y la carta y las condiciones generales desde una plantilla de Hermatix.
2. **La lista de verificación ya existe** (asistente de elegibilidad): falta marcar qué va **autenticado por
   notario** y qué documento del perfil lo cubre.
3. **La matriz de cumplimiento técnico vale 25 puntos** y la oferta económica no la trae: la respuesta punto por
   punto (cada especificación ↔ la ficha técnica que la prueba) es la etapa 2, y es donde más puntos hay después
   del precio. Ejemplo: el pliego pedía identificación facial del conductor, RS232/RS485 y cifrado de la memoria,
   que la oferta económica no menciona.
4. **Señalar inconsistencias del pliego** («sesenta (10) dispositivos») y pedir la aclaración a tiempo.

**Falta** para seguir: la oferta técnica y sus anexos, el acta de adjudicación con los puntajes y las capturas de
SICOP. (Hermatix no ha perdido concursos; para comparar, otras ofertas ganadas.)

## 10. Construido: la oferta económica (2026-11-09)

Primera parte, sin IA: `python -m app.cli oferta economica --datos OFERTA.yaml [--salida RUTA.pdf]`
(`app/oferta_economica.py`, plantilla `app/web/templates/oferta_economica.html`). Lee los datos de la oferta (el
ejemplo SINTÉTICO está en `tests/fixtures/oferta_sintetica.yaml`) y arma un PDF tamaño carta con:

- **Carta de presentación** con la declaración del Registro de Proveedores (art. 29 LGCP).
- **Tabla de precios**: líneas, precio unitario (mensual si es arrendamiento), subtotales, IVA (tasa o exento con su
  motivo, como pide el pliego), total, «Última línea» y el **monto en letras**.
- **Condiciones generales**: garantía, entrega, forma de pago, validez, aceptación del pliego y precio en firme.
- **Desglose del precio** en los cuatro rubros de la fórmula (mano de obra, insumos, gastos administrativos y
  utilidad), con montos que suman exactamente el subtotal.
- **Fórmula de reajuste** con los porcentajes del desglose.
- Bloque de **firma** (la firma digital la pone la persona).

Los montos son Decimal con su moneda (una sola por oferta). El precio lo escribe y lo aprueba una persona. El PDF
queda en `EXPORTS_DIR/ofertas/<procedimiento>/` (fuera de Git) y nunca se sobrescribe. **Comprobado:** con los datos
de la oferta ganadora de Tarrazú (solo en local), la app da los mismos montos, el mismo monto en letras y el mismo
desglose al céntimo. 32 pruebas en `tests/test_oferta_economica.py`.

**Formulario en el panel (hecho, 2026-11-09):** en el cartel, «Oferta económica» (junto a «Abrir expediente»).
Lo ven y lo llenan solo quienes entran al expediente (su encargado y los administradores), porque trae precios.
Sale lleno con lo del cartel (procedimiento, tipo, institución, objeto y líneas con su cantidad) y con
`config/oferta.yaml` (empresa, lugar, condiciones y nombres del desglose); los precios y los porcentajes, vacíos.
«Guardar borrador» lo guarda (migración 0041, un borrador por cartel); «Descargar PDF» lo guarda, lo revisa y
entrega el PDF. Si un dato no sirve, vuelve el formulario con lo escrito y el motivo. El historial anota quién guardó
y quién generó el PDF, sin montos. 5 pruebas en `tests/test_oferta_panel.py`.

**Diseño igual a la oferta de Tarrazú (2026-11-10, pedido de Ivania):** el PDF copia el formato de la oferta ganadora.
Cada hoja lleva el **membrete de Hermatix** (logo con la franja azul arriba; franjas verde, gris y azul abajo), tomado
de ese PDF (`app/web/static/membrete-cabecera.png` y `membrete-pie.png`; lo pone `oferta_economica.pdf` como
encabezado y pie de Chromium). Times New Roman; carta con la fecha en negrita a la derecha, destinatario en negrita,
referencia centrada con el objeto en mayúsculas y cuerpo justificado; tabla de precios con encabezado azul, «Por
unidad» / «Mensual», filas «Sub Total anual», «Total, IVA» y «Total anual» con la etiqueta en azul, «*****Última
Línea********» y el recuadro «Monto en Letras»; montos con punto de miles (₡27.030,00); condiciones con «Nota:» en
rojo; «DESGLOSE DE PRECIO»; «Fórmula Matemática» con llaves y fracciones; firma centrada. **Diferencias:** no salen
las páginas de descripción del equipo (son de cada cartel: esperan las fichas técnicas), la firma no lleva «Sr.» y,
si la oferta está exenta, el motivo del IVA va debajo de la tabla. La respuesta técnica no lleva membrete.

**Aviso sin precio (2026-11-10):** «Descargar PDF» con una línea sin precio decía `«precio_unitario de la línea 1» no
es un número: ''` y solo arriba del formulario. Ahora dice «Falta el precio unitario de la línea 1.» y el aviso se
repite junto a los botones. 1 prueba más en `tests/test_oferta_panel.py`.

## 11. Construido: la respuesta técnica, primera parte sin IA (2026-11-09) — reemplazada por la sección 12

> El 2026-11-10 la respuesta técnica (con su formulario, su PDF y el campo «Sección del pliego») se quitó: la oferta
> completa de la sección 12 la reemplaza, con el pliego respondido sección por sección. Lo de abajo queda como
> historia de la decisión.

Pedido de Ivania: hacer la etapa 2 en dos partes. **Primera parte (hecha), sin IA:** en el cartel, «Respuesta técnica»
(junto a «Oferta económica»; mismo acceso: su encargado y los administradores). Es la **matriz de cumplimiento**: una
fila por especificación con «el cartel pide · dónde lo dice · Hermatix ofrece · documento que lo prueba · ¿Cumple?»
(Cumple · No cumple · Revisar · Sin marcar) y una nota.

- **Filas iniciales:** si el cartel tiene resumen con IA, sus especificaciones clave, marcadas «del resumen con IA:
  revisar contra el pliego» (son solo las que más pesan); si no, una fila por línea del cartel. Todas empiezan sin
  marcar. La persona agrega las demás del pliego.
- **Documento que lo prueba:** sugiere los documentos del perfil y los archivos del expediente; se puede escribir otro.
- **PDF** (`app/respuesta_tecnica.py`, plantilla `respuesta_tecnica.html`): encabezado, conteo por estado, la tabla y
  la firma. «No cumple» y «Sin marcar» salen tal cual: no se esconde ninguna fila. **Desde el 2026-11-10 (pedido de
  Ivania), con el mismo diseño que la oferta económica:** membrete de Hermatix en cada hoja, Times New Roman, fecha y
  destinatario en negrita, título centrado («Respuesta Técnica · MATRIZ DE CUMPLIMIENTO», objeto y procedimiento),
  tabla con encabezado azul y firma centrada con la cédula jurídica de `config/oferta.yaml`. Cuando llegue la oferta
  técnica de Tarrazú, se compara con ella.
- **Comparada con la respuesta que presentó Hermatix en Tarrazú (2026-11-10).** Ivania pegó en `data/ofertas/` (fuera
  de Git) los documentos de la oferta. La respuesta técnica es «Contratación Tarrazu Se Cumple» (Word): **no es una
  tabla**, sino el pliego **punto por punto**, con cada sección en negrita (Objeto, Plazo, Forma de pago,
  Admisibilidad, Garantía, Especificaciones técnicas, Aspectos de evaluación…). Bajo cada punto va «Respuesta Hermatix:
  Se entiende, se acepta y se cumple.», o «Se entiende y se acepta.» cuando solo se aporta documentación. El PDF de
  la app pasa a esa forma: cada fila tiene **«Sección del pliego»** (campo nuevo, sin migración: va en el borrador),
  las filas se agrupan por sección y «Cumple» escribe esa frase, seguida de lo que ofrece Hermatix y el documento que
  lo prueba. «No cumple», «Revisar» y «Sin marcar» salen tal cual y en rojo, para que nadie firme sin verlos. El
  formulario del panel sigue siendo la matriz. El PDF de 33 páginas con el nombre del objeto es una copia del pliego.
  «Propuesta Proyecto…» es una cotización comercial con precios (solo en local). El ZIP trae también documentos
  personales (planillas, CV, declaraciones juradas, personería) que **no se leyeron**.
- Borrador por cartel (migración **0042**); el historial anota quién guardó y quién generó el PDF. Pruebas en
  `tests/test_respuesta_tecnica.py` (datos SINTÉTICOS).

**Segunda parte:** reemplazada por la sección 12 (el formulario y su PDF se quitaron el 2026-11-10).

## 12. Construido: la oferta completa con un botón, como la de NAVSAT (2026-11-10)

**Pedido de Oscar (comunicado por Ivania):** que la oferta sea como la de **NAVSAT** (IAFA, 2026LD-000056-0010400001,
ganada por esa empresa; en `data/ofertas/`, fuera de Git; no se copió nada de sus precios ni de sus datos), que los
documentos subidos en el asistente vayan **adjuntos** y que **no haya formulario**: un botón y la oferta sale.

**Cómo es la de NAVSAT:** un solo PDF. Portada (institución, OFERTA, tipo y número de procedimiento, objeto, oferente y
cédula jurídica) · el **pliego completo copiado** sección por sección, con «Respuesta Sección 01 – Llamado a Cotizar ·
Entendemos, aceptamos y cumplimos con lo requerido» en cursiva al final de cada una · «Listado de Anexos» en 4 grupos
(1 Oferta económica · 2 Documentación legal · 3 Propuesta técnica · 4 Certificaciones empresariales) · cada anexo con
su página de título y el documento.

**Lo construido** (`app/propuesta.py`, `app/ai/oferta.py`, plantillas `propuesta.html` y `propuesta_anexos.html`,
migración **0043**): en el cartel, el botón **«Oferta»** (solo para quien entra al expediente) arma ese PDF, lo
descarga y guarda una copia en `EXPORTS_DIR/ofertas/<procedimiento>/oferta_<fecha>.pdf` (nunca sobrescribe).
- **El pliego:** lo copia la app del texto original (DOC del pliego y especificaciones). La IA solo marca dónde empieza
  cada sección y si la respuesta es «cumple» o «acepta» (`DECISION_IA.md` §9). Con la IA apagada, una sola sección.
- **Las respuestas** (decisión de Ivania): cada requisito del asistente va a la sección del pliego donde lo cita; si
  algo no cumple, falta o hay que revisar, esa sección **no dice «cumplimos»**: sale en rojo con lo que falta, y la
  portada dice «BORRADOR: hay N puntos sin resolver. No firmar ni subir a SICOP todavía», con la lista.
- **Los precios** (decisión de Ivania): salen de **`config/tarifario.yaml`**, que llena y aprueba Oscar una vez, por
  producto de Hermatix (el de la familia con mejor encaje del cartel). Cambia la regla 3: el precio lo aprueba Oscar
  en el tarifario. Sin tarifa sale «PRECIO PENDIENTE» en rojo, sin total ni monto en letras. El anexo 1.1 es la oferta
  económica de la sección 10 (diseño de Tarrazú), calculada por la app.
- **Los anexos:** los archivos que se subieron en el asistente (o el documento vigente del perfil, si se confirmó desde
  el perfil), agrupados por el tipo del elemento del perfil. Los PDF se pegan tal cual; las imágenes, en una página.
  Los que faltan quedan en el listado como «PENDIENTE». Cada documento adjuntado queda en el historial
  («adjuntar_documento_oferta»), y se ve también en los accesos del perfil. Nunca van a la IA.
- **Representante legal:** sus datos están ahora en `config/oferta.yaml` (vacíos hasta que Oscar los llene: mientras
  tanto, pendiente en la portada).
- **Se quitaron** los formularios «Oferta económica» y «Respuesta técnica» con su PDF (y `app/respuesta_tecnica.py`).
  Los borradores ya guardados (tablas 0041 y 0042) quedan en la base sin usarse. Sigue el comando
  `python -m app.cli oferta economica --datos OFERTA.yaml`.
- **Siempre pendiente por ahora:** la ficha técnica del equipo ofertado (anexo 3), hasta que Oscar decida cómo se
  elige el equipo de cada cartel con las fichas Hero.
- Pruebas: `tests/test_propuesta.py` (datos SINTÉTICOS, IA SIMULADA).

**Pendiente · Oscar:** llenar `config/tarifario.yaml` y los datos del representante en `config/oferta.yaml`; decidir
cómo se elige la ficha técnica de cada cartel.
