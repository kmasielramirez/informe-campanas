# Agencia del futuro: captación de clientes e informes automáticos

El proyecto tiene dos herramientas conectadas:

1. **Captación de clientes (Google Forms + Google Sheets):** un formulario para posibles clientes que llena solo un CRM, calcula la prioridad y envía emails automáticos. Se monta siguiendo **GUIA_GOOGLE.md**.
2. **Informes automáticos (esta app de VS Code):** convierte los datos de una campaña en un informe y, en la sección *Clientes (CRM)*, muestra los clientes que llegan del formulario.

Recorrido completo: **el cliente rellena el formulario → el CRM lo organiza y prioriza → la agencia hace el seguimiento → cuando la campaña está en marcha, la app genera su informe con los objetivos del cliente.**

## Herramienta de informes

Herramienta que convierte los datos de una campaña de marketing (un CSV o un Excel) en un **informe visual con indicadores, conclusiones y recomendaciones** en menos de un segundo. Además, puede pedir a una IA (Gemini) que redacte el informe para el cliente y **comprueba automáticamente las cifras** que escribe la IA.

Proyecto: *Marketing 4.0 · La agencia del futuro* · Reto B: informes de marketing automáticos.

> **Consejo:** en VS Code, para leer esta guía con formato, pulsa `Ctrl + Mayús + V` (Windows) o `Cmd + Mayús + V` (Mac).

---

## Qué hay en esta carpeta

| Archivo o carpeta | Para qué sirve |
|---|---|
| `INICIAR_WINDOWS.bat` | Prepara todo y abre la herramienta en Windows |
| `INICIAR_MAC.command` | Lo mismo en Mac |
| `app.py` | La pantalla de la herramienta (lo que se ve en el navegador) |
| `informe.py` | El "cerebro": revisa los datos, calcula los KPIs y saca conclusiones |
| `clientes.py` | La sección *Clientes (CRM)*: lee el CRM de Google Sheets |
| `google/Codigo.gs` | Código que crea el formulario, el CRM y los emails en Google |
| `GUIA_GOOGLE.md` | Guía paso a paso para montar el formulario y el CRM |
| `datos/` | Tres campañas ficticias y un CRM de ejemplo para hacer las pruebas |
| `.env.example` | Plantilla para guardar la clave de la IA |
| `evidencias/` | Aparece cuando guardáis la primera prueba: es vuestro registro de pruebas |
| `requirements.txt` | Lista de librerías de Python que se instalan solas |

No hace falta tocar el código para usar la herramienta.

---

## Paso 1. Instalar Python (solo una vez)

**Windows**
1. Entra en https://www.python.org/downloads/ y pulsa el botón amarillo **Download Python**.
2. Abre el instalador.
3. **Muy importante:** antes de nada, marca abajo la casilla **"Add python.exe to PATH"**.
4. Pulsa **Install Now** y espera a que termine.

**Mac**
1. Entra en https://www.python.org/downloads/ y descarga el instalador para macOS.
2. Instálalo como cualquier programa.
3. Al terminar, se abre una carpeta de Python. Haz doble clic en **Install Certificates.command** (evita errores al descargar librerías).

---

## Paso 2. Abrir el proyecto en VS Code

1. Si no lo tenéis, instalad VS Code desde https://code.visualstudio.com/
2. **Descomprimid el ZIP** (clic derecho → *Extraer todo* en Windows, doble clic en Mac). No trabajéis dentro del ZIP sin descomprimir.
3. En VS Code: **Archivo → Abrir carpeta…** y elegid la carpeta `informe-campanas`.
4. Si pregunta *"¿Confías en los autores?"*, pulsad **Sí, confío**.
5. Opcional: VS Code os sugerirá instalar la extensión **Python** de Microsoft. Aceptad: colorea el código y lo hace más fácil de leer.

---

## Paso 3. Arrancar la herramienta

1. En VS Code: menú **Terminal → Nuevo terminal**. Se abre un panel abajo.
2. Escribid este comando y pulsad Enter:
   - **Windows:** `.\INICIAR_WINDOWS.bat`
   - **Mac:** `bash INICIAR_MAC.command`
3. **La primera vez tarda entre 2 y 5 minutos** porque descarga las librerías. Veréis mucho texto: es normal.
4. Se abrirá el navegador con la herramienta. Si no se abre solo, entrad en **http://localhost:8501**
5. Para cerrarla: haced clic en la terminal y pulsad `Ctrl + C`.

Las siguientes veces arranca en pocos segundos. En Windows también podéis hacer doble clic en `INICIAR_WINDOWS.bat` sin abrir VS Code.

---

## Paso 4 (opcional). Activar la IA

La herramienta funciona sin IA. La IA solo añade el botón **"Redactar informe con IA"**.

1. Entrad en https://aistudio.google.com/apikey con una cuenta de Google.
2. Pulsad **Create API key** y copiad la clave.
3. En VS Code, clic derecho sobre `.env.example` → **Copiar**, y después clic derecho en un hueco vacío → **Pegar**. Cambiad el nombre de la copia a **`.env`** (solo eso, con el punto delante).
4. Abrid `.env`, sustituid `pega_aqui_tu_clave` por vuestra clave y guardad (`Ctrl + S` / `Cmd + S`).
5. Cerrad la herramienta (`Ctrl + C`) y volved a arrancarla.

**Importante sobre la seguridad (os sirve para la presentación):**
- La clave es secreta, como una contraseña: no la pongáis en la presentación ni la compartáis por WhatsApp.
- En el nivel gratuito, Google puede usar lo que se envía para mejorar sus productos. Por eso la herramienta **solo envía totales por canal**, nunca datos personales de clientes. Usad datos ficticios o agregados.

---

## Paso 5. Hacer las pruebas y guardar evidencias

El proyecto pide probar la solución con casos concretos y guardar evidencias. Os propongo estas cuatro pruebas:

| Prueba | Qué hacer | Qué debería pasar |
|---|---|---|
| 1. Campaña de moda | Ejemplo *Hilo Verde* | Detecta que **Display pierde dinero** y recomienda mover su presupuesto a Google Ads |
| 2. Campaña de gimnasio | Ejemplo *Fit Pisuerga* | Detecta que el CPA no cumple el objetivo y que Meta Ads mejora semana a semana |
| 3. Datos con errores | Ejemplo *Archivo con errores* | Encuentra 6 incidencias: fecha imposible, gasto negativo, más clics que impresiones, fila repetida… |
| 4. La IA | Botón *Redactar informe con IA* | La herramienta marca las cifras de la IA que no están en los datos |

En cada prueba:
1. Revisad el informe y, si usáis la IA, marcad la checklist de revisión.
2. Id a la pestaña **Descargar y registrar**, escribid los minutos que tardaríais a mano y una nota, y pulsad **Guardar esta prueba en el registro**.
3. Haced capturas de pantalla (`Win + Mayús + S` en Windows, `Cmd + Mayús + 4` en Mac).
4. Descargad el informe HTML: es el resultado que recibiría el cliente.

El registro se guarda en `evidencias/registro_pruebas.csv` y se abre con Excel.

---

## Usar vuestros propios datos

Podéis copiar uno de los CSV de `datos/`, abrirlo con Excel, cambiar los números y guardarlo como CSV. El archivo necesita **una fila por día y canal** con estas columnas:

| Columna | Ejemplo | Obligatoria |
|---|---|---|
| `fecha` | 2026-03-02 o 02/03/2026 | Sí |
| `canal` | Instagram Ads | Sí |
| `impresiones` | 8371 | Sí |
| `clics` | 106 | Sí |
| `conversiones` | 2 | Sí |
| `gasto` | 51,88 | Sí |
| `ingresos` | 144,74 | No (sin ella no se calcula el ROAS) |

También reconoce nombres parecidos: *inversión*, *coste*, *ventas*, *clicks*, *pedidos*…

---

## Cómo funciona por dentro (para explicarlo en la presentación)

1. **Lectura:** abre el CSV o el Excel, sea con comas o con punto y coma.
2. **Revisión de datos:** reconoce columnas con otros nombres, elimina filas repetidas, descarta fechas imposibles, valores negativos o vacíos y filas con más clics que impresiones, y unifica canales mal escritos.
3. **Cálculo de KPIs** por canal y por semana:
   - **CTR** = clics ÷ impresiones (cuánta gente hace clic)
   - **CPC** = gasto ÷ clics (cuánto cuesta cada clic)
   - **CPA** = gasto ÷ conversiones (cuánto cuesta cada venta o cliente)
   - **ROAS** = ventas ÷ gasto (euros vendidos por cada euro invertido; por debajo de 1 se pierde dinero)
4. **Conclusiones automáticas** con reglas fijas: mejor y peor canal, objetivos, tendencias, CTR bajo…
5. **IA (opcional):** Gemini redacta el informe con los datos ya calculados. La IA no calcula nada: solo redacta.
6. **Control de la IA:** la herramienta compara cada cifra del texto con los datos que se le enviaron y avisa de las que no coinciden. Después, el equipo revisa con una checklist.
7. **Entrega:** informe HTML descargable y registro de pruebas.

**Herramientas utilizadas:** Google Forms y Google Sheets con Apps Script (captación y CRM), Gmail (emails automáticos), Python, Streamlit (pantalla web), pandas (cálculos), Plotly (gráficos), Gemini de Google (IA) y VS Code (desarrollo).

**Sección Clientes (CRM):** en la barra lateral, elegid *Clientes (CRM)*. Lee los clientes del enlace publicado de Google Sheets, de un Excel descargado o del ejemplo incluido. Muestra los indicadores, los seguimientos pendientes y los gráficos, y tiene un botón para abrir el informe de campaña de un cliente con sus objetivos ya puestos. Los emails y teléfonos aparecen ocultos por defecto.

---

## Riesgos y limitaciones

- **Los datos de entrada mandan:** si el archivo tiene errores que parecen correctos (por ejemplo, un gasto mal copiado pero positivo), la herramienta no los puede detectar.
- **Las recomendaciones son orientativas:** las estimaciones suponen que cada canal mantiene su rendimiento si se le da más presupuesto, algo que no siempre ocurre.
- **La IA puede equivocarse o inventar:** por eso se comprueban sus cifras y una persona revisa el texto antes de enviarlo.
- **Privacidad:** en el nivel gratuito de Gemini, Google puede usar los datos enviados. Solo se envían totales por canal, nunca datos personales.
- **Es un prototipo local:** funciona en vuestro ordenador. Para usarlo en una agencia habría que publicarlo en un servidor con usuarios y contraseñas.
- **Mejoras futuras:** conectar directamente con Meta Ads o Google Ads para no tener que exportar archivos, enviar el informe por email cada lunes y comparar con campañas anteriores.

---

## Si Windows bloquea Python: VS Code en el navegador (GitHub Codespaces)

Si aparece *"Una directiva de Control de aplicaciones bloqueó este archivo"*, Windows no deja ejecutar las librerías de Python. Podéis usar el mismo proyecto en **VS Code dentro del navegador**, que funciona en la nube y no depende de vuestro ordenador:

1. Cread una cuenta gratis en https://github.com
2. Pulsad **+ → New repository**. Nombre: `informe-campanas`. Marcad **Private** y pulsad **Create repository**.
3. Pulsad el enlace **uploading an existing file**.
4. Descomprimid el ZIP en una carpeta nueva, abridla, seleccionad **todo su contenido** (`Ctrl + A`) y arrastradlo a la página de GitHub. **No subáis nunca** la carpeta `.venv` ni el archivo `.env` (lleva vuestra clave).
5. Esperad a que se suban todos los archivos y pulsad **Commit changes**.
6. Pulsad el botón verde **Code → Codespaces → Create codespace on main**.
7. Se abre VS Code en el navegador. La primera vez tarda 2 o 3 minutos en preparar todo y después **la app se abre sola** en un panel. Si no, id a la pestaña **Puertos** (abajo), buscad el 8501 y pulsad el icono del globo.
8. Para la clave de Gemini y el enlace del CRM: cread ahí el archivo `.env` igual que en el Paso 4 (no se sube a GitHub).

Las siguientes veces: https://github.com/codespaces y abrid el que ya tenéis. Cuando terminéis, cerrad la pestaña; el Codespace se detiene solo al rato.

## Problemas frecuentes

| Problema | Solución |
|---|---|
| *"No se encuentra Python"* o *"py no se reconoce"* | Reinstalad Python marcando **"Add python.exe to PATH"** y cerrad y abrid VS Code |
| En Windows, la terminal no deja ejecutar el archivo | Escribid `cmd` y Enter en la terminal, y después `INICIAR_WINDOWS.bat` |
| En Mac sale *"no se puede abrir porque es de un desarrollador no identificado"* | Usad la terminal de VS Code con `bash INICIAR_MAC.command` |
| Error de *certificate* o *SSL* en Mac | Aplicaciones → Python 3.x → doble clic en **Install Certificates.command** |
| El navegador no se abre | Entrad a mano en http://localhost:8501 |
| *"La clave de Gemini no es válida"* | Revisad que el archivo se llama exactamente `.env` y que la clave está entera, sin espacios |
| *"Has llegado al límite gratuito"* | Esperad un minuto: el nivel gratuito limita las peticiones por minuto |
| Algo se rompe al instalar | Borrad la carpeta `.venv` y volved a arrancar |
| *"Una directiva de Control de aplicaciones bloqueó este archivo"* | Windows bloquea las librerías: usad otro ordenador o VS Code en el navegador (sección anterior) |
| *"Windows protegió su PC"* al abrir el .bat | Pulsad **Más información → Ejecutar de todas formas**, o escribid los comandos a mano en la terminal |
