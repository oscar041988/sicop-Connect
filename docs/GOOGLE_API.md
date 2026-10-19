# Acceso a la API de Gmail para los avisos — pasos

Para la lección 7, encargo B: que SICOP CONNECT envíe el resumen diario desde licitaciones@hermatix.com.
Opción elegida: **A · OAuth con la cuenta licitaciones@**, con permiso solo para enviar (`gmail.send`).
Ver la comparación en `docs/DESPLIEGUE.md`, sección 5.

> Google cambia los nombres de los menús con el tiempo. Si un botón no se llama igual, busca el más
> parecido y anota aquí el nombre real. Entre paréntesis va el nombre anterior.

## Antes de empezar (5 min)

- [ ] **licitaciones@hermatix.com es un usuario de verdad**, con licencia de Gmail: en
      admin.google.com → *Directorio → Usuarios* aparece como usuario. Si es un **grupo** o un **alias** de
      otra persona, detente y avísame: el plan cambia.
- [ ] Tener a mano la contraseña de licitaciones@ (y su segundo factor, si tiene). Se usa en el paso 7.
- [ ] Crear una carpeta **fuera del proyecto** para los secretos, por ejemplo
      `C:\Users\User\secretos-sicop\`. Nunca dentro de `sicop-connect` (git podría subirlos).

## 1. Entrar a Google Cloud

1. Abre https://console.cloud.google.com con la **cuenta de administrador** de hermatix.com.
2. Si es la primera vez, acepta los términos del servicio. No hace falta activar facturación: la Gmail API
   no cobra por enviar.

## 2. Crear el proyecto

1. Arriba a la izquierda, junto al logo, abre el **selector de proyectos** → **Proyecto nuevo**.
2. Nombre: `SICOP Connect`. **Organización:** `hermatix.com` (importante para el paso 4). Ubicación: la misma.
3. **Crear**. Espera la notificación y **selecciona** el proyecto (su nombre debe verse arriba).

## 3. Activar la Gmail API

1. Menú ☰ → **APIs y servicios → Biblioteca**.
2. Busca `Gmail API` → ábrela → **Habilitar**.

## 4. Configurar la pantalla de consentimiento

Menú ☰ → **APIs y servicios → Pantalla de consentimiento de OAuth** (puede abrir «Google Auth Platform»)
→ **Comenzar**.

1. **Información de la app:** nombre `SICOP Connect`; correo de asistencia: el de la cuenta con la que entraste
   (la lista solo ofrece esa cuenta y los grupos que administra; en Hermatix, el de Oscar). Ese correo solo se
   muestra como contacto en la pantalla de permiso: **no** decide desde qué cuenta salen los avisos.
2. **Público:** **Interno**. Así solo la usan cuentas de hermatix.com y Google no pide revisar la app.
   Si «Interno» no aparece, el proyecto no quedó dentro de la organización (paso 2.2): detente y avísame.
3. **Información de contacto:** tu correo o el de Oscar. Acepta la política de datos → **Crear**.
4. **Acceso a datos** (Data Access; antes «Permisos»): **Agregar o quitar permisos** → busca
   `gmail.send` → marca **`.../auth/gmail.send`** («Enviar correo en tu nombre») → **Actualizar → Guardar**.
   **Solo ese permiso.** No marques los de leer o administrar el correo.

## 5. Crear el cliente OAuth

1. **Clientes** (antes *APIs y servicios → Credenciales → Crear credenciales → ID de cliente OAuth*)
   → **Crear cliente**.
2. Tipo de aplicación: **App de escritorio**. Nombre: `SICOP Connect - avisos` → **Crear**.
3. En la ventana que aparece, **Descargar JSON** *en ese momento*: Google puede no volver a mostrar el secreto.
4. Guarda el archivo como `C:\Users\User\secretos-sicop\google_cliente.json`.

**No** lo pegues en el chat, no lo mandes por correo ni lo pongas en la carpeta del proyecto.
Para el servidor (lección 9) se copiará con `scp` directo a su carpeta protegida.

## 6. Revisar los controles de API de Workspace (solo si hace falta)

Las apps **internas** normalmente funcionan sin más. Si en el paso 7 sale «acceso bloqueado» o
«esta app está bloqueada»:

1. admin.google.com → **Seguridad → Acceso y control de datos → Controles de API**.
2. **Administrar acceso de apps de terceros** → busca `SICOP Connect` (o su ID de cliente, que viene en el JSON)
   → marca **Confiable**.

## 7. Autorización única: `python -m app.cli google-auth`

1. En `.env` (no en `.env.example`):
   ```
   MAIL_PROVIDER=gmail_api
   MAIL_FROM=licitaciones@hermatix.com
   GOOGLE_CLIENT_FILE=C:\Users\User\secretos-sicop\google_cliente.json
   GOOGLE_TOKEN_FILE=C:\Users\User\secretos-sicop\google_token.json
   ```
   Deja `NOTIFICATIONS_ENABLED=false` y `NOTIFICATIONS_DRY_RUN=true`: esto todavía no activa ningún envío.
2. `python -m app.cli doctor` → debe decir «Gmail: archivo del cliente existe · token NO EXISTE».
3. `python -m app.cli google-auth` → se abre el navegador. Entra **como licitaciones@hermatix.com** (no como
   el administrador) y acepta. Google pide «Enviar correo en tu nombre» y ver tu correo: lo segundo solo sirve
   para que la app compruebe que autorizó la cuenta correcta. Si entras con otra cuenta, la app se niega y no
   guarda nada.
4. La terminal dice «Autorizado: licitaciones@hermatix.com…». `doctor` ya muestra «token existe».

El token vale hasta que se cambie la contraseña de licitaciones@, se retire el acceso o pasen ~6 meses sin uso:
entonces `notify --send` lo dice y basta repetir este paso.

## Después: quién hace qué (para no depender de una sola persona)

- **Renovar el permiso no requiere a Oscar.** El token es de licitaciones@: si deja de servir, se repite el
  paso 7 entrando como licitaciones@. Pasa si se cambia la contraseña de licitaciones@, si alguien quita el
  acceso de la app en su cuenta o si la app pasa unos 6 meses sin usarse. Con la app «Interna», el token no vence
  a los 7 días (eso solo les pasa a las apps externas en modo de prueba).
- **Oscar (administrador) solo hace falta para cambiar la configuración:** permisos, cliente o controles de API.
- **Segundo dueño del proyecto:** en Google Cloud → *IAM y administración → IAM → Otorgar acceso*, agregar a
  Ivania (o Anabelle) con el rol **Propietario**. Así, si Oscar no está, otra persona puede entrar al proyecto.
- El proyecto es de la **organización** hermatix.com, no de la cuenta de Oscar, y sigue existiendo aunque esa
  cuenta cambie. Si cambia el correo de asistencia, se edita en *Información de la marca* (Branding).

## Qué me cuentas al terminar

- Qué pasos quedaron hechos y cualquier mensaje de error **copiado tal cual**.
- La **ruta** del JSON (solo la ruta, nunca el contenido).
- Si licitaciones@ es usuario, grupo o alias.
- Los nombres reales de los menús, si cambiaron, para corregir esta guía.
