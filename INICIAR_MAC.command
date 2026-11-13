#!/bin/bash
# Arranca la herramienta en Mac. Desde la terminal de VS Code: bash INICIAR_MAC.command
cd "$(dirname "$0")" || exit 1
echo ""
echo "  =============================================="
echo "    INFORME AUTOMÁTICO DE CAMPAÑAS"
echo "  =============================================="
echo ""

if ! command -v python3 >/dev/null 2>&1; then
  echo "  No se encuentra Python en este ordenador."
  echo "  Descárgalo de https://www.python.org/downloads/ e instálalo."
  read -r -p "  Pulsa Enter para cerrar..."
  exit 1
fi

if [ ! -x ".venv/bin/python" ]; then
  echo "  Primera vez: preparando Python para el proyecto."
  echo "  Tardará unos minutos. No cierres esta ventana."
  python3 -m venv .venv || { echo "  No se ha podido crear el entorno."; read -r -p "  Pulsa Enter para cerrar..."; exit 1; }
fi

echo "  Comprobando las librerías necesarias..."
if ! .venv/bin/python -m pip install --disable-pip-version-check -r requirements.txt; then
  echo ""
  echo "  Algo ha fallado al instalar. Comprueba la conexión a internet."
  echo "  Si aparece un error de 'certificate', abre la carpeta Aplicaciones > Python 3.x"
  echo "  y haz doble clic en 'Install Certificates.command'. Después vuelve a intentarlo."
  read -r -p "  Pulsa Enter para cerrar..."
  exit 1
fi

# Evita que Streamlit pida un email la primera vez
if [ ! -f "$HOME/.streamlit/credentials.toml" ]; then
  mkdir -p "$HOME/.streamlit"
  printf '[general]\nemail = ""\n' > "$HOME/.streamlit/credentials.toml"
fi

echo ""
echo "  Abriendo la herramienta en el navegador: http://localhost:8501"
echo "  Para cerrarla, pulsa Ctrl+C en esta ventana."
echo ""
.venv/bin/python -m streamlit run app.py
