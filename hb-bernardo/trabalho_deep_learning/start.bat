@echo off
echo ============================================
echo   Multiopen AI - Assistente Local Multimodal
echo   Powered by Gemma4:e4b via Ollama
echo ============================================
echo.

REM Verificar se o Ollama está a correr
ollama list >nul 2>&1
if errorlevel 1 (
    echo [ERRO] Ollama nao esta a correr! Inicia o Ollama primeiro.
    pause
    exit /b 1
)

echo [OK] Ollama detectado.

REM Ativar ambiente virtual
call "%~dp0venv\Scripts\activate.bat"

echo [OK] Ambiente virtual ativado.
echo.
echo A iniciar Multiopen AI em http://localhost:8000
echo Prima Ctrl+C para parar.
echo.

cd /d "%~dp0"
python backend\main.py
