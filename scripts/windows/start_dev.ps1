# CCF Platform - Dev Server Starter
# Ejecuta este script desde d:\ccf para arrancar el entorno completo

Write-Host ""
Write-Host "=== CCF Mesh Platform - Dev Environment ===" -ForegroundColor Cyan
Write-Host ""

# 1. Backend (necesita PostgreSQL corriendo en puerto 5435)
Write-Host "[1/2] Starting Backend on :8000..." -ForegroundColor Yellow
$backend = Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd d:\ccf; `$env:PYTHONPATH='d:\ccf'; cd backend; python -m uvicorn app:app --reload --port 8000" -PassThru

Start-Sleep -Seconds 3

# 2. Frontend
Write-Host "[2/2] Starting Frontend on :3000..." -ForegroundColor Yellow
$frontend = Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd d:\ccf\frontend; npm run dev" -PassThru

Write-Host ""
Write-Host "=== Services Starting ===" -ForegroundColor Green
Write-Host "  Backend:  http://localhost:8000" -ForegroundColor White
Write-Host "  Frontend: http://localhost:3000" -ForegroundColor White
Write-Host "  API Docs: http://localhost:8000/docs" -ForegroundColor White
Write-Host ""
Write-Host "Note: Make sure PostgreSQL is running on port 5435" -ForegroundColor DarkYellow
