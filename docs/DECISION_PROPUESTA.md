# Decisión: que la app arme la oferta de un cartel para presentarla en SICOP

**BORRADOR para Oscar. Redactado por Ivania con Claude el 2026-11-09. Todavía no está aprobado.**
Lo marcado **[por decidir · Oscar]** no se llena hasta que él lo diga. Mientras este documento no esté aceptado,
no se construye nada de esta ampliación.

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
   descargable. Después del concurso se registra el resultado (ganada o perdida y el puntaje) para aprender.

## 4. Lo que se necesita para empezar

| Qué | Para qué | ¿Ya está? | Quién lo entrega |
|---|---|---|---|
| **Una o dos ofertas reales ya presentadas en SICOP**, una ganada y una perdida, con capturas de cada pantalla del formulario de oferta | Conocer los campos y adjuntos que pide SICOP sin inventarlos | **Parcial:** pliego y oferta económica de una ganada (Tarrazú, 2025; sección 9). Faltan la oferta técnica, una perdida y las capturas | Oscar |
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

- [ ] Oscar leyó este documento y decide la sección 6 (fecha: ____).
- [ ] Llegaron las ofertas de ejemplo de la sección 4 (sin ellas no se empieza la etapa 1).
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
equipo y de las funciones ADAS y DSM · desglose del precio en 4 rubros (montos y porcentajes) · firma.

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

**Falta** para seguir: la oferta técnica y sus anexos, el acta de adjudicación con los puntajes, una oferta
perdida y las capturas de SICOP.
