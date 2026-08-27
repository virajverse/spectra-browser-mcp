@echo off
setlocal
title SpectraBrowser MCP Setup
echo ========================================================
echo   🚀 SpectraBrowser MCP - Automated Installation
echo   World-Class Autonomous Cognitive Browser QA Suite
echo ========================================================

if not exist ".venv" (
    echo [1/4] Creating virtual environment (.venv)...
    python -m venv .venv
) else (
    echo [1/4] Existing virtual environment found.
)

echo [2/4] Activating environment and upgrading pip...
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip

echo [3/4] Installing dependencies...
python -m pip install -r requirements.txt
python -m pip install -e .

echo [4/4] Installing Playwright Chromium browser...
python -m playwright install chromium

echo.
echo ========================================================
echo   ✅ SpectraBrowser MCP installed successfully!
echo.
echo   To start the Open WebUI / OpenAPI Bridge (Port 8002):
echo     run_bridge.bat
echo.
echo   To run as direct FastMCP Server (STDIO):
echo     .venv\Scripts\python.exe -m browser_qa.server
echo ========================================================
pause
