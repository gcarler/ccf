@echo off
:: inicioccf.bat - Lanzador de Doble Clic para CCF
TITLE Levantando Plataforma CCF - El Faro

:: Ejecutar el script de PowerShell con política de bypass para evitar errores de permisos
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0inicioccf.ps1"

:: Si el script falla por alguna razón, dejar la ventana abierta para ver el error
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Hubo un problema al iniciar los servicios.
    pause
)
