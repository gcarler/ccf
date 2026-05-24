@echo off
setlocal enabledelayedexpansion

:: ============================================
:: failover-check.bat
:: Script de failover automatico A/B para PLE
:: Team A = Codex local (GPT models)
:: Team B = Codex OSS (Ollama local models)
:: ============================================

set "TEAM_A_MODEL=%~1"
set "TEAM_B_MODEL=%~2"
set "TASK=%~3"
set "ROLE=%~4"

if "%TEAM_A_MODEL%"=="" goto usage
if "%TEAM_B_MODEL%"=="" goto usage
if "%TASK%"=="" goto usage
if "%ROLE%"=="" set "ROLE=default"

echo ============================================
echo PLE Failover Check
echo ============================================
echo Role: %ROLE%
echo Team A: %TEAM_A_MODEL%
echo Team B: %TEAM_B_MODEL%
echo Task: %TASK%
echo.

:: Team A attempt
echo [A] Intentando con Team A (%TEAM_A_MODEL%)...
codex exec -m %TEAM_A_MODEL% "%TASK%"
set "EXIT_A=%ERRORLEVEL%"

if %EXIT_A% EQU 0 (
    echo.
    echo [OK] Team A exitoso.
    goto success
)

echo.
echo [WARN] Team A fallo (exit code: %EXIT_A%)
echo [A] Detectando motivo de fallo...

:: Detect failover triggers
:: Common failure patterns: rate limit, auth, quota, timeout

echo.
echo ============================================
echo [A] Failsafe: Ejecutando Team B (%TEAM_B_MODEL%)...
echo ============================================
echo.

codex exec --oss --local-provider ollama -m %TEAM_B_MODEL% "%TASK%"
set "EXIT_B=%ERRORLEVEL%"

if %EXIT_B% EQU 0 (
    echo.
    echo [OK] Team B exitoso.
    echo [LOG] Failover: %ROLE% %TEAM_A_MODEL% -^> %TEAM_B_MODEL%
    goto success
)

echo.
echo [ERROR] Team B tambien fallo (exit code: %EXIT_B%)
echo [ERROR] Ambos equipos fallaron. Requiere intervencion manual.
exit /b 1

:success
echo.
echo [DONE] Tarea completada exitosamente.
exit /b 0

:usage
echo.
echo ============================================
echo uso: failover-check.bat ^<model_A^> ^<model_B^> ^"^task^" ^"^role^"
echo ============================================
echo.
echo ejemplos:
echo   failover-check.bat o3 qwen3:8b "Analiza el backlog de PLE" "CEO"
echo   failover-check.bat gpt-5.4 qwen3:8b "Revisa la arquitectura" "CTO"
echo   failover-check.bat gpt-5.3-codex qwen2.5-coder:7b "Escribe tests para auth" "Backend"
echo   failover-check.bat o4-mini qwen2.5-coder:7b "Crea plan de regression" "QA"
echo   failover-check.bat gpt-5-mini qwen3:8b "Triage incidente PLE-1" "Support"
echo.
echo Modelos Team A validados: o3, gpt-5.4, gpt-5.3-codex, o4-mini, gpt-5-mini
echo Modelos Team B validados: qwen3:8b, qwen2.5-coder:7b
echo.
exit /b 1