@echo off
setlocal
title SpectraBrowser OpenAPI Bridge (Port 8002)
echo ========================================================
echo   🌐 Starting SpectraBrowser MCP Bridge on Port 8002...
echo   Open WebUI URL: http://localhost:8002/openapi.json
echo ========================================================
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
)
python openapi_bridge.py
pause
