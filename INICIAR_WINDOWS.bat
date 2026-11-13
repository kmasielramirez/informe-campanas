@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Informe automatico de campanas
echo.
echo   ==============================================
echo     INFORME AUTOMATICO DE CAMPANAS
echo   ==============================================
echo.

set "PY="
where py >nul 2>nul && set "PY=py"
if not defined PY (where python >nul 2>nul && set "PY=python")
if not defined PY goto nopython

if not exist ".venv\Scripts\python.exe" (
  echo   Primera vez: preparando Python para el proyecto.
  echo   Tardara unos minutos. No cierres esta ventana.
  echo.
  %PY% -m venv .venv || goto error
)

echo   Comprobando las librerias necesarias...
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -r requirements.txt || goto error

rem Evita que Streamlit pida un email la primera vez
if not exist "%USERPROFILE%\.streamlit\credentials.toml" (
  mkdir "%USERPROFILE%\.streamlit" 2>nul
  > "%USERPROFILE%\.streamlit\credentials.toml" echo [general]
  >> "%USERPROFILE%\.streamlit\credentials.toml" echo email = ""
)

echo.
echo   Abriendo la herramienta en el navegador: http://localhost:8501
echo   Para cerrarla, cierra esta ventana o pulsa Ctrl+C.
echo.
".venv\Scripts\python.exe" -m streamlit run app.py
pause
exit /b 0

:nopython
echo   No se encuentra Python en este ordenador.
echo   1. Descargalo de https://www.python.org/downloads/
echo   2. En el instalador, MARCA la casilla "Add python.exe to PATH".
echo   3. Vuelve a abrir este archivo.
echo.
pause
exit /b 1

:error
echo.
echo   Algo ha fallado al preparar la herramienta.
echo   Comprueba la conexion a internet y vuelve a intentarlo.
echo   Si sigue fallando, borra la carpeta .venv y abre otra vez este archivo.
echo.
pause
exit /b 1
