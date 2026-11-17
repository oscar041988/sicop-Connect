# Evaluación del asistente de elegibilidad con Oscar · 5 carteles (2026-11-17)

Lista preparada por Claude a pedido de Ivania para la reunión con Oscar. Datos **REALES**, de la base local el
17/11 (consulta de solo lectura). Los 5 ya cerraron: la evaluación sirve para ajustar el asistente, no para ofertar.

Objetivo (pendiente de `ESTADO_PROYECTO.md`): en cada cartel, comparar lo que dice el asistente (Cumple / No cumple
/ Falta / Revisar) con el criterio de Oscar y anotar cada diferencia. Las reglas se ajustan con lo que él diga.

Regla de Ivania: todo requisito se presenta; nadie filtra, el usuario decide.

---

## Los 5 carteles

| # | Cartel | Familia | Requisitos | Resultado del asistente | Qué mirar |
|---|---|---|---|---|---|
| 1 | [`20261003280`](http://127.0.0.1:8000/oportunidades/20261003280) · Localización, monitoreo y alquiler de equipos GPS | GPS (Media) | 116 | No cumple excluyente | Producto principal y la lista más larga. ¿El excluyente que falla es real? |
| 2 | [`20261100233`](http://127.0.0.1:8000/oportunidades/20261100233) · Cámaras corporales, radios y tintas | Bodycams (Alta) | 31 | No cumple excluyente | Revisado «Interesa». ¿Oscar coincide en que no se podía? |
| 3 | [`20261001587`](http://127.0.0.1:8000/oportunidades/20261001587) · Alquiler de cámaras corporales y almacenamiento | Bodycams (Alta) | 13 | Falta información | ¿Lo que «falta» de verdad falta o Hermatix ya lo tiene? |
| 4 | [`20261002824`](http://127.0.0.1:8000/oportunidades/20261002824) · Compra de cámaras y accesorios | Ninguna (falso positivo) | 30 | Puede si completa | Único con este resultado. El cartel no era de Hermatix: ¿el asistente igual lo da posible? |
| 5 | [`20261101092`](http://127.0.0.1:8000/oportunidades/20261101092) · Cámaras portátiles para la Policía Municipal (Escazú) | Bodycams (Media) | 35 | Sin resultado todavía | Resumen v10 de hoy; el asistente está empezado: terminarlo con Oscar es la prueba en vivo. Usa IA (~0,10 USD). |

**Reemplazos**, si Oscar prefiere otro: `20261002863` (cámaras corporales, «Falta información») y `20261003868`
(64 sensores LoRaWAN; todavía sin asistente).

## Preguntas para Oscar

1. «Lo tiene · archivo pendiente»: ¿cuenta como cumplido o como falta?
2. Los «Revisar» excluyentes: ¿están bien marcados o sobran?
3. En el n.º 4: si el cartel no es de Hermatix, ¿el asistente debería avisarlo?

---

## Diferencias (una fila por requisito donde Oscar opine distinto)

Ejemplo:

| Requisito | Dice el asistente | Dice Oscar | Por qué |
|---|---|---|---|
| Experiencia 5 años | No cumple | Cumple | Tenemos 6 años con municipalidades |

### 1. `20261003280` · GPS

| Requisito | Dice el asistente | Dice Oscar | Por qué |
|---|---|---|---|
| | | | |

### 2. `20261100233` · Cámaras corporales, radios y tintas

| Requisito | Dice el asistente | Dice Oscar | Por qué |
|---|---|---|---|
| | | | |

### 3. `20261001587` · Alquiler de cámaras corporales

| Requisito | Dice el asistente | Dice Oscar | Por qué |
|---|---|---|---|
| | | | |

### 4. `20261002824` · Cámaras y accesorios

| Requisito | Dice el asistente | Dice Oscar | Por qué |
|---|---|---|---|
| | | | |

### 5. `20261101092` · Cámaras portátiles, Escazú

| Requisito | Dice el asistente | Dice Oscar | Por qué |
|---|---|---|---|
| | | | |
