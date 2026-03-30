# inicioccf.ps1 - Lanzador oficial de la plataforma CCF para PowerShell

$Host.UI.RawUI.WindowTitle = "Levantando Plataforma CCF..."

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "   INICIANDO SERVICIOS EL FARO / CCF    " -ForegroundColor White -BackgroundColor Blue
Write-Host "==========================================" -ForegroundColor Cyan

# Directorios de trabajo
$RootDir = Get-Location
$FrontendDir = Join-Path $RootDir "frontend"
$BackendLog = Join-Path $RootDir "backend-dev.log"
$FrontendLog = Join-Path $RootDir "frontend.log"

# 1. Verificar Entorno Virtual (venv)
$VenvPath = Join-Path $RootDir "venv\Scripts\python.exe"
$PythonCmd = "python"
if (Test-Path $VenvPath) {
    $PythonCmd = $VenvPath
    Write-Host "[OK] Entorno virtual detectado." -ForegroundColor Green
} else {
    Write-Host "[!] Advertencia: No se detectó venv, usando python global." -ForegroundColor Yellow
}

# 2. Levantar Backend (Puerto 8000)
Write-Host "[1/2] Iniciando Backend en http://localhost:8000..." -ForegroundColor Cyan
Start-Process -FilePath $PythonCmd -ArgumentList "-m uvicorn backend.main:app --reload --port 8000" -WindowStyle Normal

# 3. Levantar Frontend (Puerto 3000)
Write-Host "[2/2] Iniciando Frontend en http://localhost:3000..." -ForegroundColor Cyan
if (Test-Path $FrontendDir) {
    Set-Location $FrontendDir
    Start-Process -FilePath "npm.cmd" -ArgumentList "run dev" -WindowStyle Normal
    Set-Location $RootDir
} else {
    Write-Host "[ERROR] No se encontró la carpeta 'frontend'." -ForegroundColor Red
}

Write-Host "`n==========================================" -ForegroundColor Green
Write-Host " SISTEMA LEVANTADO EXITOSAMENTE " -ForegroundColor Black -BackgroundColor Green
Write-Host "==========================================" -ForegroundColor Green
Write-Host "Acceso rápido:"
Write-Host "- FRONTEND: http://localhost:3000" -ForegroundColor Yellow
Write-Host "- BACKEND API: http://localhost:8000/docs" -ForegroundColor Yellow
Write-Host "=========================================="
Write-Host "Presiona cualquier tecla para cerrar este mensaje (los servicios seguirán corriendo en ventanas separadas)."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
