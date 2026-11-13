# Formulario y CRM en Google: guía paso a paso

Con esta guía vais a tener, en unos 15 minutos y sin programar:

- **Un formulario de Google** para que los posibles clientes pidan una propuesta, con su enlace y su **código QR**.
- **Una hoja de Google Sheets que hace de CRM.** Cada solicitud llega ordenada, con una **puntuación de 0 a 100**, su **prioridad** (Alta, Media o Baja, con colores), su estado y la fecha del primer seguimiento.
- **Un panel** con indicadores y gráficos: contactos, presupuesto en juego, tasa de cierre y de dónde vienen los clientes.
- **Emails automáticos:** el cliente recibe un mensaje de bienvenida y la agencia recibe un aviso con su resumen.
- **La conexión con vuestra app de VS Code**, que lee el CRM en la sección *Clientes (CRM)*.

Todo se crea solo con el código del archivo `google/Codigo.gs`.

> Necesitáis una cuenta de Google (Gmail). Los emails automáticos saldrán desde esa cuenta.

---

## Paso 1. Crear una hoja de cálculo vacía

1. Entrad en https://sheets.new (crea una hoja nueva directamente).
2. Arriba a la izquierda, cambiad *"Hoja de cálculo sin título"* por **CRM Agencia**.

## Paso 2. Pegar el código

1. En la hoja, menú **Extensiones → Apps Script**. Se abre una pestaña nueva con un editor.
2. Arriba a la izquierda, cambiad *"Proyecto sin título"* por **CRM Agencia**.
3. En VS Code, abrid `google/Codigo.gs`, seleccionad todo (`Ctrl + A` / `Cmd + A`) y copiad (`Ctrl + C` / `Cmd + C`).
4. En el editor de Apps Script, borrad lo que hay en `Código.gs` y pegad (`Ctrl + V` / `Cmd + V`).
5. Guardad con el icono del disquete o con `Ctrl + S` / `Cmd + S`.

> **Opcional:** si queréis que vuestra agencia tenga otro nombre, cambiad `'Agencia del Futuro'` al principio del código (línea `NOMBRE_AGENCIA_INICIAL`) **antes** de seguir.

## Paso 3. Ejecutarlo una vez

1. Arriba, en el desplegable que hay junto a **Ejecutar**, elegid **configurarTodo**.
2. Pulsad **Ejecutar**.
3. Google pedirá permisos. Es normal, porque el código es vuestro y Google no lo conoce:
   - Pulsad **Revisar permisos** y elegid vuestra cuenta.
   - Si aparece *"Google no ha verificado esta aplicación"*, pulsad **Configuración avanzada** y después **Ir a CRM Agencia (no seguro)**.
   - Pulsad **Permitir**. El código pide crear formularios, editar esta hoja y enviar emails en vuestro nombre.
4. Esperad unos 30 segundos y volved a la pestaña de la hoja: aparecerá un mensaje **"¡Listo!"** con el enlace del formulario.

Recargad la página de la hoja (`F5`). Arriba aparecerá un menú nuevo llamado **Agencia**.

## Paso 4. Qué se ha creado

| Pestaña | Para qué sirve |
|---|---|
| **Panel** | Indicadores, gráficos, enlace del formulario y código QR |
| **CRM** | Un posible cliente por fila. El **Estado** se cambia con el desplegable: Nuevo → Contactado → Reunión → Propuesta enviada → Ganado o Perdido |
| **Ajustes** | Nombre de la agencia, email que recibe los avisos y si se envía o no el email al cliente |
| **Respuestas (no tocar)** | Las respuestas en bruto que guarda Google. No la editéis |

**Cómo se calcula la prioridad (0 a 100 puntos):**
- Presupuesto: de 5 puntos (menos de 500 €) a 40 puntos (más de 6.000 €).
- Urgencia: 30 puntos si quieren empezar este mes, 20 si es en 1-3 meses y 5 si solo se están informando.
- Servicios: 5 puntos por cada servicio que piden, hasta 15.
- 5 puntos extra por dejar teléfono, 5 por escribir un mensaje y 5 si vienen recomendados.
- **Alta** a partir de 65 puntos (seguimiento al día siguiente), **Media** a partir de 40 (a los 3 días) y **Baja** por debajo (a los 7 días).

**Objetivos para el informe:** con el precio medio que indica el cliente, el CRM calcula un **CPA objetivo** (un tercio del precio) y un **ROAS objetivo de 3**. La app los usa al preparar el informe de campaña.

## Paso 5. Probarlo

1. Menú **Agencia → Cargar clientes de prueba**. Se añaden 8 clientes ficticios (su ID empieza por DEMO) para que el panel tenga datos.
2. Menú **Agencia → Ver enlace del formulario y QR**. Abrid el enlace y rellenad el formulario **con vuestro propio email**.
3. Comprobad que:
   - Aparece una fila nueva en **CRM** con su puntuación y su color.
   - Os llega el email de bienvenida (mirad también en *Spam*).
   - Os llega el aviso de *"Nuevo contacto · Prioridad…"*.
4. Haced capturas: son evidencias de prueba.

Para quitar los clientes ficticios: **Agencia → Borrar clientes de prueba**.

## Paso 6. Conectarlo con la app de VS Code

1. En la hoja: **Archivo → Compartir → Publicar en la web**.
2. En el primer desplegable, cambiad *"Todo el documento"* por **CRM**.
3. En el segundo, cambiad *"Página web"* por **Valores separados por comas (.csv)**.
4. Pulsad **Publicar** y aceptad. Copiad el enlace (termina en `output=csv`).
5. En VS Code, abrid vuestro archivo `.env` (si no lo tenéis, mirad el Paso 4 del README) y añadid una línea:
   ```
   CRM_URL=pega_aqui_el_enlace
   ```
6. Guardad, cerrad la app (`Ctrl + C` en la terminal) y volved a arrancarla.
7. En la barra lateral, elegid la sección **Clientes (CRM)**. Veréis vuestros clientes, los seguimientos pendientes y los gráficos.
8. Abajo del todo, elegid un cliente ganado y pulsad **Ir al informe de este cliente**. La app abre el informe de campaña con su nombre y sus objetivos ya puestos.

> **Ojo con el tiempo de actualización:** Google tarda **unos minutos** en actualizar el enlace publicado. La hoja de Google sí se actualiza al instante. En la demo, enseñad primero la hoja y después pulsad **Actualizar datos** en la app.
>
> **Plan B sin internet o con prisa:** en la hoja, **Archivo → Descargar → Microsoft Excel (.xlsx)**, y en la app elegid *Subir Excel o CSV*.

---

## Guion para la demo en clase (unos 3 minutos)

1. **Proyectad el QR** (Agencia → Ver enlace del formulario y QR) y pedid a dos o tres compañeros que rellenen el formulario desde el móvil.
2. **Enseñad la pestaña CRM:** las solicitudes aparecen solas, con su prioridad y su color.
3. **Enseñad vuestro correo:** ha llegado el aviso de la agencia. El cliente ha recibido su email de bienvenida.
4. **Enseñad el Panel:** los indicadores y gráficos se han actualizado.
5. **Pasad a la app:** sección *Clientes (CRM)* → seguimientos de hoy → elegís *Hilo Verde* → **Ir al informe** → informe de campaña con sus objetivos.

Así se ve todo el recorrido: **captar → organizar → priorizar → hacer seguimiento → informar**.

---

## Protección de datos y seguridad (para la parte de riesgos)

**Qué hace bien la solución:**
- **Consentimiento obligatorio** antes de enviar el formulario, con la información básica de protección de datos.
- **Consentimiento separado y opcional** para recibir publicidad, como exige la normativa.
- **Datos mínimos:** solo se piden los necesarios para preparar una propuesta. El teléfono es opcional.
- En la app, **emails y teléfonos aparecen ocultos** por defecto.
- **A la IA nunca se le envían datos de clientes**, solo cifras de campañas.

**Riesgos y limitaciones que hay que reconocer:**
- **El enlace publicado es público:** cualquiera que lo tenga puede ver el CRM. Usadlo solo con datos de prueba y **dejad de publicarlo al terminar** (Archivo → Compartir → Publicar en la web → *Detener publicación*). En una agencia real habría que conectarlo de forma privada, con la API de Google y permisos.
- **Los emails salen de una cuenta personal de Gmail**, que tiene un límite diario de envíos. Una agencia real usaría su propio dominio (Google Workspace).
- **La prioridad se calcula con reglas fijas:** es una ayuda, no sustituye el criterio del equipo.
- **El formulario no evita respuestas falsas o de spam.** Se podría añadir una verificación.
- El formulario promete **borrar los datos a los 12 meses** si no hay acuerdo, así que la agencia necesitaría un procedimiento para hacerlo.

---

## Problemas frecuentes

| Problema | Solución |
|---|---|
| No aparece el menú *Agencia* | Recargad la página de la hoja (`F5`) |
| Las respuestas no llegan al CRM | En Apps Script, icono del reloj (**Activadores**): debe existir `alEnviarFormulario`. Si no está, ejecutad otra vez *configurarTodo* en una hoja nueva |
| No llega el email | Mirad en *Spam* y comprobad en **Ajustes** que *Enviar email al cliente* está en *Sí* |
| Error de permisos al ejecutar | Volved a ejecutar *configurarTodo* y aceptad todos los permisos |
| La app dice que el enlace no es el CSV publicado | Repetid el Paso 6 eligiendo la pestaña **CRM** y el formato **.csv** |
| La app no muestra el último cliente | Esperad unos minutos y pulsad **Actualizar datos**, o usad el plan B con Excel |
| Queréis cambiar una pregunta del formulario | Podéis añadir preguntas nuevas, pero **no cambiéis el texto de las existentes**: el código las reconoce por su título |
