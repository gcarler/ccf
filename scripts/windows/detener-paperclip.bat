@echo off
setlocal

title Paperclip Stopper

echo ============================================
echo   Deteniendo Paperclip...
echo ============================================

set "FOUND=0"

for /f "tokens=5" %%P in ('netstat -ano ^| findstr ":3100" ^| findstr "LISTENING"') do (
  echo [INFO] Cerrando proceso PID %%P (puerto 3100)
  taskkill /PID %%P /F >nul 2>nul
  set "FOUND=1"
)

if "%FOUND%"=="0" (
  echo [INFO] No se encontro Paperclip escuchando en el puerto 3100.
) else (
  echo [OK] Paperclip detenido.
)

echo.
pause
