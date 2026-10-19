CONFIDENCIAL

H E R M AT I X M 2 M C O M M U N I C AT I O N S . R . L .

C O N F I D E N C I A L

SICOP CONNECT

Guía de aprendizaje y ejecución del proyecto

Práctica profesional asistida por inteligencia artificial

Participante Ivania Jazmín Reyes Escoto — pasante de Desarrollo Web

Líder del proyecto Oscar, Gerente General de Hermatix

Periodo 5 al 30 de octubre de 2026 · 20 jornadas · 160 horas

Contexto académico Primer bloque de una práctica de 320 horas

Herramienta de IA Claude Pro con Claude Code

Entorno Windows (desarrollo) · Mac (despliegue) · servidor Linux de Hermatix

Versión 3.1 — 4 de octubre de 2026

Clasificación CONFIDENCIAL — Uso interno de Hermatix

AVISO DE CONFIDENCIALIDAD. Este documento contiene información confidencial y de propiedad de Hermatix M2M

Communication S.R.L., incluidos planes comerciales, criterios de evaluación de oportunidades, información de infraestructura

y procedimientos internos. Se entrega exclusivamente a las personas autorizadas para el desarrollo del proyecto SICOP

CONNECT. Queda prohibida su reproducción, distribución o divulgación, total o parcial, a terceros sin autorización escrita de

Hermatix. Si usted recibió este documento por error, notifíquelo a Hermatix y elimínelo.

CONFIDENCIALContenido

Antes de empezar: cómo usar esta guía ........................................................................................................................... 3

PARTE I · ENTENDER ......................................................................................................................................4

1\. El problema: por qué existe este proyecto ................................................................................................................... 4

2\. La solución: SICOP CONNECT ........................................................................................................................................ 5

3\. Por qué existe cada pieza.............................................................................................................................................. 6

4\. Conceptos clave explicados .......................................................................................................................................... 7

5\. Tu asistente: qué es Claude y cómo calcular su tiempo real....................................................................................... 10

PARTE II · CÓMO TRABAJAR ........................................................................................................................12

6\. El método para resolver problemas............................................................................................................................ 12

7\. Cómo trabajar con Claude Code ................................................................................................................................. 13

8\. La rutina de trabajo..................................................................................................................................................... 16

9\. Cómo demostrar que algo funciona ........................................................................................................................... 17

PARTE III · EL RECORRIDO: 20 LECCIONES.....................................................................................................18

10\. Mapa del recorrido ................................................................................................................................................... 18

11\. Semana 1 — Piloto local de punta a punta............................................................................................................... 20

12\. Semana 2 — Piloto en producción............................................................................................................................ 31

13\. Semana 3 — Ampliaciones de valor.......................................................................................................................... 39

14\. Semana 4 — Operación resiliente y transferencia.................................................................................................... 43

PARTE IV · REFERENCIA TÉCNICA .................................................................................................................47

15\. Arquitectura del piloto.............................................................................................................................................. 47

16\. La fuente: SICOP, datos y reglas comerciales............................................................................................................ 49

17\. Despliegue en el servidor de Hermatix..................................................................................................................... 52

18\. Pruebas y criterios de aceptación técnica................................................................................................................. 56

PARTE V · GESTIÓN DEL PROYECTO..............................................................................................................58

19\. Alcance, roles y dependencias.................................................................................................................................. 58

20\. Seguimiento: estado, bitácora y retos de comprensión............................................................................................ 60

21\. Entregables, presentación e informe final ................................................................................................................ 61

22\. Métricas del proyecto............................................................................................................................................... 63

23\. Riesgos, contingencias y continuidad ....................................................................................................................... 63

24\. Solución de problemas, aprendizaje y fuentes......................................................................................................... 64

ANEXOS ......................................................................................................................................................67

Anexo A. Modelo de estimación del tiempo de Claude.................................................................................................. 67

Anexo B. Competencias que habrás desarrollado .......................................................................................................... 68

Primera acción: lunes 5 de octubre, 08:00 ..................................................................................................................... 69

SICOP CONNECT · Guía de aprendizaje y ejecución C O N F I D E N C I A L

Hermatix M2M Communication S.R.L. · Documento confidencial — uso interno. Prohibida su distribución sin autorización. Página 2 de 69

CONFIDENCIALAntes de empezar: cómo usar esta guía

Esta guía está escrita para que puedas entender el proyecto antes de hacerlo. No es una lista de comandos para

copiar: cada paso explica para qué existe, qué problema resuelve y cómo sabes que quedó bien. Si en algún

momento no entiendes por qué haces algo, detente y vuelve a la parte que lo explica; ese es el comportamiento

que se espera de una profesional.

La guía tiene cinco partes:

Parte Qué contiene Cuándo leerla

I. Entender (secciones 1–5) El problema de Hermatix, la solución, el porqué de cada pieza, los

conceptos y el papel de Claude

Completa, antes del día 1.

Toma unas 2 horas

II. Cómo trabajar (secciones

6–9)

El método para resolver problemas, cómo pedir trabajo a Claude,

la rutina diaria y cómo demostrar que algo funciona

Antes del día 1, y cada vez

que te sientas perdida

III. El recorrido (secciones

10–14)

20 lecciones, una por jornada, con objetivo, explicación, paso a

paso, encargo para Claude, comprobación y autoevaluación

Cada mañana, la lección del

día

IV. Referencia técnica

(secciones 15–18)

Arquitectura, datos de SICOP, despliegue en servidor y pruebas Cuando una lección te envíe

a ellas

V. Gestión del proyecto

(secciones 19–24 y anexos)

Roles, plantillas, entregables, métricas, riesgos, fuentes Oscar la usa para supervisar;

tú, para entregar

Para Oscar o la persona supervisora: las secciones 1, 5, 10, 19, 21 y 22 y el anexo A resumen el plan, los

compromisos de Hermatix y los criterios de aceptación.

Para Claude Code: el archivo CLAUDE.md (lección 1) y la sección que cada encargo indique. Claude no necesita leer

la guía completa.

Símbolos que verás:

Símbolo Significado

Objetivo o criterio de aceptación

Para qué sirve: la razón detrás del paso

Concepto que necesitas entender

Paso a paso

Encargo para Claude Code (texto para copiar)

Cómo compruebas que funcionó

Qué hacer si algo falla

Preguntas de autoevaluación

Estimación de tiempo

\[OSCAR] · \[CLAUDE] · \[TÚ] Quién realiza la acción

SICOP CONNECT · Guía de aprendizaje y ejecución C O N F I D E N C I A L

Hermatix M2M Communication S.R.L. · Documento confidencial — uso interno. Prohibida su distribución sin autorización. Página 3 de 69

CONFIDENCIALPARTE I · ENTENDER

1\. El problema: por qué existe este proyecto

1.1. Quién es Hermatix y qué vende

Hermatix es una empresa costarricense de tecnología para vehículos y operaciones. Sus soluciones principales son:

Producto Qué resuelve, en palabras simples

FleetMatix Saber dónde está cada vehículo de una flota, por dónde anduvo y cómo se usa (rastreo GPS)

Fenova IA Cámaras con inteligencia artificial dentro de los vehículos: graban, detectan distracción o fatiga del conductor y

alertan riesgos

PassengerIQ Contar automáticamente cuántos pasajeros suben y bajan de un bus

MoveOn Organizar el transporte de colaboradores de una empresa o institución

SmartTags Rastrear activos (equipos, contenedores) con etiquetas electrónicas

FleetRun Llevar el control del mantenimiento de una flota

Soluciones

IoT

Sensores que envían datos a distancia: temperatura, niveles, telemetría

Muchos de los clientes potenciales de estas soluciones son instituciones públicas: ministerios, municipalidades,

hospitales, empresas estatales, autoridades de transporte.

1.2. Cómo compra el Estado en Costa Rica

En Costa Rica, las instituciones públicas no pueden comprar a quien quieran: deben publicar lo que necesitan en un

sistema oficial para que cualquier empresa pueda ofertar. Ese sistema se llama SICOP (Sistema Integrado de

Compras Públicas).

Cada compra publicada se llama cartel (o pliego). Un cartel dice qué institución compra, qué necesita, y hasta qué

fecha recibe ofertas. Dentro del cartel, las líneas detallan cada cosa que se pide: «línea 1: 40 dispositivos de rastreo

GPS; línea 2: servicio de monitoreo por 24 meses».

SICOP publica esta información como datos abiertos: cualquiera puede solicitar archivos con los carteles y sus

líneas.

1.3. El problema concreto

Hoy, para enterarse de una compra que le interesa, alguien de Hermatix tendría que revisar SICOP manualmente,

todos los días. Eso tiene tres problemas:

1\. Consume tiempo. Se publican muchas compras; la mayoría no tiene nada que ver con Hermatix.

SICOP CONNECT · Guía de aprendizaje y ejecución C O N F I D E N C I A L

Hermatix M2M Communication S.R.L. · Documento confidencial — uso interno. Prohibida su distribución sin autorización. Página 4 de 69

CONFIDENCIALSe pierden oportunidades. Muchas compras tienen títulos genéricos («Contratación de servicios para la flota

institucional») y la necesidad real solo aparece en las líneas o en códigos. Leyendo títulos, se escapan.

Se llega tarde. Un cartel tiene una fecha de cierre. Si Hermatix lo descubre a dos días de cerrar, ya no le da

tiempo de preparar una buena oferta.

1.4. El objetivo, en una oración

Que el equipo comercial de Hermatix reciba cada mañana, sin buscar, las compras públicas que

probablemente le interesan, con la razón de por qué le interesan, a tiempo para decidir si participa.

Todo lo que construirás existe para cumplir esa oración. Cuando dudes si algo es importante, pregúntate: ¿esto

ayuda a que el encargado reciba oportunidades correctas, explicadas y a tiempo?

2\. La solución: SICOP CONNECT

2.1. Qué hace la aplicación

SICOP CONNECT es una aplicación web que:

Recibe los archivos de datos abiertos de SICOP.

Guarda su información de forma ordenada y sin duplicados.

Evalúa cada compra con reglas que buscan señales del negocio de Hermatix («rastreo vehicular», «conteo de

pasajeros», «cámaras a bordo»).

Muestra las compras candidatas en un panel web, con la frase exacta que causó la coincidencia.

Registra la decisión de una persona: «nos interesa», «no nos interesa», «hay que revisar requisitos».

Avisa por correo al encargado comercial con un resumen.

Funciona sola en un servidor de Hermatix, todos los días, aunque tu computadora esté apagada.

2.2. El viaje de un dato: la historia completa en un ejemplo

La mejor forma de entender el sistema es seguir un caso. Imagina que el Ministerio X publica una compra:

Cartel 2026LE-000123 · Ministerio X · Cierre: 30 de octubre, 10:00

Título: "Contratación de servicios para la flota institucional"

Línea 1: "Servicio de monitoreo satelital de vehículos, 24 meses" cantidad: 85

Línea 2: "Cámaras vehiculares con grabación a bordo" cantidad: 20

Este es su recorrido por SICOP CONNECT, estación por estación:

Estación Qué ocurre Pregunta que resuelve

1\. Obtención Alguien de Hermatix (o un proceso automático, si se logra) descarga de SICOP el archivo

de carteles y el de líneas, y los deja en una carpeta de entrada

¿De dónde salen los

datos?

2\.

3\.

1\.

2\.

3\.

4\.

5\.

6\.

7\.

SICOP CONNECT · Guía de aprendizaje y ejecución C O N F I D E N C I A L

Hermatix M2M Communication S.R.L. · Documento confidencial — uso interno. Prohibida su distribución sin autorización. Página 5 de 69

CONFIDENCIALEstación Qué ocurre Pregunta que resuelve

2\. Importación El programa lee el archivo, revisa que cada fila sea válida, guarda el cartel y sus líneas

en la base de datos, y guarda una copia del archivo original

¿Están los datos

completos y sin

errores?

3\. Relación El programa une el cartel con sus dos líneas y con el nombre del Ministerio ¿Qué se compra

realmente y quién lo

compra?

4\. Evaluación Las reglas encuentran «monitoreo satelital de vehículos» (familia GPS → FleetMatix) y

«cámaras vehiculares» (familia videotelemática → Fenova IA). Resultado: prioridad

Alta, con esas dos frases como evidencia

¿Le interesa a

Hermatix y por qué?

5\. Panel El cartel aparece en la lista de oportunidades, ordenado por fecha de cierre, con las

frases resaltadas

¿Cómo lo ve una

persona?

6\. Revisión

humana

El encargado lo abre, lee y marca «Interesa — revisar requisitos», con un comentario ¿Quién decide?

7\. Aviso Al día siguiente, a las 07:00, el encargado recibe un correo con este cartel en la lista de

nuevas oportunidades

¿Cómo se entera a

tiempo?

Fíjate en algo importante: el título solo («servicios para la flota institucional») no habría bastado. La oportunidad

se detectó gracias a las líneas. Por eso el proyecto da tanta importancia a importar líneas y catálogo correctamente.

2.3. Lo que la aplicación NO hace (y por qué)

No hace Por qué

Decidir si Hermatix participa Esa es una decisión comercial y legal que requiere leer el pliego completo. La app sugiere;

una persona decide

Garantizar que Hermatix cumple

los requisitos

«Alta coincidencia» significa «parece del negocio de Hermatix», no «Hermatix puede ganar»

Usar inteligencia artificial para

evaluar

Las reglas son explicables, gratuitas de ejecutar y suficientes para el piloto. La IA en la app es

una mejora futura con costo aparte

Saltarse controles de SICOP Si SICOP exige un código por correo para descargar, no se elude. Se trabaja en modo asistido

3\. Por qué existe cada pieza

Un error común al aprender a programar es construir piezas sin saber qué problema resuelven. Esta tabla

responde, para cada parte del sistema, qué pasaría si no existiera. Si puedes explicar esta tabla con tus palabras,

entiendes el diseño.

Pieza Para qué sirve Qué pasaría sin ella

Copia del archivo original (con

su huella o hash)

Poder demostrar de dónde salió

cada dato y volver a procesarlo

Si hay un error, no sabrías si vino de SICOP o de tu

programa

SICOP CONNECT · Guía de aprendizaje y ejecución C O N F I D E N C I A L

Hermatix M2M Communication S.R.L. · Documento confidencial — uso interno. Prohibida su distribución sin autorización. Página 6 de 69

CONFIDENCIALPieza Para qué sirve Qué pasaría sin ella

Identificadores guardados

como texto

Conservar exactos los códigos de 24

dígitos

Un código como 000123… se convertiría en un número,

perdería ceros y dejaría de coincidir con sus líneas

Importación idempotente

(repetible sin duplicar)

Poder cargar el mismo archivo dos

veces sin daño

Cada recarga duplicaría compras y avisos; el encargado

recibiría lo mismo varias veces

Registro de filas rechazadas Saber qué datos no se pudieron

cargar y por qué

Los errores pasarían en silencio y perderías

oportunidades sin saberlo

Relación cartel–líneas–

catálogo

Ver qué se compra realmente Solo verías títulos genéricos y te perderías casos como el

del ejemplo 2.2

Reglas con evidencia Explicar por qué algo coincide El encargado no confiaría en una alerta sin saber de

dónde salió

Exclusiones en las reglas Evitar falsos positivos («GPS

topográfico», «cámaras del edificio»)

El correo se llenaría de ruido y la gente dejaría de leerlo

Revisión humana persistente Guardar decisiones y comentarios Al actualizar datos se borrarían las decisiones y habría

que revisar todo otra vez

Autenticación del panel Que solo personal autorizado vea y

modifique

Cualquiera en Internet podría ver o alterar las decisiones

comerciales

Outbox con deduplicación Recordar qué aviso se envió a quién Cada ciclo reenviaría todo; o, al fallar un envío, no sabrías

si llegó

Modo dry-run (simulación) Ver qué se enviaría sin enviarlo Las pruebas mandarían correos reales por error

Registro de cobertura de la

fuente

Distinguir «no hubo compras» de «la

descarga falló»

Un fallo parecería un día sin oportunidades: el peor error

posible

Servidor + programador

(systemd)

Que todo corra solo cada día Dependería de que tu computadora y tu sesión estén

abiertas

Respaldo y restauración

probados

Recuperarse si se daña la base Una falla del disco borraría meses de decisiones

Documentación Que Hermatix lo opere sin ti El proyecto moriría al terminar tu práctica

4\. Conceptos clave explicados

No necesitas dominar todo esto el día 1. Cada lección te indica qué concepto usar ese día. Vuelve aquí cuando lo

necesites.

4.1. Herramientas de trabajo

Concepto Explicación Analogía

Terminal Ventana donde escribes órdenes a la

computadora en texto

Hablarle a la computadora en lugar de hacer clic

SICOP CONNECT · Guía de aprendizaje y ejecución C O N F I D E N C I A L

Hermatix M2M Communication S.R.L. · Documento confidencial — uso interno. Prohibida su distribución sin autorización. Página 7 de 69

CONFIDENCIALConcepto Explicación Analogía

Git / repositorio Sistema que guarda el historial de cambios

del código

Un «control de versiones» como el historial de Google Docs,

pero con puntos de guardado que tú nombras

Commit Un punto de guardado con nombre en Git Una foto del proyecto en un momento en que funciona

Entorno virtual

( .venv )

Carpeta con las bibliotecas de Python de

este proyecto, separadas del resto

Una caja de herramientas propia del proyecto, para no

mezclarla con la de otros

Variable de

entorno / .env

Configuración que vive fuera del código

(rutas, horarios, contraseñas)

Las llaves de la casa no se pegan en la puerta: se guardan

aparte

Claude Code Asistente de IA que trabaja dentro de tu

carpeta: lee, edita y ejecuta

Un programador muy rápido que necesita instrucciones

claras y supervisión

4.2. La aplicación web

Concepto Explicación Analogía

Backend La parte del programa que procesa datos y

responde al navegador

La cocina de un restaurante

FastAPI Biblioteca de Python para construir el backend El equipamiento de la cocina

Ruta web ( /health , /

oportunidades )

Una dirección dentro de tu aplicación Cada plato del menú

Plantilla (Jinja2) HTML con espacios que se llenan con datos Un formulario impreso que se rellena

Sesión / cookie La forma en que el sitio recuerda que ya

iniciaste sesión

La pulsera de un evento: entraste una vez

y te reconocen

CSRF Protección para que otro sitio no envíe

formularios en tu nombre

Pedir la firma de la persona, no solo su

pulsera

Hash de contraseña Transformación irreversible: se guarda la huella,

no la contraseña

Guardar la huella digital, no el dedo

4.3. Datos

Concepto Explicación Analogía

Base de datos

(SQLite)

Archivo que guarda datos en tablas relacionadas Un archivero con carpetas ordenadas

Tabla, fila,

columna

Una tabla es un tipo de cosa (carteles); cada fila es una

cosa; cada columna, un dato

Una hoja de cálculo bien disciplinada

Clave / relación Un dato que identifica una fila y permite unirla con

otra tabla

El número de cédula que une a una persona con sus

trámites

Migración Cambio controlado y versionado de la estructura de

las tablas

Planos de remodelación numerados: se aplican en

orden y quedan registrados

SICOP CONNECT · Guía de aprendizaje y ejecución C O N F I D E N C I A L

Hermatix M2M Communication S.R.L. · Documento confidencial — uso interno. Prohibida su distribución sin autorización. Página 8 de 69

CONFIDENCIALConcepto Explicación Analogía

CSV Archivo de texto con datos separados por comas o

punto y coma

Una tabla escrita en texto plano

Idempotencia Repetir una operación da el mismo resultado que

hacerla una vez

Presionar el botón del ascensor diez veces no llama

diez ascensores

Hash de archivo Huella única del contenido; si cambia un carácter,

cambia la huella

El código de barras de un producto

Decimal Tipo de número exacto para dinero Contar monedas, no estimar a ojo

4.4. Evaluación y calidad

Concepto Explicación

Regla Instrucción del tipo «si aparece rastreo vehicular, es familia GPS»

Señal / exclusión Palabras que suman a una familia / palabras que la anulan por contexto («topográfico» anula

«GPS»)

Falso positivo La app alerta algo que no interesa (GPS para topografía)

Falso negativo La app no alerta algo que sí interesaba

Golden set (conjunto de

prueba)

Lista de casos reales que Oscar etiquetó a mano; sirve para medir si las reglas aciertan

Precisión De todo lo que la app alertó, ¿cuánto interesaba de verdad?

Cobertura De todo lo que interesaba, ¿cuánto alertó la app?

4.5. Operación

Concepto Explicación Analogía

Servidor Computadora encendida siempre, donde vive la

aplicación

El local del restaurante, abierto todos los días

SSH Conexión segura para escribir órdenes en otra

computadora

Un control remoto cifrado

systemd: servicio y

timer

El servicio mantiene el panel encendido; el timer ejecuta

el ciclo a una hora

El encargado que abre el local / la alarma que

suena a las 7:00

Dry-run Ejecutar como simulación, sin efectos reales Ensayo general sin público

Respaldo /

restauración

Copia de seguridad / volver a usar esa copia Un respaldo solo vale si alguna vez probaste

restaurarlo

HTTPS Conexión cifrada entre el navegador y el servidor Un sobre sellado en lugar de una postal

SICOP CONNECT · Guía de aprendizaje y ejecución C O N F I D E N C I A L

Hermatix M2M Communication S.R.L. · Documento confidencial — uso interno. Prohibida su distribución sin autorización. Página 9 de 69

CONFIDENCIAL5. Tu asistente: qué es Claude y cómo calcular su tiempo real

5.1. Qué es y qué no es Claude en este proyecto

Claude sí Claude no

Escribe código en minutos a partir de una buena

especificación

Sabe qué necesita Hermatix si no se lo dices

Ejecuta pruebas y corrige sus propios errores Garantiza que su código funcione con los datos reales: eso lo compruebas

tú

Explica conceptos con ejemplos Reemplaza tu comprensión: si no puedes explicar un cambio, no está

terminado

Ayuda a diagnosticar errores Accede al servidor, al correo de Hermatix ni a contraseñas (y nunca debe)

Redacta documentación Decide alcance, prioridades o si algo «ya funciona»: eso lo deciden la

evidencia y Oscar

Piensa en Claude como un colega muy rápido y muy capaz, pero que llegó hoy a la empresa: necesita contexto,

instrucciones claras y revisión.

5.2. Los tres relojes del proyecto

Las estimaciones tradicionales («dos semanas para el importador») suponen que una persona escribe el código.

Con Claude Code, el tiempo se reparte en tres relojes distintos:

Reloj Qué mide Cuánto pesa con Claude

Reloj Claude Tiempo en que Claude lee, escribe, prueba y corrige Minutos por funcionalidad (típico: 5–40

min)

Reloj humano Especificar, revisar el cambio, probar con datos reales, entender,

documentar

La mayor parte de tu jornada (≈ 70–80

%)

Reloj

calendario

Esperas externas: archivo de SICOP, ejemplos de Oscar, servidor,

correo

Claude no lo acelera. Es el principal

riesgo

Regla: una tarea termina cuando termina el reloj más lento. El piloto completo, que un junior sin IA haría en 8–11

semanas, son unas 4–6 horas de trabajo activo de Claude; lo que lo convierte en dos semanas es tu trabajo de

especificar, verificar y aprender, que no se debe recortar. El detalle por componente está en el anexo A.

5.3. Cuánta capacidad tiene tu cuenta Pro

El uso se mide en ventanas de 5 horas que empiezan con tu primer mensaje, más un límite semanal.

Claude web, Claude Desktop y Claude Code comparten la misma bolsa: chatear en el navegador gasta lo

mismo que programar.

Reportes independientes sitúan a Pro en unas 10 a 45 interacciones de Claude Code por ventana, según el

tamaño del contexto. Los límites cambian; /usage dentro de Claude Code es la fuente de verdad.

•

•

•

SICOP CONNECT · Guía de aprendizaje y ejecución C O N F I D E N C I A L

Hermatix M2M Communication S.R.L. · Documento confidencial — uso interno. Prohibida su distribución sin autorización. Página 10 de 69

CONFIDENCIALPara planificar suponemos, de forma conservadora, 2 ventanas por jornada (mañana y tarde) con 15–25 encargos

útiles cada una, y planificamos usar solo un 55 % de esa capacidad. El resto es reserva para errores y explicaciones.

Semana Encargos planificados Ventanas usadas (de 10)

1 · Piloto local 45–60 6–8

2 · Producción 35–50 5–7

3 · Ampliaciones 50–70 7–9

4 · Operación y entrega 25–40 4–6

Mes ≈ 155–220 —

No actives uso adicional pagado. Si se agota una ventana, sigues con la lista de trabajo sin Claude (sección 7.6).

Cada día anotarás en la bitácora cuántos encargos usaste y el % de ventana. Así, al final del mes Hermatix tendrá

datos propios de cuánto rinde Pro en un proyecto real.

SICOP CONNECT · Guía de aprendizaje y ejecución C O N F I D E N C I A L

Hermatix M2M Communication S.R.L. · Documento confidencial — uso interno. Prohibida su distribución sin autorización. Página 11 de 69

CONFIDENCIALPARTE II · CÓMO TRABAJAR

6\. El método para resolver problemas

Este proyecto no se resuelve sabiendo comandos, sino aplicando un método. Es el mismo que usan los equipos

profesionales y te servirá en cualquier trabajo.

6.1. Los seis pasos para construir cualquier funcionalidad

Paso Qué haces Pregunta guía Ejemplo (importador de carteles)

1\. Entender Lees la lección y relacionas la tarea con el

objetivo de la sección 1.4

¿Qué problema resuelve esto y

para quién?

«Sin importar carteles no hay nada

que evaluar»

2\. Dividir Partes la tarea en piezas que se puedan

comprobar por separado

¿Cuál es la pieza más pequeña

que puedo probar?

Leer el archivo → validar filas →

guardar → evitar duplicados

3\.

Especificar

Escribes qué debe ocurrir y cómo lo vas a

comprobar, antes de construir

¿Cómo sabré que está bien? «El mismo archivo dos veces no

crea filas nuevas»

4\. Construir Das el encargo a Claude con esa

especificación

¿Le di a Claude todo lo que

necesita?

Encargo con el formato de la

sección 7.3

5\. Verificar Ejecutas, miras resultados reales, lees el

cambio

¿Lo comprobé yo con datos

reales, o solo lo dijo Claude?

Importar el CSV real dos veces y

contar filas

6\. Registrar Guardas el avance y escribes lo aprendido ¿Podría otra persona continuar

desde aquí?

Commit + 3 líneas en la bitácora

El paso que más se salta, y el que más problemas causa, es el 3. Si no puedes escribir cómo vas a comprobar algo,

todavía no entiendes qué estás construyendo.

6.2. Cómo encontrar y corregir un error (depuración)

Cuando algo falla, no le pidas a Claude «arréglalo» a ciegas. Sigue el método científico:

Paso Qué haces Ejemplo

1\. Reproducir Consigue que el error ocurra siempre de la misma

forma

«Al importar carteles\_oct.csv , la fila 57 se

rechaza»

2\. Observar Lee el mensaje de error completo; identifica archivo

y línea

«Dice: fecha inválida '05/10/2026 08:30:00 a. m.'»

3\. Aislar Reduce el caso al mínimo: una fila, un dato Copiar solo esa fila a un archivo de prueba

SICOP CONNECT · Guía de aprendizaje y ejecución C O N F I D E N C I A L

Hermatix M2M Communication S.R.L. · Documento confidencial — uso interno. Prohibida su distribución sin autorización. Página 12 de 69

CONFIDENCIALPaso Qué haces Ejemplo

4\. Formular una

hipótesis

Explica qué crees que pasa «El programa no entiende el formato 'a. m.'»

5\. Probar la

hipótesis

Cambia una sola cosa y vuelve a ejecutar Pedir a Claude que acepte ese formato, con una

prueba de esa fila

6\. Confirmar y

proteger

Verifica con el caso real y deja una prueba

automática para que no vuelva

La prueba queda en tests/

Si después de dos intentos el error sigue, detente: anota lo que sabes y llévalo a la reunión diaria. Insistir con

Claude sin una hipótesis nueva gasta capacidad y no aporta.

6.3. Cuándo pedir ayuda a una persona

Pide ayuda a Oscar o a la persona supervisora, sin esperar, cuando:

La tarea depende de algo que no controlas (archivo, acceso, contraseña, decisión comercial).

Llevas más de 45 minutos atascada en el mismo error con el método 6.2.

No entiendes para qué sirve lo que estás haciendo.

Algo parece riesgoso (borrar datos, enviar correos reales, tocar el servidor).

Pedir ayuda a tiempo es una competencia profesional, no una debilidad. Llega con: qué intentabas, qué pasó, qué

probaste y qué hipótesis tienes.

7\. Cómo trabajar con Claude Code

7.1. El ciclo de cada ventana

La regla de oro: Claude no te espera a ti y tú no esperas a Claude. Mientras Claude ejecuta un encargo (5–15

minutos), tú preparas datos de prueba, lees sobre el concepto nuevo o redactas el siguiente encargo.

Momento Tú Claude

Antes de abrir

Claude

Lees la lección, preparas datos, escribes el encargo —

Encargo enviado Lees la documentación del concepto del día Lee archivos, escribe código, ejecuta

pruebas

Resultado recibido Lees el resumen y el cambio ( git diff ), pruebas con datos

reales

—

Si falla Aplicas el método 6.2 y das un encargo de corrección concreto Corrige

Si pasa Commit, bitácora, explicas en 3 líneas —

•

•

•

•

SICOP CONNECT · Guía de aprendizaje y ejecución C O N F I D E N C I A L

Hermatix M2M Communication S.R.L. · Documento confidencial — uso interno. Prohibida su distribución sin autorización. Página 13 de 69

CONFIDENCIAL7.2. El tamaño correcto de un encargo

Tamaño Ejemplo Resultado

Demasiado

pequeño

«Agrega un campo», luego «ahora la prueba», luego «ahora el

README»

Muchas interacciones; cada una recarga el

contexto y gasta capacidad

Correcto «Implementa el importador de líneas con su migración,

pruebas y documentación; criterio: …»

1–2 interacciones; resultado completo y

verificable

Demasiado

grande

«Construye el panel, el correo y el despliegue» Código que nadie entiende y que no se puede

verificar

Un buen encargo equivale a una funcionalidad que puedes comprobar en menos de una hora.

7.3. Cómo escribir un encargo

Todos los encargos de las lecciones siguen esta estructura. Úsala para cualquier encargo nuevo:

CONTEXTO: Lee CLAUDE.md, la sección X de la guía y docs/ESTADO\_PROYECTO.md.

TAREA: \[una funcionalidad, en una oración].

ALCANCE: qué archivos puedes tocar y qué NO debes tocar.

CRITERIO DE ACEPTACIÓN:

&#x20;- \[comprobación observable 1]

&#x20;- \[comprobación observable 2]

VERIFICA: ejecuta \[pruebas o comando] y muéstrame la salida real.

CIERRE: actualiza ESTADO\_PROYECTO.md; resume en ≤ 8 líneas; explícame el

concepto nuevo con un ejemplo corto.

Comparación:

&#x20;Encargo débil Encargo profesional

«Haz que

importe el CSV»

«Implementa import --report carteles según MAPEO\_DATOS.md. Criterio: IDs de 24 dígitos se

conservan; fila inválida se rechaza con motivo; el mismo archivo dos veces no duplica. Ejecuta pytest y

muéstrame la salida.»

«No funciona,

arréglalo»

«Al ejecutar import --path data/incoming/carteles.csv obtengo este error: \[traza sin secretos].

Revisa solo app/importers/carteles.py . Propón la causa, aplica la corrección mínima y agrega una

prueba con esta fila.»

«Explícame

FastAPI»

«Explícame, usando nuestro /health , qué hace una ruta de FastAPI. Máximo 10 líneas. No modifiques

código.»

7.4. Técnicas para que la capacidad alcance

Técnica Por qué ahorra Cómo

Modo plan para funcionalidades

nuevas

Corriges el rumbo antes de que

escriba código

Shift+Tab hasta el modo plan; revisas; apruebas

/clear al cambiar de tarea El contexto viejo se reenvía en

cada interacción

Antes, confirma que ESTADO\_PROYECTO.md está al día

SICOP CONNECT · Guía de aprendizaje y ejecución C O N F I D E N C I A L

Hermatix M2M Communication S.R.L. · Documento confidencial — uso interno. Prohibida su distribución sin autorización. Página 14 de 69

CONFIDENCIALTécnica Por qué ahorra Cómo

/compact en tareas largas Resume el historial Si /context muestra mucho contexto cargado

No pegar archivos grandes Un CSV de miles de filas agota la

ventana

Encabezados + 5 filas, o archivos en tests/fixtures/

Errores cortos y exactos Diagnóstico directo Solo la traza relevante, sin contraseñas

Que Claude ejecute las pruebas Evita idas y vueltas Siempre «ejecuta y muéstrame la salida»

Modelo por defecto Los modelos más potentes gastan

más

Usa el de propósito general de /model ; el más potente

solo para un bloqueo

Chat web solo para preguntas

cortas

Comparte la misma bolsa Nada de pegar el proyecto en el navegador

Sin subagentes ni

investigaciones amplias

Multiplican el consumo Este piloto no los necesita

7.5. Ritual diario de capacidad

08:15 — /usage : anota % de ventana y de semana en la bitácora.

11:30 — Si la ventana A va por debajo del 70 %, aprovecha un encargo pendiente: la capacidad que no usas se

pierde al renovarse.

13:15 — Nueva ventana B.

16:30 — /usage final. Si la semana supera el 80 % antes del jueves, avísalo en la reunión diaria.

7.6. Trabajo sin Claude (cuando se agota la ventana)

Nunca hay tiempo muerto:

Probar el panel manualmente con datos reales y anotar defectos con pasos para reproducirlos.

Revisar candidatos y proponer cambios al archivo de reglas (se edita a mano).

Leer el cambio del día y escribir la explicación en tu bitácora.

Avanzar documentación ( OPERACION.md , ARQUITECTURA.md , presentación).

Preparar los encargos de la siguiente ventana con la plantilla 7.3.

Estudiar el material de la semana (sección 24.2).

7.7. Seguridad: lo que nunca haces

Nunca pegues en Claude ni subas a Git contraseñas, claves, códigos de validación de SICOP, enlaces privados de

descarga ni tu PDF personal.

Nunca dejes que Claude envíe correos reales, active tareas programadas o se conecte al servidor.

Nunca agregues a Git .env , .venv , data/ , bases de datos ni respaldos. Antes de cada commit: git status y

git diff .

Nunca presentes datos sintéticos o simulados como reales.

•

•

•

•

1\.

2\.

3\.

4\.

5\.

6\.

•

•

•

•

SICOP CONNECT · Guía de aprendizaje y ejecución C O N F I D E N C I A L

Hermatix M2M Communication S.R.L. · Documento confidencial — uso interno. Prohibida su distribución sin autorización. Página 15 de 69

CONFIDENCIAL7.8. La regla de comprensión

Antes de cada commit escribe en la bitácora tres líneas: qué cambió, cómo lo comprobaste y qué concepto

aprendiste. Si no puedes escribirlas, pide a Claude una explicación con un ejemplo antes de continuar. El avance no

se mide en código generado, sino en funcionalidades verificadas que puedes explicar y defender.

8\. La rutina de trabajo

8.1. Una jornada tipo

Hora Bloque Qué haces Por qué

08:00–

08:15

Reunión diaria Resultado de ayer, demo corta, bloqueo, tarea de hoy Detectar problemas a tiempo

08:15–

08:45

Preparar (sin

Claude)

/usage , leer la lección, preparar datos y escribir el

encargo

Un buen encargo ahorra horas

08:45–

12:00

Ventana A Encargo principal → verificar → corregir Bloque de mayor energía

12:00–

13:00

Almuerzo No se contabiliza —

13:00–

13:15

Ajustar (sin Claude) Revisar lo aprendido en la mañana y preparar el encargo de

la tarde

Corregir el rumbo

13:15–

16:00

Ventana B Segundo encargo o correcciones; pruebas con datos reales —

16:00–

17:00

Cierre Pruebas finales, commit, estado, bitácora, demo de mañana Que otra persona pueda

continuar

Los viernes, 16:00–16:30 es la revisión semanal. Las lecciones de la Parte III ajustan esta estructura cuando hay

sesiones con Oscar.

8.2. La reunión diaria de 15 minutos

Minutos Presentas Ejemplo

0–2 Resultado de ayer «Importo el CSV real; 3 filas rechazadas por fecha»

2–7 Una evidencia en vivo Ejecutar el importador y mostrar el resumen

7–11 Qué aprendiste y una decisión «Los códigos van como texto porque…»

11–15 Bloqueo y tarea de hoy «Necesito el catálogo; mientras, avanzo las reglas»

«Claude está trabajando en eso» no es un avance. Un avance es algo que se puede ver o comprobar: un comando,

una pantalla, un archivo, una prueba, o un bloqueo bien diagnosticado.

SICOP CONNECT · Guía de aprendizaje y ejecución C O N F I D E N C I A L

Hermatix M2M Communication S.R.L. · Documento confidencial — uso interno. Prohibida su distribución sin autorización. Página 16 de 69

CONFIDENCIAL8.3. La revisión semanal (viernes 16:00, 30 min)

Estado (5 min) · demostración (10) · plan vs. real: horas y encargos de Claude (5) · decisiones para la semana

siguiente (10). Cada hito se califica como cumplido, parcial o bloqueado. «Cumplido» requiere tres cosas: funciona,

hay evidencia registrada y tú lo explicas.

9\. Cómo demostrar que algo funciona

9.1. Tipos de evidencia

Evidencia Qué demuestra Qué NO demuestra

Claude dice «listo, funciona» Nada por sí solo Que funcione

Pruebas automáticas que pasan

( pytest )

Que la lógica cumple los casos

probados

Que funcione con el archivo real

Ejecución con datos sintéticos Que el programa maneja ese caso

inventado

Que el formato real sea igual

Ejecución con datos reales Que funciona con lo que entrega

SICOP

Que funcione en el servidor

Funcionamiento en el servidor Que opera en producción Que siga funcionando tras un reinicio (eso se

prueba aparte)

Siempre etiqueta tu evidencia: real, sintética o simulada. Presentar algo simulado como real impide aceptar el hito.

9.2. Leer el cambio que hizo Claude

Después de cada encargo, ejecuta git diff (o revisa los cambios en el editor) y respóndete:

¿Qué archivos cambió? ¿Esperaba que tocara esos?

¿Puedo explicar con mis palabras qué hace cada parte nueva?

¿Agregó dependencias nuevas? ¿Por qué?

¿Hay algo que parezca un secreto, una ruta personal o datos reales?

Si una respuesta es «no sé», pregunta a Claude por esa parte concreta antes del commit.

1\.

2\.

3\.

4\.

SICOP CONNECT · Guía de aprendizaje y ejecución C O N F I D E N C I A L

Hermatix M2M Communication S.R.L. · Documento confidencial — uso interno. Prohibida su distribución sin autorización. Página 17 de 69

CONFIDENCIALPARTE III · EL RECORRIDO: 20 LECCIONES

10\. Mapa del recorrido

10.1. La lógica del orden

El mes está ordenado para que cada semana entregue algo que funciona y para que el riesgo baje pronto:

Semana Pregunta que responde Resultado

1 · Piloto local ¿Podemos convertir datos reales de SICOP en

oportunidades explicables?

Todo el recorrido del ejemplo 2.2 funcionando en

tu computadora

2 · Producción ¿Puede funcionar solo, de forma segura, todos los

días?

Panel protegido en el servidor, correo real, ciclo

programado

3 · Valor adicional ¿Qué más puede aportar al negocio? Ampliaciones elegidas por Oscar

4 · Operación y

entrega

¿Puede Hermatix confiar en él y mantenerlo sin ti? Recuperación probada, documentación,

presentación final

¿Por qué se despliega en la semana 2 y no al final? Porque los problemas de servidor, accesos y correo son los más

difíciles de prever. Descubrirlos el día 9 deja tiempo para resolverlos; descubrirlos el día 19 pone en riesgo toda la

entrega.

10.2. Objetivos medibles

\# Objetivo Cómo se mide Fecha

O1 Comprender la fuente Acceso a SICOP probado con archivo real y documentado Día 1

O2 Importar con confiabilidad Archivo real cargado, códigos íntegros, recarga sin duplicados Día 3

O3 Detectar con fundamento ≥ 80 % de acierto sobre el conjunto etiquetado por Oscar Día 4

O4 Piloto local completo Archivo real → candidatos → panel → decisión persistente Día 5

O5 Piloto en producción Panel protegido en servidor, correo real recibido, ciclo programado Día 10

O6 Aportar valor adicional ≥ 3 ampliaciones aceptadas por Oscar Día 15

O7 Operación resiliente Reinicio, respaldo restaurado y reversión probados Día 16

O8 Transferencia Presentación, manuales verificados, métricas y plan de continuidad Día 20

SICOP CONNECT · Guía de aprendizaje y ejecución C O N F I D E N C I A L

Hermatix M2M Communication S.R.L. · Documento confidencial — uso interno. Prohibida su distribución sin autorización. Página 18 de 69

CONFIDENCIAL10.3. Calendario

10.4. Cómo está organizada cada lección

Parte Para qué

Objetivo Lo que debe existir al terminar el día

Para qué sirve La conexión con el problema de Hermatix

Lo que necesitas entender Conceptos del día, explicados

Agenda Bloques horarios y responsables

Paso a paso Instrucciones numeradas

Encargo para Claude Texto listo para pegar en Claude Code

Comprobación Lista para marcar antes de dar el día por terminado

Si algo falla Problemas típicos y su solución

Autoevaluación Preguntas que debes poder responder sin ayuda

Entregas Lo que queda registrado al cerrar

SICOP CONNECT · Guía de aprendizaje y ejecución C O N F I D E N C I A L

Hermatix M2M Communication S.R.L. · Documento confidencial — uso interno. Prohibida su distribución sin autorización. Página 19 de 69

CONFIDENCIAL11. Semana 1 — Piloto local de punta a punta

Meta de la semana: recorrer en tu computadora todo el viaje del dato (sección 2.2) con un archivo real de SICOP.

Conceptos de la semana: terminal, Git, entorno virtual, ruta web, base de datos, migración, idempotencia, reglas

explicables. Capacidad de Claude estimada: 45–60 encargos.

Lección 1 · lunes 5 de octubre — Preparar el taller y conocer la fuente

Objetivo: tener el entorno de trabajo listo, una aplicación mínima que responde y un archivo real descargado de

SICOP.

Para qué sirve: un carpintero prepara su taller antes de construir el mueble. Hoy instalas las herramientas, creas

la estructura del proyecto y, lo más importante, compruebas cómo se obtienen los datos de verdad. Todo lo demás

depende de esto: sin datos reales, cualquier programa es una suposición.

Lo que necesitas entender: terminal, Git, entorno virtual, .env , ruta web y Claude Code (sección 4.1 y 4.2).

También qué es SICOP y qué es un cartel (sección 1.2).

Agenda

Hora Actividad Quién

08:00–08:30 Reunión de arranque: objetivo, dependencias con fecha (sección 19.5), reservar sesiones Tú + Oscar 30 min

08:30–10:00 Pasos 1–4: instalar y configurar herramientas Tú 1,5 h

10:00–12:00 Pasos 5–7: crear el proyecto mínimo con Claude y comprobarlo Tú + Claude 2 h

13:00–15:30 Paso 8: prueba real del portal SICOP Tú + Oscar 2,5 h

15:30–16:15 Paso 9: documentar lo observado Tú + Claude 45 min

16:15–17:00 Paso 10: primer commit y bitácora Tú 45 min

Paso a paso

Paso 1 — Instalar Python, Git y el editor. Descarga desde las fuentes oficiales: Python 3.12 o superior (en el

instalador marca «Add python.exe to PATH»; sin eso la terminal no lo encontrará), Git y VS Code (o Windsurf si

Hermatix ya lo usa). Abre una terminal nueva de PowerShell y verifica:

python --version

git --version

Deben responder con un número de versión. ¿Por qué una terminal nueva? Porque la terminal lee la configuración

del sistema al abrirse; una que ya estaba abierta no «ve» lo recién instalado.

Paso 2 — Activar Claude Pro. Entra a claude.ai con tu cuenta individual, activa Pro mensual (revisa el precio local) y

deja desactivado el uso adicional pagado. Así, si se agota la capacidad, simplemente esperas; nunca se generan

cobros inesperados.

Paso 3 — Instalar Claude Code. Sigue la guía oficial. En PowerShell:

SICOP CONNECT · Guía de aprendizaje y ejecución C O N F I D E N C I A L

Hermatix M2M Communication S.R.L. · Documento confidencial — uso interno. Prohibida su distribución sin autorización. Página 20 de 69

CONFIDENCIALirm https://claude.ai/install.ps1 | iex

Abre una terminal nueva y verifica con claude --version . Luego ejecuta claude , elige iniciar sesión con tu

cuenta de Claude con suscripción Pro (no Console/API) y completa el acceso en el navegador. Dentro de Claude

Code escribe /status y /usage .

&#x20;Si /status indica que se usa una clave de API ( ANTHROPIC\_API\_KEY ), Claude Code cobraría por API en

lugar de usar tu plan. Avisa a Oscar para retirarla de tu entorno. No muestres su valor a nadie ni la pegues en

Claude.

Paso 4 — Crear la carpeta del proyecto, Git y el entorno virtual.

mkdir sicop-connect

cd sicop-connect

git init

python -m venv .venv

.\\.venv\\Scripts\\Activate.ps1

Qué hace cada línea: crea la carpeta, entra en ella, inicia el historial de Git, crea la caja de herramientas de Python

del proyecto y la activa. Sabrás que está activa porque la línea de la terminal empieza con (.venv) . Si Windows

bloquea la activación, usa .\\.venv\\Scripts\\python.exe en lugar de python ; no cambies políticas de seguridad

de la empresa.

Copia esta guía en la raíz como SICOP\_CONNECT\_RETO\_4\_SEMANAS.md . Crea docs/referencias/ y coloca allí los

PDF técnicos (diccionario de datos y diagrama ERD). Tu PDF personal no entra al proyecto.

Paso 5 — Crear CLAUDE.md , la memoria del proyecto. Claude Code lee este archivo al iniciar cada sesión; es como

el reglamento que le das a un colaborador nuevo. Se mantiene corto porque se lee en cada interacción: un archivo

largo gastaría capacidad todo el mes. Crea CLAUDE.md con este contenido:

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

SICOP CONNECT · Guía de aprendizaje y ejecución C O N F I D E N C I A L

Hermatix M2M Communication S.R.L. · Documento confidencial — uso interno. Prohibida su distribución sin autorización. Página 21 de 69

CONFIDENCIAL## Prohibido

\- Inventar APIs, campos o resultados de SICOP.

\- Leer .env, secretos o documentos personales (usar .env.example).

\- Enviar correos reales, activar tareas programadas o tocar el servidor sin instrucción

explícita.

Paso 6 — Pedir a Claude la aplicación mínima. En la carpeta del proyecto ejecuta claude y pega el encargo de

abajo. Mientras trabaja, lee la sección 15 (arquitectura) para saber qué está construyendo.

Encargo para Claude

CONTEXTO: Lee CLAUDE.md y las secciones 15.2 a 15.5 de SICOP\_CONNECT\_RETO\_4\_SEMANAS.md.

TAREA: Crea la base del proyecto.

ALCANCE:

\- Estructura de carpetas de la sección 15.3 (con \_\_init\_\_.py donde aplique).

\- app/config.py: carga .env localmente; las variables del proceso tienen prioridad.

\- app/main.py con GET /health (estado de la app y acceso a la base, sin secretos).

\- app/cli.py con el comando doctor (configuración disponible/pendiente, sin valores secretos).

\- .env.example (sección 15.4), .gitignore (excluye .env, .venv, data/, \*.db, backups),

&#x20;requirements.txt, requirements-dev.txt (pytest, httpx), pyproject.toml y README.md

&#x20;con instrucciones para PowerShell.

\- docs/ESTADO\_PROYECTO.md y docs/BITACORA.md con las plantillas de la sección 20.

NO implementes importadores, reglas, correo ni programador.

CRITERIO DE ACEPTACIÓN:

\- pytest pasa con una prueba de /health y una de doctor.

\- python -m app.cli doctor muestra la configuración sin secretos.

\- uvicorn arranca y /health responde 200.

VERIFICA ejecutando todo lo anterior y muéstrame la salida.

CIERRE: actualiza ESTADO\_PROYECTO.md, resume en ≤ 8 líneas y explícame qué es

un entorno virtual y qué es una ruta web con un ejemplo corto cada uno.

Paso 7 — Comprobar tú misma. Instala dependencias y prueba:

python -m pip install -r requirements.txt -r requirements-dev.txt

python -m pytest

python -m app.cli doctor

python -m uvicorn app.main:app --reload

Abre http://127.0.0.1:8000/health en el navegador. Debes ver una respuesta de estado. Detén el servidor con

Ctrl+C .

Paso 8 — Prueba real del portal SICOP (con Oscar). Sigue el procedimiento de la sección 16.2. Lo esencial: solicitar

carteles y líneas de los últimos 30 días, sin filtrar por institución, usando el buzón empresarial; anotar si pide un

código por correo y si el enlace vence; y guardar el archivo sin abrirlo en Excel. ¿Por qué? Excel convierte los

códigos largos en notación científica ( 1,23E+23 ) y los destruye sin avisar.

Paso 9 — Documentar lo observado. Pide a Claude las plantillas y complétalas tú con lo que viste:

Crea docs/ACCESO\_SICOP.md y docs/MAPEO\_DATOS.md como plantillas para registrar

lo observado en el portal (sección 16.2) y el mapeo columna → campo interno de

los reportes de la sección 16.3. Usa docs/referencias/ solo para listar los

reportes. No declares ninguna API. No accedas al buzón ni automatices el navegador.

Paso 10 — Primer commit.

SICOP CONNECT · Guía de aprendizaje y ejecución C O N F I D E N C I A L

Hermatix M2M Communication S.R.L. · Documento confidencial — uso interno. Prohibida su distribución sin autorización. Página 22 de 69

CONFIDENCIALgit status

git add CLAUDE.md SICOP\_CONNECT\_RETO\_4\_SEMANAS.md README.md app tests

docs .gitignore .env.example requirements.txt requirements-dev.txt pyproject.toml

git commit -m "Base del proyecto y acceso a SICOP documentado"

Antes de confirmar, revisa en git status que no aparezcan .env , .venv ni data/ .

Comprobación

☐ python --version , git --version y claude --version responden.

☐ /status muestra tu cuenta Pro, sin clave de API.

☐ pytest pasa; doctor funciona; /health responde en el navegador.

☐ Hay un archivo real de carteles en data/incoming/ (o el bloqueo está documentado con responsable).

☐ ACCESO\_SICOP.md describe filtros, formato y comportamiento del código de validación.

☐ Primer commit hecho, sin secretos ni datos.

Si algo falla

Síntoma Causa probable Solución

python no se reconoce No se marcó «Add to PATH» o la

terminal es vieja

Abre una terminal nueva; prueba py ; reinstala marcando

la opción

No se puede activar

.venv

Política de ejecución de Windows Usa .\\.venv\\Scripts\\python.exe directamente

ModuleNotFoundError Dependencias no instaladas en el

entorno activo

Activa .venv y repite pip install

SICOP no envía el correo Buzón, filtros o demora del portal Revisa no deseados; espera; anota el tiempo; repite con

Oscar

Autoevaluación

¿Por qué el proyecto tiene su propio entorno virtual?

¿Qué pasaría si abrieras el CSV de SICOP en Excel y lo guardaras?

¿Qué diferencia hay entre la aplicación que construyes y Claude?

Entregas: commit inicial · ACCESO\_SICOP.md · archivo real guardado · primera entrada de bitácora. Claude:

6–9 encargos · ≈ 20–30 min de trabajo activo.

Lección 2 · martes 6 de octubre — Guardar los datos de forma confiable

Objetivo: que el archivo real de carteles se guarde en la base de datos, sin perder códigos y sin duplicar si se

carga dos veces.

Para qué sirve: la importación es la base de todo. Si un código se corrompe, el cartel no se podrá unir con sus

líneas; si una carga duplica filas, el encargado recibirá avisos repetidos. Un error aquí se multiplica en todas las

estaciones siguientes.

•

•

•

•

•

•

1\.

2\.

3\.

SICOP CONNECT · Guía de aprendizaje y ejecución C O N F I D E N C I A L

Hermatix M2M Communication S.R.L. · Documento confidencial — uso interno. Prohibida su distribución sin autorización. Página 23 de 69

CONFIDENCIALLo que necesitas entender

Tabla, fila, columna, clave (sección 4.3). Un cartel es una fila de la tabla tenders ; su NRO\_SICOP es su

identificador.

Migración: en lugar de crear tablas a mano, se escriben cambios numerados (001, 002…) que el comando

migrate aplica en orden. Así cualquier computadora —incluido el servidor— tendrá exactamente la misma

estructura.

Idempotencia: la importación debe poder repetirse sin daño. Se logra con claves únicas (el mismo cartel no

puede guardarse dos veces) y con el hash del archivo (el mismo archivo se reconoce).

Versiones: si SICOP modifica un cartel (cambia la fecha de cierre), no se borra lo anterior: se guarda una nueva

versión. Así se puede saber qué cambió.

Agenda

Hora Actividad Quién

08:15–09:00 Paso 1: inspeccionar el archivo real y mapear columnas Tú 45 min

09:00–10:30 Pasos 2–3: modelo de datos y migraciones Tú + Claude 1,5 h

10:30–12:00 Paso 4: importador de carteles Tú + Claude 1,5 h

13:15–14:30 Paso 5: importar el archivo real y verificar Tú 1,25 h

14:30–15:30 Paso 6: taller comercial 1 con Oscar Tú + Oscar 1 h

15:30–17:00 Correcciones, commit, bitácora Tú 1,5 h

Paso a paso

Paso 1 — Conocer el archivo antes de programar. Ábrelo con un editor de texto (VS Code), no con Excel. Responde

en MAPEO\_DATOS.md : ¿qué separador usa (coma, punto y coma)?, ¿qué encabezados tiene?, ¿cómo se escriben las

fechas?, ¿cuántas filas? Copia los encabezados y 5 filas a tests/fixtures/carteles\_muestra.csv (si hay datos

sensibles, cámbialos y marca el archivo como sintético). ¿Por qué? Porque programar sin mirar los datos es

programar suposiciones.

Paso 2 — Entender el modelo. Lee la sección 16.3 («Tablas internas mínimas»). Dibuja en papel cómo se relacionan

imports , raw\_snapshots y tenders .

Paso 3 — Encargo de migraciones (abajo, encargo A). Al terminar, ejecuta python -m app.cli migrate dos veces:

la segunda no debe fallar ni cambiar nada.

Paso 4 — Encargo del importador (encargo B). Usa el modo plan ( Shift+Tab ): revisa el plan que propone Claude

antes de aprobarlo. ¿Incluye guardar el original? ¿Trata los códigos como texto?

Paso 5 — Verificar con el archivo real.

python -m app.cli import --path data/incoming/NOMBRE\_ARCHIVO.csv --report carteles

python -m app.cli import --path data/incoming/NOMBRE\_ARCHIVO.csv --report carteles

La primera vez debe informar filas aceptadas y rechazadas. La segunda, cero filas nuevas. Elige un cartel del

archivo, busca su NRO\_SICOP en la base y compara carácter por carácter.

•

•

•

•

SICOP CONNECT · Guía de aprendizaje y ejecución C O N F I D E N C I A L

Hermatix M2M Communication S.R.L. · Documento confidencial — uso interno. Prohibida su distribución sin autorización. Página 24 de 69

CONFIDENCIALPaso 6 — Taller comercial con Oscar. Revisen juntos la tabla de familias (sección 16.4). Oscar confirma, quita o

agrega señales y exclusiones. Anota todo: mañana y pasado lo usarás.

Encargo A — modelo de datos

CONTEXTO: CLAUDE.md, sección 16.3 de la guía y docs/MAPEO\_DATOS.md.

TAREA: Migraciones versionadas y comando migrate para las tablas mínimas de la

sección 16.3 (todas, aunque hoy solo usemos imports, raw\_snapshots y tenders).

CRITERIO: identificadores TEXT; dinero como texto decimal + moneda; claves e

índices únicos que impidan duplicados; migrate es repetible sin error.

VERIFICA con pytest (base temporal) y ejecutando migrate dos veces.

CIERRE: resume y explícame qué es una migración y una clave única con un ejemplo.

Encargo B — importador de carteles

TAREA: import --path ARCHIVO --report carteles según el mapeo de MAPEO\_DATOS.md.

\- Lee el CSV detectando codificación y separador; IDs siempre como texto.

\- Guarda el original en RAW\_DATA\_DIR con su hash; registra la importación.

\- Reporta aceptadas, rechazadas (con motivo y número de fila) y advertencias.

\- Idempotente: el mismo archivo dos veces no duplica; una versión modificada

&#x20;de un cartel crea nueva instantánea sin perder la anterior.

CRITERIO (pytest con fixtures sintéticos marcados como tales):

\- código de 24 dígitos con ceros iniciales se conserva exacto;

\- fila inválida se rechaza con motivo;

\- archivo repetido → 0 filas nuevas; cartel modificado → nueva versión.

NO agregues JSON ni XLSX. VERIFICA y luego dime el comando para el archivo real.

Comprobación

☐ migrate se ejecuta dos veces sin error.

☐ El archivo real se importa y muestra un resumen de aceptadas y rechazadas.

☐ La segunda importación del mismo archivo agrega 0 filas.

☐ Un código largo del archivo es idéntico en la base.

☐ Puedes explicar por qué se rechazó al menos una fila.

☐ Familias comerciales confirmadas por Oscar y anotadas.

Si algo falla

Síntoma Causa probable Solución

Caracteres raros (Ã³ en lugar

de ó)

Codificación distinta (UTF-8 vs. Latin-1) Pide a Claude detectar la codificación; agrega una

prueba

Todas las filas rechazadas Separador o encabezados distintos a los

del mapeo

Revisa el paso 1; corrige MAPEO\_DATOS.md

Códigos con E+ El archivo ya pasó por Excel No se puede reparar: descarga de nuevo y registra el

incidente

La segunda carga duplica Falta una clave única Vuelve al encargo A: revisa índices únicos

Autoevaluación

Sigue una fila del CSV hasta la tabla tenders : ¿qué pasos atraviesa?

¿Por qué un identificador de 24 dígitos no se guarda como número?

•

•

•

•

•

•

1\.

2\.

SICOP CONNECT · Guía de aprendizaje y ejecución C O N F I D E N C I A L

Hermatix M2M Communication S.R.L. · Documento confidencial — uso interno. Prohibida su distribución sin autorización. Página 25 de 69

CONFIDENCIAL¿Qué significa que la importación sea idempotente y cómo lo compruebas?

Entregas: migraciones · importador con pruebas · MAPEO\_DATOS.md de carteles · familias confirmadas · commit.

Claude: 8–12 encargos · ≈ 40–55 min.

Lección 3 · miércoles 7 de octubre — Ver qué se compra realmente

Objetivo: unir cada cartel con sus líneas, con la descripción del catálogo y con el nombre de la institución; y

tener el conjunto de prueba etiquetado por Oscar.

Para qué sirve: recuerda el ejemplo 2.2: el título «Servicios para la flota institucional» no decía nada; las líneas

revelaban «monitoreo satelital» y «cámaras vehiculares». Sin esta lección, la app solo vería títulos y perdería las

mejores oportunidades.

Lo que necesitas entender

Relación entre tablas: las líneas tienen el NRO\_SICOP de su cartel; esa es la «llave» que las une. El catálogo

traduce CODIGO\_IDENTIFICACION a un nombre. La institución se une por su cédula.

Nunca unir por parecido: si dos títulos se parecen, no significa que sean la misma compra. Solo se une por

claves.

Dinero: cantidad × precio unitario es una estimación por línea, en su moneda. No es el presupuesto ni el

monto que se pagará. Colones y dólares nunca se suman.

Golden set: una lista de casos reales que Oscar etiqueta a mano. Es la «hoja de respuestas» con la que mañana

medirás si tus reglas aciertan (sección 16.5).

Agenda

Hora Actividad Quién

08:15–08:45 Paso 1: mapear encabezados reales de líneas, catálogo e instituciones Tú 30 min

08:45–11:00 Paso 2: importadores y relaciones Tú + Claude 2,25 h

11:00–12:00 Paso 3: verificar una compra real completa Tú 1 h

13:15–14:15 Paso 4: taller comercial 2 — etiquetar el golden set Tú + Oscar 1 h

14:15–15:30 Paso 5: guardar el golden set Tú + Claude 1,25 h

15:30–17:00 Commit, bitácora, demo Tú 1,5 h

Paso a paso

Repite el paso 1 de la lección 2 para los archivos de líneas, catálogo e instituciones. Completa MAPEO\_DATOS.md .

Da el encargo de abajo a Claude.

Elige un cartel real con varias líneas. Verifica que el programa muestre todas sus líneas, la descripción de cada

código y el nombre del comprador. Compáralo con el archivo original.

Con Oscar, revisen entre 20 y 40 carteles reales: una mezcla de los que claramente interesan, los que

claramente no, y casos engañosos («GPS para topografía», «cámaras del edificio»). Para cada uno, Oscar

asigna: interesa / no interesa / falso positivo conocido, y la familia esperada.

3\.

•

•

•

•

1\.

2\.

3\.

4\.

SICOP CONNECT · Guía de aprendizaje y ejecución C O N F I D E N C I A L

Hermatix M2M Communication S.R.L. · Documento confidencial — uso interno. Prohibida su distribución sin autorización. Página 26 de 69

CONFIDENCIALPide a Claude guardar ese conjunto en tests/golden/golden\_set.csv con columnas nro\_sicop, titulo,

etiqueta, familia\_esperada . Solo datos públicos del cartel; nada confidencial.

Encargo para Claude

CONTEXTO: CLAUDE.md, sección 16.3 y MAPEO\_DATOS.md actualizado.

TAREA: import --report lineas | catalogo | instituciones y sus relaciones.

\- Une líneas↔carteles por NRO\_SICOP (+ secuencia si existe), líneas↔catálogo

&#x20;por CODIGO\_IDENTIFICACION, carteles↔instituciones por cédula.

\- Estimación por línea = cantidad × precio unitario en Decimal con su moneda.

\- Registra líneas huérfanas y códigos sin catálogo como advertencias, sin inventar.

CRITERIO (pytest): un cartel con 3 líneas recupera las 3; un código sin catálogo

queda marcado; montos en monedas distintas nunca se suman.

VERIFICA con los archivos reales y muéstrame una compra con sus líneas y comprador.

Comprobación

☐ Una compra real aparece con todas sus líneas, descripciones y comprador.

☐ Los códigos sin catálogo quedan marcados, no inventados.

☐ El golden set está guardado y Oscar confirmó las etiquetas.

Si algo falla

Síntoma Causa probable Solución

Muchas líneas

«huérfanas»

Los periodos de carteles y líneas no coinciden, o la

clave tiene otro formato

Compara un NRO\_SICOP en ambos archivos;

descarga el mismo periodo

Descripciones vacías Falta el catálogo o el código tiene otra longitud Verifica que el catálogo esté importado y que los

códigos sean texto

Montos absurdos Separador decimal (coma vs. punto) Agrega una prueba con el formato real

Autoevaluación

¿Qué campo une un cartel con sus líneas? ¿Y una línea con el catálogo?

¿Por qué la estimación por línea no es el presupuesto de la compra?

¿Para qué sirve el golden set y por qué debe etiquetarlo Oscar y no tú?

Entregas: importadores con pruebas · golden set · MAPEO\_DATOS.md completo · commit. Claude: 7–10

encargos · ≈ 35–50 min.

Lección 4 · jueves 8 de octubre — Enseñarle al programa qué le interesa a Hermatix

Objetivo: un motor de reglas que clasifique cada compra por familia y prioridad, muestre la frase exacta que lo

justifica y acierte en al menos el 80 % del golden set.

Para qué sirve: este es el «cerebro» comercial del sistema. Una alerta sin explicación genera desconfianza; una

alerta con evidencia («dice monitoreo satelital de vehículos en la línea 1») le permite al encargado decidir en

segundos.

5\.

•

•

•

1\.

2\.

3\.

SICOP CONNECT · Guía de aprendizaje y ejecución C O N F I D E N C I A L

Hermatix M2M Communication S.R.L. · Documento confidencial — uso interno. Prohibida su distribución sin autorización. Página 27 de 69

CONFIDENCIALLo que necesitas entender

Reglas en un archivo de configuración (YAML): las señales y exclusiones no se escriben dentro del código, sino

en config/hermatix\_rules.yaml . Así Hermatix puede ajustarlas sin programar.

Normalizar: para comparar, se pasa todo a minúsculas y sin tildes («Rastreo» = «rastreo»); pero se guarda y se

muestra el texto original.

Exclusión por contexto: «GPS» suma a la familia de flotas, salvo que aparezca «topográfico» o

«levantamiento».

Cuatro dimensiones separadas: encaje comercial, plazo/estado, requisitos y calidad de datos (sección 16.4).

«Alta» habla del encaje, no de si Hermatix puede ganar.

Sobreajuste: ajustar las reglas solo para que acierten en el golden set, con trucos que no sirven para casos

nuevos. Se evita usando señales que tengan sentido comercial.

Agenda

Hora Actividad Quién

08:15–08:45 Paso 1: escribir tú el YAML inicial Tú 30 min

08:45–11:00 Paso 2: motor de reglas y comando evaluate Tú + Claude 2,25 h

11:00–12:00 Paso 3: revisar los 20 primeros candidatos reales Tú 1 h

13:15–15:00 Paso 4: medir contra el golden set y ajustar Tú + Claude 1,75 h

15:00–17:00 Paso 5: documentar REGLAS.md , commit, bitácora Tú 2 h

Paso a paso

Escribe tú, a mano, el primer config/hermatix\_rules.yaml con las familias confirmadas por Oscar. ¿Por qué

a mano? Porque así entiendes la estructura que luego tendrás que mantener. Ejemplo:

familias:

&#x20;gps\_flotas:

&#x20;producto: FleetMatix

&#x20;senales\_alta: \["rastreo vehicular", "monitoreo satelital de vehiculos", "gps vehicular",

"avl"]

&#x20;senales\_media: \["gestion de flota", "control de combustible"]

&#x20;exclusiones: \["topografic", "levantamiento", "catastr"]

&#x20;videotelematica:

&#x20;producto: Fenova IA

&#x20;senales\_alta: \["camaras vehiculares", "dashcam", "mdvr", "video a bordo"]

&#x20;exclusiones: \["edificio", "perimetral", "cctv urbano"]

Da el encargo de abajo a Claude.

Ejecuta python -m app.cli evaluate sobre los datos reales y revisa los primeros 20 candidatos: ¿tienen

sentido? Anota los errores.

Ejecuta la prueba del golden set. Para cada fallo, decide: ¿falta una señal?, ¿falta una exclusión?, ¿el caso es

realmente ambiguo? Cambia el YAML, predice qué caso cambiará, vuelve a medir y comprueba tu predicción.

Escribe docs/REGLAS.md : cómo se agrega una señal o una exclusión y cómo se mide el efecto.

Encargo para Claude

•

•

•

•

•

1\.

1\.

2\.

3\.

4\.

SICOP CONNECT · Guía de aprendizaje y ejecución C O N F I D E N C I A L

Hermatix M2M Communication S.R.L. · Documento confidencial — uso interno. Prohibida su distribución sin autorización. Página 28 de 69

CONFIDENCIALCONTEXTO: CLAUDE.md, sección 16.4 y config/hermatix\_rules.yaml.

TAREA: comando evaluate.

\- Normaliza mayúsculas/acentos para comparar, pero guarda el texto original.

\- Busca señales en título y descripciones de líneas/catálogo; aplica exclusiones

&#x20;por contexto (p. ej., «topográfico» anula GPS).

\- Guarda en opportunity\_assessments: familia, producto Hermatix, prioridad

&#x20;(Alta/Media/Baja/Sin coincidencia), regla y frase exacta de evidencia,

&#x20;plazo/estado y calidad de datos como dimensiones separadas.

\- Reevaluar es idempotente y registra la versión de reglas usada.

CRITERIO (pytest): «monitoreo GPS de vehículos» → Alta FleetMatix;

«GPS para levantamiento topográfico», «cámaras de seguridad del edificio» y

«radar meteorológico» → no Alta. Agrega una prueba que lea tests/golden/

e informe el % de acierto.

VERIFICA y muéstrame el % de acierto y los casos fallidos con su evidencia.

CIERRE: explícame cómo se decide la prioridad con un ejemplo.

Comprobación

☐ Cada candidato muestra familia, prioridad, regla y frase de evidencia.

☐ Los tres falsos positivos de prueba no salen como Alta.

☐ Acierto ≥ 80 % en el golden set (o explicación documentada de por qué no y qué falta).

☐ Hiciste al menos un cambio con predicción previa y la comprobaste.

Si algo falla

Síntoma Causa probable Solución

Demasiados candidatos Señales muy generales («gps», «cámara») Muévelas a «media» o exige contexto; agrega

exclusiones

Casi ningún candidato Faltan líneas o catálogo; señales muy

específicas

Verifica la lección 3; agrega sinónimos reales

Acierto bajo pese a

ajustes

Etiquetas ambiguas Revisa los casos con Oscar; no fuerces reglas

artificiales

Autoevaluación

¿Por qué las reglas viven en un YAML y no en el código?

Explica un falso positivo real que encontraste y cómo lo corregiste.

¿Qué diferencia hay entre «Alta coincidencia» y «Hermatix puede participar»?

Entregas: motor de reglas · YAML · prueba de golden set · REGLAS.md · commit. Claude: 8–12 encargos · ≈

40–55 min.

Lección 5 · viernes 9 de octubre — Mostrar y decidir · HITO 1

Objetivo: un panel web donde el encargado ve las oportunidades, abre el detalle con la evidencia y guarda su

decisión, que se conserva aunque se vuelvan a importar datos.

Para qué sirve: hasta ayer, los resultados vivían en la terminal; nadie del área comercial los usaría así. El panel

convierte el análisis en una herramienta de trabajo. Y la revisión humana persistente es la que cierra el ciclo: la app

sugiere, la persona decide, y esa decisión no se pierde.

•

•

•

•

1\.

2\.

3\.

SICOP CONNECT · Guía de aprendizaje y ejecución C O N F I D E N C I A L

Hermatix M2M Communication S.R.L. · Documento confidencial — uso interno. Prohibida su distribución sin autorización. Página 29 de 69

CONFIDENCIALLo que necesitas entender

Plantillas Jinja2: HTML con espacios que FastAPI llena con datos de la base.

Formulario y POST: cuando el encargado guarda una decisión, el navegador envía los datos al servidor con una

petición POST.

Escapar HTML: si un título de SICOP contiene <script> , debe mostrarse como texto, no ejecutarse. Jinja2 lo

hace por defecto; no se desactiva.

Paginación y filtros: con miles de carteles, se muestran por páginas y se filtra por prioridad, familia, institución

o plazo.

Agenda

Hora Actividad Quién

08:15–11:00 Paso 1: construir el panel Tú + Claude 2,75 h

11:00–12:00 Paso 2: probarlo con datos reales Tú 1 h

13:15–15:00 Paso 3: correcciones y ensayo de la demo Tú + Claude 1,75 h

15:00–16:00 Paso 4: plan vs. real de la semana Tú 1 h

16:00–16:30 Revisión semanal 1 Tú + Oscar 30 min

16:30–17:00 Commit de hito Tú 30 min

Paso a paso

Da el encargo de abajo. Usa modo plan: revisa que el plan incluya filtros, detalle con evidencia y conservación

de revisiones.

Arranca el panel ( python -m uvicorn app.main:app --reload ) y recorre como si fueras el encargado: filtra

«Alta», abre un detalle, lee la evidencia, guarda una decisión con comentario. Luego vuelve a importar el

archivo y comprueba que la decisión sigue ahí.

Corrige lo incómodo o confuso. Ensaya la demo completa del viaje del dato (sección 2.2) con un cartel real.

Compara lo planificado con lo real: horas por lección, encargos usados, % de capacidad. Anótalo; Oscar lo usará

para ajustar la semana 2.

Encargo para Claude

CONTEXTO: CLAUDE.md, secciones 15 y 16.4.

TAREA: panel con Jinja2 + HTML/CSS (sin frontend separado).

\- Lista paginada de oportunidades con filtros: prioridad, familia, institución,

&#x20;estado del plazo, revisado/no revisado; orden por cierre más próximo.

\- Detalle: datos del cartel, líneas, comprador, evidencia resaltada, regla,

&#x20;calidad de datos, cobertura de la fuente y enlace a SICOP si se conoce (si no, ID).

\- Formulario de revisión: decisión (Interesa / No interesa / Revisar requisitos),

&#x20;comentario, responsable y fecha; historial de revisiones.

\- Diseño limpio y sobrio, legible en laptop; todo el HTML escapado.

CRITERIO (pytest): la lista filtra; la revisión persiste; reimportar el mismo

cartel modificado NO borra la revisión. Sin autenticación todavía (lección 6).

VERIFICA y dame los pasos para probarlo manualmente en el navegador.

•

•

•

•

1\.

2\.

3\.

4\.

SICOP CONNECT · Guía de aprendizaje y ejecución C O N F I D E N C I A L

Hermatix M2M Communication S.R.L. · Documento confidencial — uso interno. Prohibida su distribución sin autorización. Página 30 de 69

CONFIDENCIALComprobación — HITO 1

☐ Demostración en vivo: archivo real → import → evaluate → panel → revisión guardada → reimportación

sin perder la revisión.

☐ Un título con caracteres especiales se muestra como texto.

☐ Reto de comprensión de la semana (sección 20.3) superado.

Si algo falla

Síntoma Causa probable Solución

La revisión desaparece al

reimportar

La revisión está ligada a la versión del cartel y no

al cartel

Pide que se ligue al identificador estable del

cartel

El panel es lento Consultas sin índices o sin paginación Agrega índices y paginación

Fechas en hora equivocada Zona horaria Mostrar siempre en America/

Costa\_Rica

Autoevaluación

¿Qué ocurre, paso a paso, cuando el encargado guarda una decisión?

¿Por qué el HTML debe escaparse?

¿Qué parte de esta semana tomó más tiempo: el reloj Claude, el humano o el calendario? ¿Por qué?

Entregas: panel funcional · commit de hito · métricas de la semana · bitácora. Claude: 8–12 encargos · ≈ 45–

60 min.

12\. Semana 2 — Piloto en producción

Meta de la semana: que el sistema funcione solo, protegido y todos los días en el servidor de Hermatix. Conceptos

de la semana: autenticación, sesiones, CSRF, proveedor de correo, deduplicación, bloqueo de ejecución, respaldo,

SSH, systemd. Capacidad de Claude estimada: 35–50 encargos.

Lección 6 · lunes 12 de octubre — Proteger el panel

Objetivo: que solo personas autorizadas puedan ver y modificar las oportunidades, y que se puedan subir

archivos de SICOP desde el panel.

Para qué sirve: el panel contiene decisiones comerciales de Hermatix. Al publicarlo en el servidor (lección 9), sin

protección cualquiera podría verlas o alterarlas. Además, la carga de archivos desde el panel permite que alguien

del área comercial alimente el sistema sin usar la terminal.

Lo que necesitas entender

Autenticación: comprobar quién eres (usuario y contraseña).

Hash de contraseña: la base guarda una huella irreversible, nunca la contraseña. Si alguien roba la base, no

obtiene las contraseñas.

•

•

•

1\.

2\.

3\.

•

•

SICOP CONNECT · Guía de aprendizaje y ejecución C O N F I D E N C I A L

Hermatix M2M Communication S.R.L. · Documento confidencial — uso interno. Prohibida su distribución sin autorización. Página 31 de 69

CONFIDENCIALSesión y cookie: tras iniciar sesión, el navegador guarda una cookie firmada que te identifica. HttpOnly impide

que un script la lea; Secure hace que solo viaje por HTTPS.

CSRF: un sitio malicioso podría intentar enviar un formulario a tu panel aprovechando tu sesión abierta. Un

token secreto en cada formulario lo impide.

No inventar seguridad: se usan bibliotecas mantenidas. Escribir criptografía propia es uno de los errores más

graves en desarrollo.

Agenda

Hora Actividad Quién

08:15–11:00 Paso 1: autenticación, sesiones, CSRF Tú + Claude 2,75 h

11:00–12:00 Paso 2: pruebas manuales de acceso Tú 1 h

13:15–15:00 Paso 3: confirmar servidor y correo con Oscar Tú + Oscar 1,75 h

15:00–17:00 Paso 4: carga de archivos desde el panel; commit Tú + Claude 2 h

Paso a paso

Da el encargo A. Después crea tu usuario con python -m app.cli create-user .

Prueba como atacante: abre el panel en una ventana privada sin iniciar sesión (debe redirigir al login); intenta

abrir directamente la URL de un detalle (debe rechazar); cierra sesión y usa el botón «atrás» (no debe mostrar

datos).

Con Oscar, completa en docs/DESPLIEGUE.md los datos del servidor (sistema operativo, versión de Python,

usuario SSH, rutas) y del correo (proveedor, remitente, destinatario). Si algo falta, se registra como bloqueo con

responsable; el despliegue es en tres días.

Da el encargo B y prueba subir un CSV real desde el panel.

Encargo A — proteger el panel

TAREA: proteger el panel.

\- Tabla users con contraseña hasheada (argon2 o bcrypt mediante biblioteca

&#x20;mantenida); comando create-user que pide la contraseña sin mostrarla.

\- Sesión con cookie firmada (SESSION\_SECRET externo), HttpOnly, SameSite=Lax,

&#x20;Secure en producción; expiración configurable.

\- Protección CSRF en todos los formularios POST.

\- /health sigue público y sin datos sensibles; todo lo demás requiere sesión.

NO construyas criptografía propia ni roles complejos.

CRITERIO (pytest): anónimo → redirección a login; POST sin token → 403;

login correcto → acceso; la contraseña nunca aparece en logs.

CIERRE: explícame sesión, hash y CSRF con un ejemplo cada uno.

Encargo B — carga de archivos

TAREA: página protegida para subir un CSV a INCOMING\_DIR y lanzar su

importación con el reporte elegido (carteles, lineas, catalogo, instituciones).

Límite de tamaño, validación de extensión, nombre de archivo seguro, y mostrar

el resumen de aceptadas/rechazadas. Pruebas con un archivo sintético.

Comprobación

☐ Sin sesión no se ve ningún dato; /health sí responde.

•

•

•

1\.

2\.

3\.

4\.

•

SICOP CONNECT · Guía de aprendizaje y ejecución C O N F I D E N C I A L

Hermatix M2M Communication S.R.L. · Documento confidencial — uso interno. Prohibida su distribución sin autorización. Página 32 de 69

CONFIDENCIAL☐ Un formulario sin token es rechazado.

☐ Se puede subir un CSV real desde el panel y ver su resumen.

☐ DESPLIEGUE.md tiene los datos del servidor o los bloqueos registrados.

Si algo falla: si el login funciona en desarrollo pero no en producción, suele ser la opción Secure de la cookie sin

HTTPS; en desarrollo se desactiva por configuración, nunca en el servidor.

Autoevaluación

Si alguien copia el archivo de la base, ¿puede saber tu contraseña? ¿Por qué?

¿Qué ataque evita el token CSRF?

¿Por qué /health puede ser público y el resto no?

Entregas: panel protegido · carga de archivos · DESPLIEGUE.md borrador · commit. Claude: 6–9 encargos.

Lección 7 · martes 13 de octubre — Avisar sin repetir

Objetivo: que el sistema prepare un resumen por correo, lo envíe al encargado solo cuando se le autorice y

nunca envíe el mismo aviso dos veces.

Para qué sirve: el panel requiere que alguien entre a revisarlo. El correo lleva la información a la persona, cada

mañana, sin que la busque: es lo que cumple la frase «sin buscar» del objetivo 1.4. Pero un correo con repetidos o

errores hace que la gente deje de leerlo.

Lo que necesitas entender

Outbox: una tabla donde se anota cada aviso antes de enviarlo, con su estado. Es la memoria de qué se envió a

quién.

Clave de deduplicación: destinatario + oportunidad + versión + motivo. Si ya existe, no se vuelve a enviar.

Dry-run: genera la vista previa del correo y la guarda, sin enviarlo. Todas las pruebas se hacen así.

Estados de un envío: preparado (en la outbox), aceptado (el proveedor lo recibió), fallido (el proveedor lo

rechazó), incierto (no hubo respuesta clara). Aceptado no es lo mismo que recibido en la bandeja.

Por qué no reintentar a ciegas: si un envío quedó «incierto», quizá sí llegó. Reintentar automáticamente podría

duplicarlo; se revisa primero.

Agenda

Hora Actividad Quién

08:15–11:00 Paso 1: resumen y outbox en dry-run Tú + Claude 2,75 h

11:00–12:00 Paso 2: revisar la vista previa con Oscar Tú + Oscar 1 h

13:15–15:00 Paso 3: conectar el proveedor de correo Tú + Claude 1,75 h

15:00–16:00 Paso 4: prueba real controlada Tú + Oscar 1 h

16:00–17:00 Commit y bitácora Tú 1 h

•

•

•

1\.

2\.

3\.

•

•

•

•

•

SICOP CONNECT · Guía de aprendizaje y ejecución C O N F I D E N C I A L

Hermatix M2M Communication S.R.L. · Documento confidencial — uso interno. Prohibida su distribución sin autorización. Página 33 de 69

CONFIDENCIALPaso a paso

Da el encargo A. Ejecuta python -m app.cli notify --dry-run dos veces: la segunda no debe agregar

avisos.

Muestra la vista previa (en data/exports/ ) a Oscar: ¿se entiende en 30 segundos?, ¿falta algo para decidir?,

¿sobra algo? Ajusta.

El administrador coloca las credenciales del correo en tu .env local (nunca las pegas en Claude). Da el encargo

B.

Con Oscar presente, ejecuta un envío real al destinatario acordado. Registra por separado: (a) qué respondió el

proveedor; (b) si el correo llegó a la bandeja; (c) si llegó a «no deseado». Ejecuta de nuevo --send : no debe

reenviar.

Encargo A — resumen y outbox

TAREA: notify --dry-run y notification\_outbox.

\- Selecciona oportunidades nuevas o con cambios relevantes (nueva versión,

&#x20;cambio de plazo) de prioridad Alta/Media; el lote inicial se limita a los

&#x20;últimos N días (configurable) para no enviar todo el histórico.

\- Clave de deduplicación: destinatario + oportunidad + versión + motivo.

\- Resumen en HTML y texto plano: prioridad, familia, institución, cierre,

&#x20;evidencia y enlace al panel. Vista previa en data/exports/.

\- Estados: preparado, aceptado, fallido, incierto. Dry-run NUNCA envía ni marca enviado.

CRITERIO (pytest): un segundo dry-run no duplica; dry-run no llama al proveedor.

Encargo B — proveedor de correo

TAREA: adaptador de correo para \[SMTP / proveedor confirmado] y notify --send.

\- --send exige NOTIFICATIONS\_ENABLED=true y NOTIFICATIONS\_DRY\_RUN=false.

\- Timeout o respuesta ambigua → estado «incierto», sin reintento automático.

\- Pruebas con proveedor SIMULADO (marcado como tal); nunca envío real en pytest.

\- Logs sin credenciales.

VERIFICA con el simulado; después dame el comando exacto para la prueba real

con Oscar y qué debemos observar.

Comprobación

☐ Dry-run genera vista previa y no envía.

☐ El correo real llegó a la bandeja del destinatario (evidencia registrada).

☐ Un segundo envío no repite avisos.

Si algo falla: si el proveedor acepta pero el correo no llega, revisa «no deseado» y pide al administrador revisar

SPF/DKIM del remitente. No repitas envíos a ciegas.

Autoevaluación

Muestra el registro de outbox que impide reenviar un aviso.

¿Qué diferencia hay entre «aceptado» y «recibido»?

¿Por qué un estado «incierto» no se reintenta automáticamente?

Entregas: avisos con outbox · prueba real documentada · commit. Claude: 7–10 encargos.

1\.

2\.

3\.

4\.

•

•

•

1\.

2\.

3\.

SICOP CONNECT · Guía de aprendizaje y ejecución C O N F I D E N C I A L

Hermatix M2M Communication S.R.L. · Documento confidencial — uso interno. Prohibida su distribución sin autorización. Página 34 de 69

CONFIDENCIALLección 8 · miércoles 14 de octubre — Un solo comando para todo el ciclo

Objetivo: un comando run-cycle que haga todo el recorrido (recoger → importar → evaluar → avisar), un

respaldo confiable y el paquete listo para el servidor.

Para qué sirve: el servidor no puede «hacer clic». Necesita un único comando que se ejecute cada mañana y

que sea seguro: que no se ejecute dos veces a la vez, que distinga un fallo de «no hubo compras» y que deje

registro. El respaldo protege meses de decisiones humanas.

Lo que necesitas entender

Bloqueo (lock): un archivo-señal que impide que dos ciclos corran a la vez y dupliquen trabajo.

Cobertura: cada ciclo registra qué periodo y qué archivos procesó. Si la fuente falla, el registro lo dice; nunca se

interpreta como «cero oportunidades».

Respaldo consistente: copiar el archivo SQLite mientras se usa puede dar una copia dañada; se usa la función

de respaldo de SQLite.

Dependencias congeladas ( requirements.lock.txt ): la lista exacta de versiones probadas, para que el

servidor instale lo mismo que tu computadora.

Agenda

Hora Actividad Quién

08:15–11:00 Paso 1: run-cycle Tú + Claude 2,75 h

11:00–12:00 Paso 2: provocar fallos a propósito Tú 1 h

13:15–15:00 Paso 3: respaldo, dependencias, plantillas de servidor Tú + Claude 1,75 h

15:00–16:00 Paso 4: instalación limpia y restauración de prueba Tú 1 h

16:00–17:00 Paso 5: checklist del despliegue con Oscar (15 min), commit Tú 1 h

Paso a paso

Da el encargo A.

Rompe el sistema a propósito y anota qué pasa: carpeta vacía, archivo cortado a la mitad, archivo repetido,

dos ciclos al mismo tiempo (abre dos terminales). En cada caso, el sistema debe decir claramente qué ocurrió.

Probar los fallos es tan importante como probar el éxito.

Da el encargo B.

Crea una carpeta nueva, un entorno nuevo, instala con requirements.lock.txt y arranca. Luego haz un

respaldo y restáuralo en otra carpeta: abre la base restaurada y busca una revisión que conozcas.

Repasa con Oscar la lista de la lección 9: accesos, Mac, repositorio, credenciales. Lo que falte hoy, mañana

bloquea.

Encargo A — ciclo completo

TAREA: run-cycle --dry-run | --send.

Secuencia: recoger archivos completos de INCOMING\_DIR → importar → evaluate →

notify. Registra cada ejecución en source\_runs con cobertura y errores.

\- Bloqueo de archivo que impida ejecuciones simultáneas.

\- Archivo incompleto o ilegible → error explícito; nunca «0 oportunidades».

\- Archivos procesados se mueven a una subcarpeta con fecha.

•

•

•

•

1\.

2\.

3\.

4\.

5\.

SICOP CONNECT · Guía de aprendizaje y ejecución C O N F I D E N C I A L

Hermatix M2M Communication S.R.L. · Documento confidencial — uso interno. Prohibida su distribución sin autorización. Página 35 de 69

CONFIDENCIAL- Dry-run por defecto; --send respeta las mismas habilitaciones que notify.

NO inicies un programador dentro del panel. Obtención en modo manual.

CRITERIO (pytest): dos ciclos simultáneos → el segundo sale con mensaje claro;

fallo de fuente queda registrado; ciclo repetido no duplica avisos.

Encargo B — preparación de despliegue

TAREA: preparación de despliegue según la sección 17.

\- backup --output RUTA: copia consistente de SQLite (API de backup) + manifiesto

&#x20;(fecha, commit, versión de esquema, hash).

\- requirements.lock.txt desde un entorno limpio, solo dependencias de ejecución.

\- deploy/systemd/: sicop-web.service, sicop-migrate.service, sicop-cycle.service

&#x20;(dry-run) y sicop-cycle.timer, según la sección 17.4.

\- docs/DESPLIEGUE.md con los pasos marcados por terminal: Windows / Mac / servidor.

Sin secretos ni nombres de servidor inventados: usa MARCADORES en mayúscula.

Comprobación

☐ Ciclo completo con archivo real en dry-run.

☐ Los cuatro fallos provocados quedan registrados con mensaje claro.

☐ Instalación limpia exitosa; respaldo restaurado y legible.

☐ Checklist de despliegue revisado con Oscar.

Autoevaluación

¿Por qué un fallo de descarga no debe verse como «cero oportunidades»?

¿Qué pasaría sin el bloqueo si el timer y una persona lanzan el ciclo a la vez?

¿Por qué no basta con copiar el archivo .db para respaldarlo?

Entregas: run-cycle · respaldo · paquete candidato con commit identificado · commit. Claude: 8–11

encargos.

Lección 9 · jueves 15 de octubre — Llevar la aplicación al servidor

Objetivo: la aplicación instalada en el servidor de Hermatix, accesible por su dirección segura y con datos

reales.

Para qué sirve: hasta hoy, si apagabas tu computadora, el sistema desaparecía. En el servidor, funciona siempre,

para todo el equipo. Esta es la diferencia entre un ejercicio y una herramienta de empresa.

Lo que necesitas entender

Tres máquinas, tres terminales: Windows (donde desarrollas), Mac de Oscar (desde donde se transfiere) y el

servidor (al que se entra por SSH). Después de ssh , la terminal de la Mac se ve igual, pero las órdenes se

ejecutan en el servidor. Antes de cada comando, di en voz alta en qué máquina estás.

Paquete con hash: se empaqueta exactamente el commit revisado y se compara su huella en la Mac y en el

servidor. Si coinciden, nada se alteró en el camino.

Usuario de servicio: la app corre con un usuario sin privilegios ( sicop ), nunca como administrador ( root ). Si

alguien la vulnera, el daño queda contenido.

Datos fuera del código: el código va en /opt/sicop-connect ; los datos en /var/lib/sicop-connect ; la

configuración privada en /etc/sicop-connect . Así se puede actualizar el código sin tocar los datos.

•

•

•

•

1\.

2\.

3\.

•

•

•

•

SICOP CONNECT · Guía de aprendizaje y ejecución C O N F I D E N C I A L

Hermatix M2M Communication S.R.L. · Documento confidencial — uso interno. Prohibida su distribución sin autorización. Página 36 de 69

CONFIDENCIALAgenda (sesión práctica con Oscar)

Hora Actividad Quién

08:15–

09:00

Pruebas finales en Windows y publicación del commit Tú 45

min

09:00–

12:00

Despliegue: pasos 1–6 de la sección 17.2, configuración, migración, servicio

web

Tú + Oscar +

administrador

3 h

13:15–

14:30

Acceso por la dirección acordada, HTTPS y login desde otra computadora Tú + administrador 1,25 h

14:30–

16:00

Importar un archivo real en el servidor y revisar una oportunidad Tú 1,5 h

16:00–

17:00

Acta de despliegue y bitácora Tú 1 h

Paso a paso

Sigue la sección 17 completa. Tu papel: ejecutas guiada, explicas cada paso y registras; Oscar y el administrador

manejan contraseñas, claves y permisos. Para cada comando anota en el acta: máquina, comando, resultado, y qué

cambió.

Claude puede ayudarte a interpretar un mensaje de error (pegando solo el error, sin datos de acceso). Claude no

se conecta al servidor ni recibe credenciales.

Durante el despliegue obtuve este error en el SERVIDOR al ejecutar \[comando]:

\[mensaje de error sin rutas privadas ni credenciales].

Explícame la causa más probable y qué debería verificar el administrador.

No propongas desactivar seguridad ni ejecutar como root.

Comprobación

☐ El hash del paquete coincide en Mac y servidor.

☐ curl -f http://127.0.0.1:8000/health responde en el servidor.

☐ El panel abre en la dirección real con HTTPS y pide inicio de sesión.

☐ Una oportunidad real se revisó desde otra computadora.

☐ Acta de despliegue completa: commit, hash, pasos, responsables, pendientes.

Si algo falla

Síntoma Causa probable Solución

Permission denied Permisos de carpeta o usuario

equivocado

El administrador revisa propietario sicop

El servicio arranca y se cae Configuración incompleta o ruta

errónea

journalctl -u sicop-web.service -n 50

El panel no abre desde

fuera

Proxy o dirección sin configurar El administrador revisa el proxy; mientras, túnel SSH

supervisado

•

•

•

•

•

SICOP CONNECT · Guía de aprendizaje y ejecución C O N F I D E N C I A L

Hermatix M2M Communication S.R.L. · Documento confidencial — uso interno. Prohibida su distribución sin autorización. Página 37 de 69

CONFIDENCIALAutoevaluación

¿Qué comandos se ejecutaron en la Mac y cuáles en el servidor?

¿Por qué la app no corre como root ?

¿Por qué el código y los datos viven en carpetas distintas?

Entregas: aplicación en servidor · acta de despliegue · bitácora. Claude: 3–6 encargos (solo interpretación de

errores).

Lección 10 · viernes 16 de octubre — Que funcione solo cada mañana · HITO 2

Objetivo: el ciclo programado para las 07:00, enviando correos reales, y comprobado que sobrevive a un

reinicio.

Para qué sirve: este es el momento en que el objetivo 1.4 se cumple de verdad: el encargado recibirá

oportunidades cada mañana, sin que nadie intervenga.

Lo que necesitas entender

Timer de systemd: la alarma que lanza run-cycle a una hora fija. Se verifica la zona horaria del servidor: si

está en UTC, las 07:00 de Costa Rica son las 13:00 UTC.

Activación gradual: primero dry-run manual, luego envío supervisado, y solo al final el timer. Cada paso

confirma el anterior.

Persistencia: reiniciar el servicio no debe perder datos ni decisiones.

Agenda

Hora Actividad Quién

08:15–10:00 Paso 1: ciclo dry-run manual en el servidor Tú + Oscar 1,75 h

10:00–12:00 Paso 2: correo real, envío supervisado, timer Tú + Oscar + administrador 2 h

13:15–14:30 Paso 3: reinicio y persistencia Tú 1,25 h

14:30–16:00 Paso 4: propuesta de ampliaciones para la semana 3 Tú 1,5 h

16:00–16:30 Revisión semanal 2: Oscar elige ampliaciones Tú + Oscar 30 min

16:30–17:00 Cierre Tú 30 min

Paso a paso

Sigue la sección 17.5: ejecuta el servicio del ciclo en dry-run y revisa registro y vista previa.

El administrador habilita el correo real. Ejecuta un ciclo supervisado con envío, verifica recepción y habilita el

timer. Comprueba la próxima ejecución con systemctl list-timers sicop-cycle.timer .

Reinicia el servicio web y verifica que el panel vuelve y que una decisión guardada sigue ahí.

Prepara para Oscar una tabla con las ampliaciones A1–A6 (sección 19.2): valor, esfuerzo estimado y riesgo.

Recomienda un orden y justifícalo.

Comprobación — HITO 2

☐ Panel protegido en el servidor con datos reales.

1\.

2\.

3\.

•

•

•

1\.

2\.

3\.

4\.

•

SICOP CONNECT · Guía de aprendizaje y ejecución C O N F I D E N C I A L

Hermatix M2M Communication S.R.L. · Documento confidencial — uso interno. Prohibida su distribución sin autorización. Página 38 de 69

CONFIDENCIAL☐ Correo real recibido desde el servidor.

☐ Timer activo con próxima ejecución verificada.

☐ Reinicio sin pérdida de datos.

☐ Reto de comprensión de la semana superado (sección 20.3).

Autoevaluación

¿Qué sigue funcionando si apagas tu computadora? ¿Qué no?

¿Qué hace exactamente el servidor a las 07:00?

¿Por qué el timer se activa al final y no al principio?

Entregas: piloto en producción · propuesta priorizada de ampliaciones · métricas de la semana · commit.

Claude: 3–6 encargos.

13\. Semana 3 — Ampliaciones de valor

Meta de la semana: convertir el piloto en una herramienta comercial más completa, con las ampliaciones que

Oscar eligió. Conceptos de la semana: evaluación técnica con límite de tiempo, análisis de datos, métricas de

calidad, actualización en producción. Capacidad de Claude estimada: 50–70 encargos.

Regla de la semana: cada ampliación tiene un día como límite. Si al final del día no cumple su criterio, se

documenta el estado y se pasa a la siguiente. Todas se desarrollan en Windows y se publican juntas el viernes con el

procedimiento de actualización (sección 17.6). El orden puede cambiar según lo que Oscar decidió el día 10.

Lección 11 · lunes 19 de octubre — ¿Se puede automatizar la descarga? (A1)

Objetivo: una decisión documentada y basada en evidencia sobre si la descarga de SICOP puede automatizarse,

y cómo.

Para qué sirve: hoy alguien descarga los archivos a mano. Si se automatiza, el sistema funciona sin intervención.

Pero automatizar algo que el portal no permite, o que se rompe cada semana, es peor que no hacerlo. Por eso hoy

se evalúa antes de construir.

Lo que necesitas entender

Prueba de concepto con límite de tiempo (spike): investigación corta para reducir incertidumbre. Su resultado

es una decisión, no necesariamente código.

Registro de decisión: documento con el problema, las opciones, la evidencia, los riesgos y la recomendación.

Es como trabajan los equipos profesionales para que las decisiones no se pierdan.

Límites éticos y legales: no se eluden códigos de validación, CAPTCHA ni términos de uso. «No es viable sin

intervención humana» es un resultado válido.

Paso a paso

•

•

•

•

1\.

2\.

3\.

•

•

•

SICOP CONNECT · Guía de aprendizaje y ejecución C O N F I D E N C I A L

Hermatix M2M Communication S.R.L. · Documento confidencial — uso interno. Prohibida su distribución sin autorización. Página 39 de 69

CONFIDENCIALHora Paso Quién

08:15–

09:30

1\. Revisar ACCESO\_SICOP.md (dos semanas de descargas): ¿qué paso exige a una persona? Revisar con

Oscar los términos de uso del portal

Tú +

Oscar

09:30–

12:00

2\. Evaluación técnica con Claude (encargo abajo) Tú +

Claude

13:15–

15:30

3\. Si Oscar aprueba una opción viable: prototipo mínimo, desactivado por defecto. Si no: mejorar el modo

asistido (por ejemplo, avisar cuando llegue el correo de SICOP)

Tú +

Claude

15:30–

17:00

4\. Escribir docs/DECISION\_OBTENCION.md Tú

Encargo para Claude

CONTEXTO: docs/ACCESO\_SICOP.md y sección 16.1 de la guía.

TAREA: evaluar opciones para automatizar la obtención SIN eludir controles.

1\. Analiza el flujo registrado (solicitud, código por correo, enlace).

2\. Propón opciones ordenadas por robustez: API documentada (si hay evidencia),

&#x20;lectura del buzón empresarial para el enlace, navegador automatizado.

3\. Para cada una: qué requiere, qué puede romperse, si exige intervención humana

&#x20;y riesgos de términos de uso. No eludas CAPTCHA ni validaciones.

4\. Si Oscar aprueba una opción, implementa el prototipo mínimo detrás de

&#x20;SOURCE\_MODE, desactivado por defecto, con pruebas sobre datos simulados

&#x20;marcados como tales.

No declares «automático» hasta que un ciclo real lo demuestre.

Comprobación: DECISION\_OBTENCION.md con opciones, evidencia, riesgos y recomendación aceptada por

Oscar.

Autoevaluación: ¿Por qué un resultado «no viable» también tiene valor? ¿Qué riesgo tendría un adaptador que

se rompe sin avisar?

Claude: 8–14 encargos (el día más variable del plan).

Lección 12 · martes 20 de octubre — ¿Quién gana qué? (A2)

Objetivo: una vista de inteligencia competitiva: en cada familia de producto, qué empresas ganan contratos

públicos, con qué instituciones y por qué montos.

Para qué sirve: saber dónde ganan competidores como Navsat, Skydata o Stremax ayuda a Hermatix a decidir

dónde ofertar, qué precios son de referencia y qué instituciones ya compran estas soluciones. Es información

estratégica que hoy no se tiene ordenada.

Lo que necesitas entender: los carteles son lo que se pide; las adjudicaciones son lo que se otorgó y a quién.

Los nombres de empresas varían («NAVSAT S.A.», «Navsat Sociedad Anónima»); una tabla de alias los unifica.

Paso a paso

Hora Paso Quién

08:15–09:00 1. Identificar en el diccionario el reporte de adjudicaciones o contratos y descargar una muestra real Tú

09:00–12:00 2. Importador y vista de competencia (encargo abajo) Tú + Claude

SICOP CONNECT · Guía de aprendizaje y ejecución C O N F I D E N C I A L

Hermatix M2M Communication S.R.L. · Documento confidencial — uso interno. Prohibida su distribución sin autorización. Página 40 de 69

CONFIDENCIALHora Paso Quién

13:15–15:00 3. Validar con Oscar: ¿aparecen los competidores que él conoce? Completar alias Tú + Oscar

15:00–17:00 4. Correcciones, commit, bitácora Tú

Encargo para Claude

TAREA: módulo de inteligencia competitiva.

\- Importa el reporte real de adjudicaciones/contratos (mapeo en MAPEO\_DATOS.md;

&#x20;si el campo de adjudicatario no existe, detente y repórtalo).

\- Aplica las mismas reglas de familia a lo adjudicado (histórico).

\- Página protegida «Competencia»: por familia, quién gana, cuántas veces, con qué

&#x20;instituciones y montos adjudicados por moneda; filtro por periodo.

\- config/competidores.yaml para unificar nombres (alias → competidor),

&#x20;editable por Hermatix.

CRITERIO: cifras rastreables al registro original; montos nunca mezclan monedas.

Comprobación: Oscar reconoce el panorama competitivo en al menos dos familias y lo considera útil.

Autoevaluación: ¿Cuál es la diferencia entre un cartel y una adjudicación? ¿Por qué hace falta una tabla de

alias?

Claude: 6–10 encargos.

Lección 13 · miércoles 21 de octubre — Medir cuánto acierta el sistema (A3)

Objetivo: un comando y una página que midan la precisión y la cobertura de las reglas usando las decisiones

reales de Hermatix.

Para qué sirve: «las reglas parecen funcionar» no es una respuesta profesional. Con métricas, Hermatix sabe

cuánto confiar en una alerta, y cada ajuste de reglas puede demostrar si mejoró o empeoró.

Lo que necesitas entender

Precisión: de 10 alertas, ¿cuántas interesaban? Si es baja, el correo tiene ruido.

Cobertura: de 10 oportunidades que interesaban, ¿cuántas alertó? Si es baja, se pierden negocios.

Mejorar una suele empeorar la otra; el equilibrio lo decide Oscar según el costo de cada error.

Paso a paso

Hora Paso Quién

08:15–11:00 1. Comando score-rules y página de calidad (encargo abajo) Tú + Claude

11:00–12:00 2. Analizar falsos positivos y oportunidades perdidas de la semana 2 Tú

13:15–15:30 3. Ajustar el YAML a mano, prediciendo y midiendo antes/después Tú + Claude

15:30–17:00 4. Agregar a REGLAS.md el procedimiento de mejora continua Tú

Encargo para Claude

TAREA: score-rules y página «Calidad de reglas».

\- Compara las predicciones con el golden set y las revisiones humanas acumuladas.

•

•

•

SICOP CONNECT · Guía de aprendizaje y ejecución C O N F I D E N C I A L

Hermatix M2M Communication S.R.L. · Documento confidencial — uso interno. Prohibida su distribución sin autorización. Página 41 de 69

CONFIDENCIAL- Por familia: precisión, cobertura y lista de errores con su evidencia.

\- Guarda cada medición con la versión de reglas para ver la evolución.

CRITERIO: un cambio en el YAML se refleja en la siguiente medición.

CIERRE: explícame precisión y cobertura con un caso real de nuestros datos.

Comprobación: métricas por familia antes y después del ajuste; tu predicción comparada con el resultado.

Autoevaluación: Explica con un caso real la diferencia entre precisión y cobertura. Si Oscar prefiere no perder

ninguna oportunidad, ¿qué métrica priorizas?

Claude: 5–8 encargos.

Lección 14 · jueves 22 de octubre — Que ninguna oportunidad venza sin decisión (A4 y A5)

Objetivo: alertas de cierre próximo, un resumen ejecutivo semanal y exportación a Excel del listado filtrado.

Para qué sirve: detectar una oportunidad no basta; hay que decidir a tiempo. Las alertas de cierre evitan que

una oportunidad marcada «Interesa» se venza olvidada. El resumen semanal da a la gerencia una vista rápida. La

exportación permite compartir con ventas sin dar acceso al panel.

Paso a paso

Hora Paso Quién

08:15–11:00 1. Alertas de cierre y resumen semanal (encargo A4) Tú + Claude

11:00–12:00 2. Revisar la redacción con Oscar Tú + Oscar

13:15–14:45 3. Exportación a Excel (encargo A5) Tú + Claude

14:45–17:00 4. Pruebas integrales de todas las ampliaciones; versión candidata Tú

Encargos para Claude

TAREA A4: (1) aviso cuando una oportunidad marcada «Interesa» o «Revisar

requisitos» cierra en ≤ N días sin decisión final; (2) resumen ejecutivo

semanal (lunes): nuevas oportunidades por familia, revisadas, pendientes,

próximos cierres y, si existe, adjudicaciones relevantes. Reutiliza outbox

y deduplicación; dry-run por defecto; motivo nuevo en la clave de deduplicación.

TAREA A5: botón «Exportar a Excel» que respete los filtros activos. Los IDs

deben quedar como texto en la hoja (que Excel no los convierta en número).

Comprobación: vista previa de ambos correos aprobada por Oscar; el Excel exportado abre con los códigos de

24 dígitos intactos.

Autoevaluación: ¿Por qué la alerta de cierre necesita un motivo distinto en la clave de deduplicación? ¿Cómo

evitaste que Excel dañara los códigos?

Claude: 7–11 encargos.

SICOP CONNECT · Guía de aprendizaje y ejecución C O N F I D E N C I A L

Hermatix M2M Communication S.R.L. · Documento confidencial — uso interno. Prohibida su distribución sin autorización. Página 42 de 69

CONFIDENCIALLección 15 · viernes 23 de octubre — Actualizar producción sin riesgo · HITO 3

Objetivo: publicar en el servidor todas las ampliaciones aceptadas usando el procedimiento de actualización,

sin perder datos.

Para qué sirve: un sistema real se actualiza muchas veces. Hacerlo con un procedimiento (respaldar, detener,

instalar, migrar, verificar, reactivar) es lo que separa un cambio controlado de un accidente.

Paso a paso

Hora Paso Quién

08:15–09:30 1. A6 (importar XLSX/JSON) solo si SICOP los entrega de forma más confiable; si no, se omite Tú + Claude

09:30–12:00 2. Actualización en servidor con la sección 17.6 Tú + Oscar

13:15–15:00 3. Verificar cada ampliación en producción Tú

15:00–16:00 4. Plan vs. real de la semana; propuesta para la semana 4 Tú

16:00–16:30 Revisión semanal 3 Tú + Oscar

Comprobación — HITO 3

☐ Al menos tres ampliaciones aceptadas y funcionando en el servidor.

☐ Actualización con respaldo previo y sin pérdida de datos.

☐ Reto de comprensión de la semana superado.

Autoevaluación: Enumera de memoria los pasos de una actualización y explica qué protege cada uno.

Claude: 3–6 encargos.

14\. Semana 4 — Operación resiliente y transferencia

Meta de la semana: demostrar que Hermatix puede confiar en el sistema y mantenerlo sin ti. Conceptos de la

semana: recuperación ante fallos, reversión, documentación operativa, comunicación ejecutiva. Capacidad de

Claude estimada: 25–40 encargos.

Lección 16 · lunes 26 de octubre — Simulacro: ¿qué pasa si algo se rompe?

Objetivo: comprobar en el servidor que el sistema se recupera de reinicios, fallos de la fuente, pérdida de la

base y una actualización fallida.

Para qué sirve: igual que un simulacro de incendio, se practica la recuperación cuando no hay emergencia. Un

respaldo que nunca se restauró es solo una esperanza.

Paso a paso (sesión con Oscar y el administrador)

•

•

•

SICOP CONNECT · Guía de aprendizaje y ejecución C O N F I D E N C I A L

Hermatix M2M Communication S.R.L. · Documento confidencial — uso interno. Prohibida su distribución sin autorización. Página 43 de 69

CONFIDENCIALHora Paso

08:15–

10:15

1\. Reiniciar el servicio · reiniciar el servidor en ventana acordada · ciclo con fuente fallida (sección 18, simulacros 1, 2

y 4)

10:15–

12:00

2\. Restaurar un respaldo en un directorio aislado y leer una revisión conocida (simulacro 3)

13:15–

15:00

3\. Reversión: volver a la versión del día 10 y regresar a la actual (sección 17.6)

15:00–

17:00

4\. Documentar resultados en OPERACION.md ; corregir lo que falló, con Claude si hace falta

Comprobación: los cinco simulacros de la sección 18 con evidencia registrada.

Autoevaluación: Si mañana se daña la base, ¿qué haces, en qué orden y en qué máquina?

Claude: 3–6 encargos.

Lección 17 · martes 27 de octubre — Mejorar con lo que dijeron los usuarios

Objetivo: implementar las 3–5 mejoras de mayor valor y menor riesgo que pidieron quienes usaron el sistema.

Para qué sirve: después de dos semanas de uso real aparecen necesidades que nadie previó. Escuchar a los

usuarios y priorizar es una competencia clave de cualquier profesional de software.

Paso a paso

Hora Paso Quién

08:15–09:00 1. Recoger retroalimentación de Oscar y del equipo comercial; clasificar por valor y esfuerzo Tú

09:00–12:00 2. Implementar las mejoras elegidas (encargo abajo) Tú + Claude

13:15–15:00 3. Probar y actualizar el servidor con la sección 17.6 Tú + Oscar

15:00–17:00 4. Listar lo no implementado, con estimación, para el plan de continuidad Tú

Encargo para Claude

CONTEXTO: docs/ESTADO\_PROYECTO.md y esta retroalimentación: \[pegar].

TAREA: implementa SOLO estas mejoras, en este orden, una por commit: \[1…5].

Para cada una: cambio mínimo, prueba y nota en ESTADO\_PROYECTO.md.

No cambies arquitectura ni dependencias. Si una mejora requiere más que un

cambio pequeño, detente y descríbela como pendiente para el plan de continuidad.

Comprobación: mejoras desplegadas y verificadas; pendientes listados con estimación.

Claude: 8–12 encargos.

SICOP CONNECT · Guía de aprendizaje y ejecución C O N F I D E N C I A L

Hermatix M2M Communication S.R.L. · Documento confidencial — uso interno. Prohibida su distribución sin autorización. Página 44 de 69

CONFIDENCIALLección 18 · miércoles 28 de octubre — Dejar todo documentado

Objetivo: documentación verificada contra el código real, con la que otra persona pueda instalar, operar y

recuperar el sistema.

Para qué sirve: el proyecto debe sobrevivir a tu práctica. Si la documentación dice un comando que ya no

existe, en una emergencia nadie podrá recuperar el sistema.

Paso a paso

Hora Paso Quién

08:15–11:00 1. Auditoría de documentación (encargo abajo) Tú + Claude

11:00–12:00 2. Seguir OPERACION.md literalmente en una instalación limpia; corregir donde te trabes Tú

13:15–17:00 3. Redactar el informe final con tus palabras (sección 21.3); diagramas Tú

Encargo para Claude

TAREA: auditoría de documentación. Compara README.md, OPERACION.md,

DESPLIEGUE.md, REGLAS.md y ARQUITECTURA.md con el código y los comandos reales.

Lista las discrepancias (comando inexistente, opción renombrada, paso faltante)

y corrígelas. Completa ARQUITECTURA.md con el diagrama de la sección 15.1

actualizado. No inventes resultados: marca «pendiente de verificar» lo que no

puedas comprobar localmente.

Comprobación: una persona que no participó podría instalar, operar y recuperar el sistema solo con los

manuales.

Claude: 4–7 encargos.

Lección 19 · jueves 29 de octubre — Medir resultados y ensayar

Objetivo: las métricas del mes calculadas y la presentación final ensayada.

Para qué sirve: Hermatix necesita saber qué obtuvo: cuántas oportunidades, con qué calidad, cuánto tiempo

ahorró y cuánto rindió realmente Claude. Con eso decidirá cómo continuar.

Paso a paso

Hora Paso

08:15–10:00 1. Calcular las métricas de la sección 22

10:00–12:00 2. Reserva: cerrar cualquier pendiente crítico

13:15–15:00 3. Preparar la presentación de 20 minutos (sección 21.2)

15:00–16:30 4. Ensayo completo con demostración en vivo, cronometrado

16:30–17:00 5. Bitácora

Comprobación: métricas completas; ensayo dentro de 20 minutos; demo funcionando con datos reales.

SICOP CONNECT · Guía de aprendizaje y ejecución C O N F I D E N C I A L

Hermatix M2M Communication S.R.L. · Documento confidencial — uso interno. Prohibida su distribución sin autorización. Página 45 de 69

CONFIDENCIALClaude: 0–6 encargos (reserva).

Lección 20 · viernes 30 de octubre — Presentar y entregar · HITO 4

Objetivo: presentar el proyecto, entregar formalmente y acordar el plan de las próximas 160 horas.

Paso a paso

Hora Paso Quién

08:15–10:00 1. Verificar que el ciclo de hoy corrió en el servidor; últimos ajustes Tú

10:00–11:00 2. Presentación final (20 min) y preguntas (40 min) Tú + Oscar (+ supervisor académico)

11:00–12:00 3. Acta de entrega: cumplido, parcial, pendientes con responsable Tú + Oscar

13:15–15:00 4. Plan de continuidad (sección 23.2), estimado con los datos del mes Tú

15:00–16:00 5. Confirmar que nada depende de tu cuenta de Claude Tú + Oscar

16:00–16:30 Revisión semanal 4 y cierre del bloque Tú + Oscar

16:30–17:00 6. Bitácora final y registro de horas Tú

Comprobación — HITO 4

☐ Sistema en producción con dos semanas de uso real.

☐ Recuperación probada, documentación verificada, métricas presentadas.

☐ Plan de continuidad aceptado.

☐ Reto final: explicas a Oscar cómo reiniciar el servicio y recuperar un respaldo, distinguiendo Mac y servidor.

•

•

•

•

SICOP CONNECT · Guía de aprendizaje y ejecución C O N F I D E N C I A L

Hermatix M2M Communication S.R.L. · Documento confidencial — uso interno. Prohibida su distribución sin autorización. Página 46 de 69

CONFIDENCIALPARTE IV · REFERENCIA TÉCNICA

15\. Arquitectura del piloto

15.1. Vista general

Una sola aplicación Python, sin microservicios. El panel y el ciclo programado comparten la base de datos, pero el

ciclo corre como comando separado disparado por el programador del servidor: nunca se inicia un programador

dentro del proceso web (podría duplicar envíos).

15.2. Componentes

Componente Tecnología Responsabilidad

Backend y panel FastAPI + Jinja2 + HTML/CSS Rutas web, formularios, sesiones

Almacenamiento SQLite con migraciones versionadas Datos, revisiones, outbox, auditoría

de cargas

Obtención Adaptador manual (carpeta de entrada / carga en panel); adaptador

automático solo si A1 lo valida

Llevar archivos completos a la app

Reglas config/hermatix\_rules.yaml + Python Coincidencias con evidencia,

prioridad y familia

Avisos Adaptador de correo (SMTP o API del proveedor) Vista previa, envío explícito,

deduplicación

Operación CLI python -m app.cli + systemd Ciclo diario, respaldo, diagnóstico

15.3. Estructura del repositorio

sicop-connect/

&#x20;SICOP\_CONNECT\_RETO\_4\_SEMANAS.md CLAUDE.md README.md

&#x20;pyproject.toml requirements.txt requirements-dev.txt requirements.lock.txt

&#x20;.env.example .gitignore

&#x20;app/

&#x20;main.py cli.py config.py database.py

SICOP CONNECT · Guía de aprendizaje y ejecución C O N F I D E N C I A L

Hermatix M2M Communication S.R.L. · Documento confidencial — uso interno. Prohibida su distribución sin autorización. Página 47 de 69

CONFIDENCIAL sources/ importers/ matching/ notifications/ web/

&#x20;templates/ static/

&#x20;migrations/

&#x20;config/hermatix\_rules.yaml

&#x20;tests/ tests/fixtures/ tests/golden/

&#x20;docs/

&#x20;ESTADO\_PROYECTO.md BITACORA.md ACCESO\_SICOP.md MAPEO\_DATOS.md

&#x20;REGLAS.md OPERACION.md DESPLIEGUE.md ARQUITECTURA.md referencias/

&#x20;data/ incoming/ raw/ exports/ (fuera de Git)

&#x20;deploy/ systemd/ (plantillas sin secretos)

requirements.txt lista dependencias directas; requirements-dev.txt agrega herramientas de desarrollo;

requirements.lock.txt congela las versiones probadas para el servidor, generado desde un entorno limpio.

15.4. Configuración

.env.example (versionado, sin secretos). El .env real solo existe localmente; en el servidor, las variables vienen de

/etc/sicop-connect/app.env .

APP\_ENV=development

APP\_TIMEZONE=America/Costa\_Rica

DATABASE\_PATH=data/sicop.db

RAW\_DATA\_DIR=data/raw

INCOMING\_DIR=data/incoming

SOURCE\_MODE=manual

AI\_MODE=none

NOTIFICATIONS\_ENABLED=false

NOTIFICATIONS\_DRY\_RUN=true

SCHEDULER\_ENABLED=false

MAIL\_PROVIDER=unconfigured

MAIL\_FROM=

MAIL\_TO=

SESSION\_SECRET=

15.5. Comandos que la aplicación debe ofrecer

Comando Resultado esperado

python -m app.cli doctor Configuración disponible y pendiente, sin revelar secretos

python -m app.cli migrate Crea o actualiza el esquema con migraciones versionadas

python -m app.cli import --path ARCHIVO

\--report carteles

Importa y reporta aceptados, rechazados y advertencias ( carteles ,

lineas , catalogo , instituciones )

python -m app.cli evaluate Evalúa con las reglas vigentes

python -m app.cli score-rules (A3) Precisión y cobertura frente al conjunto etiquetado

python -m app.cli notify --dry-run / --

send

Vista previa sin envío / envío explícito habilitado

python -m app.cli run-cycle --dry-run /

\--send

Recoge → importa → evalúa → prepara/envía, con bloqueo antisuperposición

python -m app.cli backup --output RUTA Respaldo consistente de SQLite con manifiesto

SICOP CONNECT · Guía de aprendizaje y ejecución C O N F I D E N C I A L

Hermatix M2M Communication S.R.L. · Documento confidencial — uso interno. Prohibida su distribución sin autorización. Página 48 de 69

CONFIDENCIALComando Resultado esperado

python -m app.cli create-user Crea un usuario del panel pidiendo la contraseña de forma interactiva

python -m uvicorn app.main:app --

reload

Panel en modo desarrollo

16\. La fuente: SICOP, datos y reglas comerciales

16.1. Qué sabemos de SICOP y qué falta comprobar

El punto de partida es el módulo de datos abiertos de SICOP. La guía del ICD describe una solicitud con filtros y

formato, el ingreso de un correo, un código de confirmación y un enlace de descarga enviado a ese correo. No se ha

verificado una API pública documentada. La dirección del módulo y las llamadas internas que hace el navegador

no equivalen a una API autorizada ni estable.

Resultado posible de la prueba Implementación Nivel que se puede declarar

API oficial documentada y accesible Adaptador que consulta, registra cobertura

y guarda originales

Obtención automática, una vez

probado el ciclo completo

Flujo web/correo automatizable y

permitido por los términos

Adaptador con navegador y lectura del

buzón

Automática, tras pruebas reales de

errores y vencimientos

Requiere validación humana en cada

solicitud

Una persona descarga; la app hace todo lo

demás

Obtención asistida; análisis y avisos

automáticos

Un agente de IA no elimina un código de validación por correo, un CAPTCHA ni un límite del portal. El modo asistido

ya entrega valor comercial; la automatización total es la ampliación A1, con tiempo acotado.

16.2. Procedimiento de prueba con archivo real (día 1 tarde, con Oscar)

Abre el portal en un navegador normal; revisa reportes, filtros y formatos disponibles.

Para oportunidades nuevas solicita carteles/pliegos (y sus líneas), no solo contratos adjudicados.

Usa una ventana de fechas pequeña (por ejemplo, últimos 30 días) sin filtrar por institución: el filtro del ICD en

su guía es un ejemplo propio de esa entidad.

Usa el buzón empresarial designado; ingresa el código recibido y sigue el enlace.

Anota: ¿cada solicitud exige un código nuevo?, ¿cuánto demora el correo?, ¿vence el enlace? No guardes

códigos ni enlaces privados en Git.

Guarda el archivo original sin abrirlo y volverlo a guardar en Excel: Excel puede convertir identificadores de 24

dígitos en notación científica y destruirlos.

Registra formato, encabezados, filas, filtros y fecha de obtención en docs/ACCESO\_SICOP.md .

Solicita también líneas, catálogo de códigos e instituciones. Si existe un reporte de adjudicaciones/contratos,

descárgalo para A2.

Repite la solicitud otro día para observar el comportamiento; una sola descarga no demuestra estabilidad.

1\.

2\.

3\.

4\.

5\.

6\.

7\.

8\.

9\.

SICOP CONNECT · Guía de aprendizaje y ejecución C O N F I D E N C I A L

Hermatix M2M Communication S.R.L. · Documento confidencial — uso interno. Prohibida su distribución sin autorización. Página 49 de 69

CONFIDENCIALLas preguntas para soporte de SICOP se registran; Hermatix decide si las envía. Claude nunca envía mensajes

por iniciativa propia.

16.3. Datos y reglas de calidad

Un cartel tiene su identificación, título y fechas; sus líneas dicen qué se compra, a veces solo con un código que se

traduce con el catálogo. Unir esas piezas evita perder oportunidades cuyo título es genérico («Contratación de

servicios varios»).

Reporte del diccionario Campos de referencia Uso

2\. Detalle carteles NRO\_SICOP , NRO\_PROCEDIMIENTO , CEDULA\_INSTITUCION ,

DESCRIPCION , FECHA\_PUBLICACION , FECHA\_INICIO\_RECEPCION ,

FECHA\_CIERRE\_RECEPCION

Identificar la compra y

su plazo

2.1. Detalle líneas de

carteles

NRO\_SICOP , NUMERO\_LINEA , NUMERO\_PARTIDA ,

CODIGO\_IDENTIFICACION , CANTIDAD\_SOLICITADA ,

PRECIO\_UNITARIO\_ESTIMADO , TIPO\_MONEDA

Qué se compra y

estimación por línea

10.2. Códigos de

identificación

CODIGO\_IDENTIFICACION , CODIGO\_CLASIFICACION ,

NOMBRE\_IDENTIFICACIÓN

Nombre del bien o

servicio

11\. Instituciones

compradoras

CEDULA , NOMBRE\_INSTITUCION Mostrar el comprador

1\. Solicitud de

contratación

(complementario)

IDENTIFICADOR , CARTEL\_NO , INST\_CARTEL\_NO , PRESUPUESTO ,

MONEDA , FINALIDAD\_PUBLICA

Complementar cuando

la relación se

compruebe

Los encabezados reales pueden diferir del diccionario: el mapeo vive explícito en docs/MAPEO\_DATOS.md y en

código, y el archivo original se conserva.

Reglas de calidad que Ivania debe poder explicar:

Identificadores como texto. Clasificación, identificación y producto usan 8, 16 y 24 dígitos. Un código truncado

por Excel no se puede reconstruir: se registra y se pide un archivo sin pérdida.

Uniones solo por claves verificadas ( NRO\_SICOP y secuencia; código de catálogo; cédula de institución). Nunca

por parecido del título.

Versiones. El ERD menciona NRO\_SEQ\_SICOP ; si viene, se conserva. Si no, se guardan instantáneas con hash de

contenido (detecta cambios, pero no es una secuencia oficial).

Dinero. Decimal con moneda; cantidad × precio unitario es una estimación por línea, no el presupuesto ni el

monto adjudicado.

Fechas y estado. Se interpreta la zona de la fuente y se muestra hora de Costa Rica. Una fecha de cierre futura

no prueba que el concurso siga activo: si el estado no se conoce, se muestra «estado por verificar». ESTADO del

reporte de ofertas es de la oferta, no del procedimiento.

Cobertura. Cada obtención registra cuándo, con qué filtros y qué periodo cubre. Un fallo de descarga es un

fallo de datos, no «cero oportunidades».

Historial. Una actualización nunca borra comentarios ni decisiones humanas.

Tablas internas mínimas: source\_runs (obtenciones y cobertura), imports y raw\_snapshots (archivo, hash,

aceptadas/rechazadas), institutions , catalog\_items , tenders , tender\_lines , opportunity\_assessments

10\.

•

•

•

•

•

•

•

SICOP CONNECT · Guía de aprendizaje y ejecución C O N F I D E N C I A L

Hermatix M2M Communication S.R.L. · Documento confidencial — uso interno. Prohibida su distribución sin autorización. Página 50 de 69

CONFIDENCIAL(regla, evidencia, prioridad), reviews (decisión humana), notification\_outbox (aviso, destinatario, estado, clave

de deduplicación), users .

16.4. Familias comerciales alineadas al portafolio de Hermatix

Son semillas que Oscar confirma el día 2 y ajusta con ejemplos reales. No afirman que Hermatix cumpla los

requisitos de cada compra.

Familia Producto Hermatix

de referencia Señales de ejemplo Falsos positivos típicos

GPS / AVL / gestión

de flotas

FleetMatix rastreo vehicular, monitoreo de flotas,

localización satelital de vehículos, AVL, control

de combustible

GPS topográfico, GPS de mano,

levantamiento catastral

Videotelemática Fenova IA cámaras vehiculares, dashcam, MDVR, video a

bordo, grabación en unidades

cámaras de edificio, CCTV

perimetral, videovigilancia

urbana fija

Seguridad vial y

conductor

Fenova IA /

soluciones de

seguridad

ADAS, DMS/DSM, fatiga, distracción,

anticolisión, puntos ciegos

radar meteorológico, radar de

velocidad fijo de tránsito

(revisar)

Conteo y analítica de

pasajeros

PassengerIQ conteo de pasajeros, contador automático,

ocupación de buses, validación de pasajeros,

transporte público

conteo de inventario, control de

asistencia de personal

Transporte

corporativo

MoveOn transporte de personal, rutas de colaboradores,

gestión de transporte institucional

servicio de taxi individual

Rastreo de activos SmartTags rastreo de activos, etiquetas, BLE, trazabilidad

de equipos, contenedores

etiquetas de inventario

impresas, código de barras

Mantenimiento de

flotas

FleetRun software de mantenimiento vehicular, control de

flota, órdenes de taller

repuestos o reparación

mecánica sin software

IoT / telemetría y

cadena de frío

Soluciones IoT sensores de temperatura, telemetría, LoRaWAN,

monitoreo remoto, CAN bus, identificación de

conductor RFID

sensores de laboratorio sin

monitoreo remoto

Las reglas buscan en título y líneas, normalizan mayúsculas y acentos pero guardan el texto original, y combinan

señales positivas con exclusiones por contexto. La salida separa cuatro dimensiones:

Dimensión Valores

Encaje comercial Alta · Media · Baja · Sin coincidencia

Plazo / estado Abierto · Cierra en ≤ 7 días · Vencido · Por verificar

Requisitos Viabilidad pendiente (por defecto) · Revisado

Calidad de datos Completo · Sin líneas · Código sin catálogo · Archivo parcial

SICOP CONNECT · Guía de aprendizaje y ejecución C O N F I D E N C I A L

Hermatix M2M Communication S.R.L. · Documento confidencial — uso interno. Prohibida su distribución sin autorización. Página 51 de 69

CONFIDENCIALEjemplo sintético: «Servicio de monitoreo GPS de vehículos institucionales» → Alta, FleetMatix, evidencia

«monitoreo GPS de vehículos». «Adquisición de GPS para levantamiento topográfico» → Sin coincidencia por

exclusión «topográfico». La diferencia se explica sin IA.

16.5. Conjunto de prueba etiquetado («golden set»)

El día 3, Oscar etiqueta entre 20 y 40 carteles reales: interesa, no interesa o falso positivo conocido. Se guardan en

tests/golden/ (solo identificadores, títulos y etiqueta; nada confidencial). Este conjunto convierte «las reglas

parecen funcionar» en una cifra: porcentaje de acierto, que es el criterio O3 y la base de la ampliación A3.

17\. Despliegue en el servidor de Hermatix

Ruta de referencia para Linux con systemd y un proxy HTTPS existente. El administrador confirma el sistema

operativo el día 6; si es distinto, adapta servicios y programador (no se pegan comandos de Linux en otro sistema).

El servidor no necesita Claude: ejecuta Python, SQLite y el programador.

17.1. Dónde se ejecuta cada cosa

Lugar Responsable Qué se hace

Windows de Ivania Ivania Desarrollar, probar, documentar, publicar el

commit revisado

Mac de Oscar, terminal local Oscar + Ivania Obtener ese commit, empaquetar y transferir

Servidor, terminal remota tras

ssh

Oscar / administrador; Ivania ejecuta guiada

y registra

Instalar, configurar, migrar, arrancar, comprobar

Después de ssh , la terminal de la Mac se ve igual pero actúa sobre el servidor. Antes de cada comando, Ivania

dice en voz alta en qué máquina está.

17.2. Secuencia Windows → Mac → servidor

Paso 1 — Windows: publicar el commit revisado en el repositorio privado autorizado. Confirmar que no se

versionan .env , .venv , datos, bases, respaldos ni documentos personales.

git status

git log -1 --oneline

git rev-parse HEAD

git push -u origin NOMBRE\_RAMA

Paso 2 — Mac: verificar herramientas. git --version y ssh -V . El administrador entrega usuario/host y

configura el método de acceso; claves y contraseñas las maneja Oscar, nunca se pegan en Claude.

Paso 3 — Mac: obtener exactamente la versión revisada.

SICOP CONNECT · Guía de aprendizaje y ejecución C O N F I D E N C I A L

Hermatix M2M Communication S.R.L. · Documento confidencial — uso interno. Prohibida su distribución sin autorización. Página 52 de 69

CONFIDENCIALgit clone URL\_REPOSITORIO\_AUTORIZADO sicop-connect # o: cd sicop-connect \&\& git fetch origin

cd sicop-connect

git checkout COMMIT\_REVISADO

git rev-parse HEAD # debe coincidir con el hash de Windows

Paso 4 — Mac: empaquetar y transferir.

git archive --format=tar.gz --output=../sicop-connect-release.tar.gz COMMIT\_REVISADO

shasum -a 256 ../sicop-connect-release.tar.gz

scp ../sicop-connect-release.tar.gz USUARIO@HOST:/tmp/sicop-connect-release.tar.gz

ssh USUARIO@HOST

Paso 5 — Servidor: verificar e instalar.

hostname \&\& whoami

sha256sum /tmp/sicop-connect-release.tar.gz # debe coincidir con el de la Mac

El administrador crea el usuario de servicio sicop (sin privilegios) y las rutas: /opt/sicop-connect (código),

/var/lib/sicop-connect (base, originales, entrada), /etc/sicop-connect (configuración privada). Primera

instalación:

sudo tar -xzf /tmp/sicop-connect-release.tar.gz -C /opt/sicop-connect

sudo chown -R sicop:sicop /opt/sicop-connect

cd /opt/sicop-connect

sudo -u sicop python3 -m venv .venv

sudo -u sicop .venv/bin/python -m pip install -r requirements.lock.txt

Nunca se ejecuta la app como root ni con --reload en el servidor.

Paso 6 — Cerrar sesión con exit y registrar en el acta: commit, hash del paquete, servidor, responsables,

comandos, resultados y pendientes. Sin claves ni contraseñas.

17.3. Configuración persistente

El administrador crea /etc/sicop-connect/app.env (propietario sicop , permisos 600 ):

APP\_ENV=production

APP\_TIMEZONE=America/Costa\_Rica

DATABASE\_PATH=/var/lib/sicop-connect/sicop.db

RAW\_DATA\_DIR=/var/lib/sicop-connect/raw

INCOMING\_DIR=/var/lib/sicop-connect/incoming

SOURCE\_MODE=manual

AI\_MODE=none

NOTIFICATIONS\_ENABLED=false

NOTIFICATIONS\_DRY\_RUN=true

SCHEDULER\_ENABLED=false

MAIL\_PROVIDER=unconfigured

MAIL\_FROM=

MAIL\_TO=

SESSION\_SECRET=

Los valores reales de correo y sesión los coloca el administrador. No se rellenan valores ficticios para que doctor

«salga bien».

SICOP CONNECT · Guía de aprendizaje y ejecución C O N F I D E N C I A L

Hermatix M2M Communication S.R.L. · Documento confidencial — uso interno. Prohibida su distribución sin autorización. Página 53 de 69

CONFIDENCIAL17.4. Servicios systemd

/etc/systemd/system/sicop-web.service :

\[Unit]

Description=Panel SICOP CONNECT

After=network.target

\[Service]

Type=simple

User=sicop

Group=sicop

WorkingDirectory=/opt/sicop-connect

EnvironmentFile=/etc/sicop-connect/app.env

ExecStart=/opt/sicop-connect/.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port

8000 --workers 1 --proxy-headers

Restart=on-failure

RestartSec=5

UMask=0077

\[Install]

WantedBy=multi-user.target

/etc/systemd/system/sicop-migrate.service :

\[Unit]

Description=Migraciones SICOP CONNECT

\[Service]

Type=oneshot

User=sicop

Group=sicop

WorkingDirectory=/opt/sicop-connect

EnvironmentFile=/etc/sicop-connect/app.env

ExecStart=/opt/sicop-connect/.venv/bin/python -m app.cli migrate

UMask=0077

/etc/systemd/system/sicop-cycle.service (empieza en dry-run):

\[Unit]

Description=Ciclo SICOP CONNECT

After=network-online.target

Wants=network-online.target

\[Service]

Type=oneshot

User=sicop

Group=sicop

WorkingDirectory=/opt/sicop-connect

EnvironmentFile=/etc/sicop-connect/app.env

ExecStart=/opt/sicop-connect/.venv/bin/python -m app.cli run-cycle --dry-run

UMask=0077

/etc/systemd/system/sicop-cycle.timer (07:00 de Costa Rica = 13:00 UTC si el servidor está en UTC; verificar

con timedatectl ):

SICOP CONNECT · Guía de aprendizaje y ejecución C O N F I D E N C I A L

Hermatix M2M Communication S.R.L. · Documento confidencial — uso interno. Prohibida su distribución sin autorización. Página 54 de 69

CONFIDENCIAL\[Unit]

Description=Revision diaria SICOP CONNECT

\[Timer]

OnCalendar=\*-\*-\* 13:00:00

Persistent=true

Unit=sicop-cycle.service

\[Install]

WantedBy=timers.target

Un solo proceso web es lo correcto con SQLite en el piloto. Si en el futuro crece la concurrencia, se mide y se evalúa

PostgreSQL antes de escalar procesos.

17.5. Arranque, acceso y activación del ciclo

sudo systemd-analyze verify /etc/systemd/system/sicop-\*.service /etc/systemd/system/sicopcycle.timer

sudo systemctl daemon-reload

sudo systemctl start sicop-migrate.service \&\& sudo systemctl status sicop-migrate.service

sudo systemctl enable --now sicop-web.service

curl -f http://127.0.0.1:8000/health

sudo systemd-run --uid=sicop --pty --wait \\

&#x20;-p EnvironmentFile=/etc/sicop-connect/app.env \\

&#x20;-p WorkingDirectory=/opt/sicop-connect \\

&#x20;/opt/sicop-connect/.venv/bin/python -m app.cli create-user

La última orden ejecuta un comando CLI con exactamente la misma configuración que el servicio, sin imprimir

secretos ni interpretar el archivo con source . Se usa el mismo patrón para doctor , import o backup en el

servidor.

Un servicio oneshot aparece «inactive» al terminar bien: se revisa el código de salida y journalctl , no solo esa

palabra.

El administrador configura en el proxy existente el subdominio acordado, HTTPS y restricciones de acceso. Desde

otra computadora: iniciar sesión, listar, guardar una revisión; un visitante sin acceso no ve datos.

Activación del ciclo, en este orden: (1) sudo systemctl start sicop-cycle.service en dry-run y revisar registro

y vista previa; (2) el administrador configura correo real y habilita NOTIFICATIONS\_ENABLED=true ,

NOTIFICATIONS\_DRY\_RUN=false , SCHEDULER\_ENABLED=true ; (3) cambiar ExecStart a run-cycle --send ; (4)

daemon-reload y un ciclo supervisado; (5) verificar recepción; (6) habilitar el timer:

sudo systemctl enable --now sicop-cycle.timer

sudo systemctl list-timers sicop-cycle.timer

Si la obtención sigue siendo asistida, alguien de Hermatix continúa descargando de SICOP y subiendo el archivo

desde el panel o a la carpeta de entrada; el timer automatiza todo lo posterior.

17.6. Actualizar y revertir

Registrar commit y versión de esquema actuales.

backup a la ubicación de respaldo.

1\.

2\.

SICOP CONNECT · Guía de aprendizaje y ejecución C O N F I D E N C I A L

Hermatix M2M Communication S.R.L. · Documento confidencial — uso interno. Prohibida su distribución sin autorización. Página 55 de 69

CONFIDENCIALDetener el timer (y el panel si la migración lo exige).

Instalar la nueva versión en una carpeta nueva ( /opt/sicop-connect-NUEVA ), crear su entorno, apuntar el

servicio a ella.

Migrar, verificar /health y una oportunidad conocida.

Reiniciar el panel y reactivar el timer.

Si falla: desactivar el timer, volver a la carpeta anterior y, si la migración cambió el esquema de forma incompatible,

restaurar también la base desde el respaldo del paso 2. Volver solo al código no revierte una migración.

17.7. Registros y respaldos

sudo journalctl -u sicop-web.service -n 100 --no-pager

sudo journalctl -u sicop-cycle.service -n 100 --no-pager

Los registros muestran fecha, operación, identificador de ejecución y error útil; nunca contraseñas, códigos ni

enlaces privados. Respaldo diario (un timer adicional o el mismo ciclo) hacia un destino distinto del disco de

operación, con la retención que defina Hermatix (D8).

18\. Pruebas y criterios de aceptación técnica

Claude automatiza las pruebas de lógica que evitan errores reales; no se generan decenas de pruebas triviales. Los

datos sintéticos y los proveedores simulados sirven para lógica y se etiquetan como tales: no son evidencia de

conexión real.

Área Comprobación Dónde

Instalación Entorno limpio instala y arranca con requirements.lock.txt Local día 8 · servidor día 9

Datos Archivo real; filas inválidas; códigos de 24 dígitos; fechas; monedas Local días 2–3

Relaciones Varias líneas; código sin catálogo; comprador correcto Local día 3

Repetición Mismo archivo dos veces; actualización conserva revisión humana Local día 5

Reglas ≥ 80 % de acierto en golden set; falsos positivos conocidos Local día 4 · métricas día 13

Estado Plazo vencido, estado desconocido, cierre próximo Local días 5 y 14

Acceso Anónimo rechazado; CSRF; HTML escapado Local día 6 · servidor día 9

Correo Dry-run no envía; real llega; incierto no se reenvía a ciegas Días 7 y 10

Fuente Fallo o archivo incompleto ≠ «sin oportunidades» Día 8 · simulacro día 16

Operación Reinicio de servicio y servidor; timer; respaldo restaurado; reversión Servidor día 16

Simulacros obligatorios del día 16:

Reiniciar el servicio: el panel vuelve y una decisión guardada persiste.

Reiniciar el servidor en ventana acordada: el panel arranca solo y el timer sigue programado.

3\.

4\.

5\.

6\.

1\.

2\.

SICOP CONNECT · Guía de aprendizaje y ejecución C O N F I D E N C I A L

Hermatix M2M Communication S.R.L. · Documento confidencial — uso interno. Prohibida su distribución sin autorización. Página 56 de 69

CONFIDENCIALRestaurar un respaldo en otro directorio y leer una revisión conocida.

Ciclo con fuente fallida: se registra error o cobertura desactualizada, nunca «cero compras».

Repetir el ciclo: no se duplican avisos.

3\.

4\.

5\.

SICOP CONNECT · Guía de aprendizaje y ejecución C O N F I D E N C I A L

Hermatix M2M Communication S.R.L. · Documento confidencial — uso interno. Prohibida su distribución sin autorización. Página 57 de 69

CONFIDENCIALPARTE V · GESTIÓN DEL PROYECTO

19\. Alcance, roles y dependencias

19.1. Alcance obligatorio

CSV real → importación idempotente → relaciones → reglas explicables → panel protegido → revisión humana

→ correo probado → ciclo programado en servidor → respaldo y recuperación.

La obtención de archivos puede ser asistida (una persona descarga de SICOP y la app hace todo lo demás). Eso ya

entrega valor y se declara explícitamente.

19.2. Ampliaciones de valor (semana 3)

Oscar elige y prioriza el día 10. Cada una tiene un límite de tiempo y un criterio de aceptación (sección 13).

Código Ampliación Valor para Hermatix Claude estimado

A1 Prueba acotada de obtención

automática desde SICOP

Eliminar la descarga manual si el

portal lo permite

1 jornada máximo; puede concluir

«no viable» y eso es un resultado

válido

A2 Inteligencia competitiva: adjudicaciones

y contratos, quién gana qué

Ver dónde ganan Navsat, Skydata,

Stremax y otros; precios de

referencia

6–10 interacciones

A3 Calidad medible de reglas: precisión y

cobertura frente a las revisiones

humanas

Saber cuánto confiar en las alertas y

mejorar con datos

5–8 interacciones

A4 Alertas de cierre próximo y resumen

ejecutivo semanal

Que ninguna oportunidad revisada

venza sin decisión

5–8 interacciones

A5 Exportación a Excel del listado filtrado Compartir con ventas sin dar acceso

al panel

2–4 interacciones

A6 Importadores XLSX/JSON Solo si SICOP entrega esos formatos

de forma más confiable

3–5 interacciones

Fuera de alcance del mes (se evalúan en el plan de continuidad): análisis semántico de pliegos con IA vía API (tiene

costo aparte), múltiples usuarios con roles avanzados, integración con CRM, aplicaciones móviles.

19.3. Principios no negociables

Nada simulado se presenta como real. Datos sintéticos y proveedores simulados se etiquetan siempre.

La app sugiere; Hermatix decide. «Alta coincidencia» nunca significa «Hermatix puede o debe participar».

1\.

2\.

SICOP CONNECT · Guía de aprendizaje y ejecución C O N F I D E N C I A L

Hermatix M2M Communication S.R.L. · Documento confidencial — uso interno. Prohibida su distribución sin autorización. Página 58 de 69

CONFIDENCIALSin secretos en Git ni en Claude. Contraseñas, claves, códigos de validación y documentos personales no se

pegan en conversaciones ni se versionan.

Cada tarea termina con evidencia comprobable por otra persona, y con Ivania capaz de explicarla.

Credenciales y cambios de infraestructura quedan bajo control de Oscar o del administrador.

19.4. Matriz de responsabilidades (RACI)

R = realiza · A = aprueba · C = consultado · I = informado

Actividad Ivania Claude

Code Oscar

Administrador

servidor

Supervisor

académico

Especificar cada tarea y criterio de

aceptación

R C A — I

Generar y modificar código A R I — —

Verificar con datos reales y explicar el

cambio

R C A — I

Familias comerciales, ejemplos y

etiquetado

C — R/A — —

Acceso a SICOP y buzón empresarial R — A — —

Servidor, SSH, dominio, HTTPS, respaldo C C A R —

Proveedor de correo y destinatarios C — A R —

Despliegue en servidor R (ejecuta

guiada)

C A R (accesos) —

Revisión semanal y aceptación de hitos R — A C I

Validación de horas de práctica R — C — A

19.5. Dependencias que Hermatix debe entregar, con fecha límite

Este es el cuadro más importante para que el plan funcione. Claude acelera el código, pero cada fila de esta tabla

puede detener el proyecto. Las fechas se adelantaron respecto de la versión 2.1 porque el despliegue ahora ocurre

el día 9.

\# Insumo \[OSCAR] Para qué Fecha

límite Si llega tarde

D1 Supervisor diario y bloque de 15 min en calendario Reunión diaria Día 1,

08:00

Ivania trabaja con este plan y deja

preguntas por escrito

D2 Buzón empresarial para solicitar exportaciones de

SICOP

Obtener datos

reales

Día 1 Bloquea O1–O4: se usa una muestra

sintética etiquetada y el hito queda

«parcial»

3\.

4\.

5\.

SICOP CONNECT · Guía de aprendizaje y ejecución C O N F I D E N C I A L

Hermatix M2M Communication S.R.L. · Documento confidencial — uso interno. Prohibida su distribución sin autorización. Página 59 de 69

CONFIDENCIAL# Insumo \[OSCAR] Para qué Fecha

límite Si llega tarde

D3 Catálogo de soluciones Hermatix confirmado + 20–

40 ejemplos etiquetados («sí interesa», «no

interesa», «falso positivo»)

Reglas y su

medición

Día 3 Las reglas usan las familias semilla

de la sección 16.4; la medición O3

se pospone

D4 Datos del servidor: SO, versión de Python, usuario

SSH, ruta de datos, recursos

Preparar

despliegue

Día 5 Despliegue se mueve al día 10–11;

la semana 3 se acorta

D5 Proveedor de correo (SMTP o API) con credenciales

creadas por el administrador, remitente y

destinatario

Avisos reales Día 6 Se mantiene dry-run; O5 queda

parcial

D6 Dirección de acceso (subdominio interno o público

con HTTPS) y método de acceso (VPN o

autenticación)

Publicar el panel Día 8 Acceso temporal por túnel SSH

supervisado

D7 Bloques de sesión práctica con Oscar: días 2 (1 h), 3

(1 h), 9 (3 h), 10 (2 h), 16 (2 h), 20 (1 h)

Transferencia y

despliegue

Reservar el

día 1

Se reprograma el hito afectado

D8 Política de respaldo (destino, retención) Recuperación Día 8 Respaldo local en el servidor,

marcado como provisional

Servidor candidato: el VPS de Hermatix que confirme el administrador (por ejemplo, el que ya aloja

nexus.hermatix.com ). La app escuchará solo en 127.0.0.1 detrás del proxy existente; no requiere un puerto

público propio. Como referencia de planificación, el piloto sin IA local cabe holgadamente en 1–2 vCPU y 1–2 GB de

RAM libres; se mide con el volumen real.

20\. Seguimiento: estado, bitácora y retos de comprensión

20.1. docs/ESTADO\_PROYECTO.md (lo actualiza Claude al cerrar cada encargo; Ivania lo revisa)

\# Estado de SICOP CONNECT

Última actualización: Día / tarea: Commit probado:

\## Último resultado

\- Qué funciona (verificado):

\- Comandos ejecutados y resultado:

\- Evidencia: real / sintética / proveedor simulado

\- Concepto que puedo explicar:

\## Estado de integraciones

\- Obtención: sin verificar / asistida / automática comprobada

\- Correo: sin configurar / dry-run / prueba real confirmada

\- Servidor: local / instalado / producción con timer

\## Pendientes

\- Bloqueo · responsable · próximo paso:

\## Siguiente encargo

\- Objetivo: Archivos: Criterio de aceptación:

SICOP CONNECT · Guía de aprendizaje y ejecución C O N F I D E N C I A L

Hermatix M2M Communication S.R.L. · Documento confidencial — uso interno. Prohibida su distribución sin autorización. Página 60 de 69

CONFIDENCIAL20.2. docs/BITACORA.md (la escribe Ivania, una entrada por jornada)

\## Día N — fecha

Horas realizadas:

Objetivo acordado en la reunión:

Trabajo y archivos cambiados:

Evidencia y comando de comprobación:

Datos: reales / sintéticos / simulados

Claude: interacciones usadas · % ventana A · % ventana B · % semanal

Estimado vs. real (horas humanas por tarea):

Concepto aprendido, con mis palabras:

Error encontrado y cómo se resolvió:

Bloqueo, responsable y próximo paso:

Commit:

Demo para mañana:

20.3. Retos de comprensión (en la revisión semanal, sin abrir Claude)

Ivania usa el código y sus notas. Si necesita ayuda, se registra qué concepto reforzar; una dificultad explicada y

resuelta cuenta como aprendizaje. Ocultar un fallo o presentar una simulación como conexión real impide aceptar

el hito.

Semana Reto Evidencia

1 Seguir una fila del CSV real hasta la base; explicar por qué otra fue rechazada Archivo, registro, diagnóstico

2 Mostrar por qué un segundo ciclo no reenvía el mismo aviso; localizar el registro de

outbox

Outbox y repetición

comprobada

3 Proponer un cambio de regla, predecir su efecto en las métricas y verificarlo Predicción, resultado,

explicación

4 Explicar a Oscar cómo reiniciar el servicio y recuperar un respaldo, distinguiendo Mac

y servidor

Demostración supervisada

21\. Entregables, presentación e informe final

21.1. Entregables a Hermatix

\# Entregable Evidencia de aceptación

E1 Repositorio privado con código, dependencias bloqueadas y pruebas, sin secretos ni

documentos personales

Instalación limpia exitosa siguiendo

el README

E2 Aplicación operando en el servidor con panel protegido, correo y ciclo programado URL real, registros de ciclos,

correos recibidos

E3 Reglas comerciales revisadas con Oscar + golden set + métricas de calidad REGLAS.md y salida de scorerules

E4 Ampliaciones aceptadas de la semana 3 Demostración en producción

SICOP CONNECT · Guía de aprendizaje y ejecución C O N F I D E N C I A L

Hermatix M2M Communication S.R.L. · Documento confidencial — uso interno. Prohibida su distribución sin autorización. Página 61 de 69

CONFIDENCIAL# Entregable Evidencia de aceptación

E5 ACCESO\_SICOP.md , MAPEO\_DATOS.md y DECISION\_OBTENCION.md Evidencia observada, no supuesta

E6 OPERACION.md (importar, revisar, enviar, diagnosticar, recuperar) y

DESPLIEGUE.md (instalar, actualizar, revertir)

Probados literalmente en el día 18

E7 Acta de despliegue y resultados de simulacros Commit, hash y resultados del día

16

E8 Métricas del mes, incluido el rendimiento real de Claude Pro Sección 14 completa

E9 Informe final, bitácora y registro de horas Para validación académica

E10 Plan de continuidad de las 160 h restantes Aceptado por Oscar el día 20

Condición de independencia: nada de lo entregado requiere la cuenta de Claude de Ivania para operar, mantenerse

o continuar.

21.2. Presentación final (20 minutos + preguntas)

No se memoriza un texto escrito por Claude: se usa el sistema real, un cartel real y las palabras de Ivania.

Minutos Parte Pregunta que debe quedar respondida

0–2 Problema y valor ¿Qué trabajo le ahorra esto a Hermatix?

2–4 Fuente ¿Qué es automático y qué necesita una persona?

¿Por qué?

4–9 Recorrido en vivo de un cartel real: origen → importación →

líneas → regla y evidencia → panel → revisión → correo

¿Cómo se evitan códigos perdidos y duplicados?

9–12 Calidad de las reglas ¿Cuánto se puede confiar en una alerta? ¿Por qué

hay falsos positivos?

12–14 Ampliaciones ¿Qué valor agregó la semana 3?

14–16 Operación ¿Qué sigue funcionando con tu computadora

apagada? ¿Qué hace Hermatix si se pierde la base?

16–18 Métricas del mes y uso de Claude ¿Cuánto tiempo tomó realmente con IA y dónde

estuvo el cuello de botella?

18–20 Límites y siguientes pasos ¿Qué recomiendas para las próximas 160 horas?

21.3. Estructura del informe final

Resumen ejecutivo (1 página).

Objetivos O1–O8: cumplido / parcial / bloqueado, con evidencia.

Arquitectura y decisiones técnicas (con alternativas descartadas y por qué).

Fuente SICOP: lo comprobado y lo pendiente.

Calidad de reglas: métricas y evolución.

Operación: despliegue, simulacros, recuperación.

1\.

2\.

3\.

4\.

5\.

6\.

SICOP CONNECT · Guía de aprendizaje y ejecución C O N F I D E N C I A L

Hermatix M2M Communication S.R.L. · Documento confidencial — uso interno. Prohibida su distribución sin autorización. Página 62 de 69

CONFIDENCIALUso de Claude: plan vs. real, lecciones para futuros proyectos.

Aprendizaje por semana, con los retos de comprensión.

Pendientes y plan de continuidad.

22\. Métricas del proyecto

Se calculan el día 19 y se presentan el día 20. Convierten el piloto en una decisión informada para Hermatix.

Categoría Métrica Fuente

Valor

comercial

Carteles procesados · oportunidades Alta/Media detectadas · revisadas ·

marcadas «Interesa»

Base de datos

Oportunidades que el proceso manual anterior no habría visto (necesidad solo

en las líneas)

Evaluaciones con evidencia en

líneas

Tiempo estimado de revisión manual ahorrado por semana Estimación con Oscar

Calidad Precisión y cobertura por familia (inicio vs. final) score-rules

Operación Ciclos ejecutados · fallidos · correos enviados · duplicados (meta: 0) source\_runs , outbox

Uso de Claude Interacciones totales · % promedio de ventana · veces que se agotó · horas

humanas por funcionalidad

Bitácora

Comparación con la estimación del anexo A Bitácora

Aprendizaje Retos de comprensión superados sin ayuda Revisiones semanales

La métrica de uso de Claude es especialmente valiosa para Hermatix: es la primera medición propia de cuánto rinde

una cuenta Pro en un proyecto real y sirve para presupuestar futuros proyectos con IA (por ejemplo, decidir cuándo

conviene una cuenta de mayor capacidad).

23\. Riesgos, contingencias y continuidad

23.1. Matriz de riesgos

Riesgo Prob. Impacto Mitigación Plan B

No llega el archivo real de

SICOP a tiempo (D2)

Media Alto Prueba del portal el día 1 con

Oscar

Fixtures sintéticos marcados; hito

«parcial»; se recupera en cuanto llegue el

archivo

Excel o la exportación

truncan identificadores

Media Alto Nunca abrir y guardar en Excel;

validar longitudes al importar

Pedir otro formato a SICOP; registrar el

defecto

Servidor o accesos no listos

el día 9 (D4, D6)

Media Alto Datos del servidor pedidos el día

1, confirmados el día 6

Desplegar el día 10–11 y acortar la semana

3; acceso temporal por túnel SSH

7\.

8\.

9\.

SICOP CONNECT · Guía de aprendizaje y ejecución C O N F I D E N C I A L

Hermatix M2M Communication S.R.L. · Documento confidencial — uso interno. Prohibida su distribución sin autorización. Página 63 de 69

CONFIDENCIALRiesgo Prob. Impacto Mitigación Plan B

Correo no configurado (D5) Media Medio Pedido el día 1 Mantener dry-run; el resumen se revisa en

el panel

Se agota la capacidad

semanal de Claude

Media Medio Presupuesto de la sección 5.3;

técnicas de la 7.4

Adelantar tareas humanas (7.6); no activar

pagos sin autorización de Oscar

Las reglas dan demasiados

falsos positivos

Media Medio Golden set y exclusiones desde el

día 4

Subir umbral de alerta a solo «Alta»

mientras se ajusta

SICOP cambia formato o

encabezados

Baja Medio Mapeo explícito; validación de

encabezados al importar

Error claro y actualización del mapeo

La automatización de

obtención no es viable

Alta Bajo Límite de un día para A1 Modo asistido, ya operativo desde la

semana 2

Código generado que Ivania

no entiende

Media Alto Regla de comprensión (7.8) y

retos semanales

Repasar con Claude en modo explicación

antes de seguir

Disponibilidad de Oscar en

sesiones clave

Media Alto Bloques reservados el día 1 (D7) Designar suplente con acceso al servidor

23.2. Plan de continuidad (las 160 horas restantes de la práctica)

Se acuerda el día 20 con los datos reales del mes. Candidatos, por orden de valor esperado:

Consolidación: corregir lo observado en el uso real; ampliar cobertura de formatos o reportes que la operación

demuestre necesarios.

Obtención automática si DECISION\_OBTENCION.md dejó una ruta viable y permitida.

Análisis de pliegos con IA (opcional): resumir requisitos de los candidatos Alta. Requiere decisión de

presupuesto de API separado de la suscripción Pro (o modelo local si el hardware lo permite), límites de gasto

por día y mes, caché por hash, y que la IA nunca gestione credenciales, envíe correos ni decida participar. Las

reglas siguen operando si la IA falla.

Integración comercial: exportar oportunidades aprobadas al flujo de ventas de Hermatix.

Ampliación regional: evaluar fuentes de compras públicas de otros países donde opera Hermatix, reutilizando

el motor de reglas.

Cada candidato se estima con el método del anexo A, ya calibrado con la bitácora del mes.

24\. Solución de problemas, aprendizaje y fuentes

24.1. Problemas frecuentes

Situación Qué revisar primero

python o claude no se reconoce Instalación, terminal nueva y PATH; no es un error del código

Falta una biblioteca Entorno virtual activo e instalación en ese entorno

1\.

2\.

3\.

4\.

5\.

SICOP CONNECT · Guía de aprendizaje y ejecución C O N F I D E N C I A L

Hermatix M2M Communication S.R.L. · Documento confidencial — uso interno. Prohibida su distribución sin autorización. Página 64 de 69

CONFIDENCIALSituación Qué revisar primero

Claude alcanzó el límite /usage ; pasar a la lista 7.6; esperar la renovación

Claude parece cobrar por API /status ; existencia de ANTHROPIC\_API\_KEY (sin mostrar su valor)

Claude responde lento o «olvida»

decisiones

Demasiado contexto: actualizar ESTADO\_PROYECTO.md , /clear , reiniciar el

encargo

No hay candidatos Importaciones, periodo cubierto, catálogo y reglas; comprobar la fuente antes de

concluir

Código de compra deformado Archivo original y tipo de columna; pedir exportación sin pérdida

Aviso repetido Clave de deduplicación, versión y outbox anterior

Correo no llega Proveedor, destinatario, estado registrado y carpeta de no deseado; no reintentar a

ciegas

El panel solo funciona con la terminal

abierta

Está en modo desarrollo; revisar el servicio del servidor

Datos desaparecen al actualizar Ruta de la base y datos persistentes; detener el ciclo y restaurar

SICOP pide un código en cada solicitud Mantener modo asistido hasta validar otra ruta (A1)

24.2. Material de estudio por semana (sin consumir Claude)

Semana Tema Recurso

1 Entornos virtuales · FastAPI básico · SQL relacional venv · Tutorial FastAPI

2 Sesiones y CSRF · conceptos de despliegue · systemd Conceptos de despliegue FastAPI

3 Precisión y cobertura · análisis de datos Documentación de score-rules en REGLAS.md

4 Respaldos y recuperación · comunicación técnica OPERACION.md propio

24.3. Fuentes consultadas

Consultadas el 4 de octubre de 2026. Productos, límites y pantallas cambian; se revisan al implementar.

Claude: plan Pro, Claude Code incluido y API aparte

Claude Code con plan Pro o Max: autenticación y facturación

Claude: cómo funcionan los límites de uso

Claude Code: instalación y primer inicio

Claude Code: buenas prácticas de contexto y tareas

Reportes independientes de uso de Claude Code en Pro (rangos de interacciones por ventana de 5 horas); se

usan solo como referencia de planificación, la fuente de verdad es /usage .

ICD: procedimiento de descarga mediante SICOP — su filtro institucional es un ejemplo del ICD, no el alcance

de Hermatix.

SICOP: módulo de datos abiertos — no se verificó una API pública directa.

Python: entornos virtuales · FastAPI: despliegue

•

•

•

•

•

•

•

•

•

SICOP CONNECT · Guía de aprendizaje y ejecución C O N F I D E N C I A L

Hermatix M2M Communication S.R.L. · Documento confidencial — uso interno. Prohibida su distribución sin autorización. Página 65 de 69

CONFIDENCIALDocumentos aportados: diccionario de datos y diagrama ERD de SICOP (describen datos, no una API de acceso), y el

PDF de práctica y perfil de Ivania, del cual solo se usan la solicitud de 320 horas y su formación profesional

(Desarrollo Web; bases en Python, JavaScript, HTML/CSS; certificaciones introductorias de datos; experiencia en

soporte y documentación). No se trasladan datos de identidad.

Las estimaciones de tiempo de Claude de este documento son un modelo de planificación basado en experiencia

con proyectos de este tamaño y en los límites públicos de Pro; se validan y corrigen con la bitácora real.

SICOP CONNECT · Guía de aprendizaje y ejecución C O N F I D E N C I A L

Hermatix M2M Communication S.R.L. · Documento confidencial — uso interno. Prohibida su distribución sin autorización. Página 66 de 69

CONFIDENCIALANEXOS

Anexo A. Modelo de estimación del tiempo de Claude

A.1. Estimación por componente: tradicional vs. real con Claude

Estas cifras son la base del cronograma. Son estimaciones de planificación, no garantías, y se recalibran con los

datos reales de la bitácora al cierre de cada semana.

Componente

Junior sin IA

(referencia)

Interacciones

Claude

&#x20;Claude

activo

&#x20;Ivania (especificar,

probar, entender)

Jornadas en

este plan

Esqueleto FastAPI, configuración,

/health , doctor , pruebas

base

3–5 días 4–6 15–25 min 2–3 h 0,5

Migraciones y modelo de datos (7

tablas)

3–4 días 3–5 15–20 min 2 h 0,5

Importador CSV de carteles

idempotente con rechazos

4–6 días 5–8 25–40 min 3–4 h 1

Importadores de líneas, catálogo e

instituciones + relaciones

4–5 días 5–8 25–40 min 3–4 h 1

Motor de reglas YAML +

evaluate + conjunto de prueba

5–7 días 6–10 30–45 min 4–5 h 1

Panel: lista, filtros, detalle, revisión

persistente

6–8 días 8–12 40–60 min 4–5 h 1

Autenticación, sesiones, CSRF,

escape HTML

3–5 días 4–6 20–30 min 2–3 h 0,5

Correo: dry-run, outbox

deduplicada, proveedor

4–6 días 6–9 30–45 min 3–4 h 1

run-cycle , bloqueo, cobertura,

respaldo

3–5 días 5–8 25–40 min 3 h 1

Plantillas systemd, manual de

despliegue, ensayo

3–4 días 3–5 15–20 min 2 h + sesión con Oscar 1

Subtotal piloto obligatorio ≈ 38–55 días (8–

11 semanas)

≈ 50–80 ≈ 4–6 h ≈ 30–37 h ≈ 8,5

Lectura para Oscar: el piloto completo que antes se estimaba en un mes cabe en unas 4–6 horas de trabajo activo

de Claude, repartidas en 10–14 ventanas. Lo que convierte esas horas en 8–9 jornadas es el trabajo humano de

especificar, verificar con datos reales y aprender, que no se debe recortar: es lo que vuelve el resultado confiable y

es el objetivo formativo de la práctica.

SICOP CONNECT · Guía de aprendizaje y ejecución C O N F I D E N C I A L

Hermatix M2M Communication S.R.L. · Documento confidencial — uso interno. Prohibida su distribución sin autorización. Página 67 de 69

CONFIDENCIALEsto libera aproximadamente 10 jornadas y ≈ 60 % de la capacidad de Claude del mes para ampliaciones de valor

(semana 3) y operación real (semana 4).

A.2. Cómo se mide si la estimación fue correcta

Cada jornada, la bitácora registra: interacciones usadas, % de ventana consumido ( /usage ), tiempo de Claude

activo aproximado y horas humanas por tarea. El viernes, la revisión semanal compara plan vs. real y ajusta la

semana siguiente. Así, al final del mes Hermatix tendrá datos propios de cuánto rinde una cuenta Pro en un

proyecto real, útiles para planificar proyectos futuros con IA.

Anexo B. Competencias que habrás desarrollado

Usa esta lista al final de cada semana. Marca una competencia solo si puedes demostrarla sin ayuda.

Competencia Semana Cómo se demuestra

Preparar un entorno de desarrollo reproducible (Python, Git, entorno

virtual)

1 Otra persona instala el proyecto con tu

README

Analizar un archivo de datos real antes de programar 1 MAPEO\_DATOS.md completo y correcto

Diseñar importaciones confiables e idempotentes 1 Carga repetida sin duplicados, explicada

Modelar datos relacionales y unir tablas por claves 1 Un cartel con sus líneas y comprador

Traducir una necesidad comercial en reglas explicables 1 Reglas con evidencia y ≥ 80 % de acierto

Construir una interfaz web con datos persistentes 1 Panel con revisión que sobrevive a reimportar

Aplicar seguridad básica en aplicaciones web 2 Autenticación, sesión y CSRF explicados

Integrar un servicio externo de forma segura (correo) 2 Outbox, dry-run y estados de envío

Diseñar procesos automáticos robustos ante fallos 2 run-cycle con bloqueo y cobertura

Desplegar y operar en un servidor Linux 2 Despliegue documentado y ciclo programado

Evaluar opciones técnicas y documentar decisiones 3 DECISION\_OBTENCION.md

Medir la calidad de un sistema con métricas 3 Precisión y cobertura explicadas con datos

reales

Actualizar producción de forma controlada 3 Actualización con respaldo y verificación

Recuperar un sistema ante fallos 4 Simulacros superados

Escribir documentación operativa verificada 4 Manuales seguidos literalmente por otra

persona

Trabajar con IA de forma profesional y medible 1–4 Bitácora con encargos, capacidad y plan vs.

real

Comunicar resultados técnicos a la gerencia 4 Presentación final

SICOP CONNECT · Guía de aprendizaje y ejecución C O N F I D E N C I A L

Hermatix M2M Communication S.R.L. · Documento confidencial — uso interno. Prohibida su distribución sin autorización. Página 68 de 69

CONFIDENCIALPrimera acción: lunes 5 de octubre, 08:00

Lee las Partes I y II de esta guía (si no lo hiciste el fin de semana).

Reunión de arranque con Oscar: repasar las dependencias de la sección 19.5 y fijar responsable y fecha de cada

una.

Abre la Lección 1 y sigue el paso a paso.

El proyecto avanza cuando cada tarea produce un resultado que tú puedes explicar y otra persona puede

comprobar. Claude escribe el código en minutos; tu trabajo es entender el problema, decidir qué construir,

comprobar que es correcto y dejarlo listo para que Hermatix lo use durante años.

1\.

2\.

3\.

SICOP CONNECT · Guía de aprendizaje y ejecución C O N F I D E N C I A L

Hermatix M2M Communication S.R.L. · Documento confidencial — uso interno. Prohibida su distribución sin autorización. Página 69 de 69

