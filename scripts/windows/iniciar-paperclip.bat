@echo off
setlocal

title Paperclip Launcher

echo ============================================
echo   Iniciando Paperclip...
echo ============================================

where paperclipai >nul 2>nul
if %errorlevel% neq 0 (
  echo [INFO] paperclipai no esta en PATH. Usando npx.
  set "PC_CMD=npx paperclipai"
) else (
  set "PC_CMD=paperclipai"
)

echo [INFO] Abriendo interfaz en el navegador...
start "" "http://127.0.0.1:3100"

echo [INFO] Ejecutando: %PC_CMD% run
echo [INFO] Deja esta ventana abierta mientras uses Paperclip.
echo.

call %PC_CMD% run

echo.
echo [WARN] Paperclip se detuvo o cerro.
pause
