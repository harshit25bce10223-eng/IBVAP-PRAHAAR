@echo off
title PRAHAAR - Universal Startup
color 0A

echo.
echo  ============================================================
echo   PRAHAAR - AI-Powered Intelligent Border Surveillance
echo   Universal One-Click Startup
echo  ============================================================
echo.

set BACKEND=C:\SIH\ibvap-backend
set FRONTEND=C:\SIH\ibvap-frontend

echo [1/2] Starting Backend (FastAPI on port 8000)...
start "PRAHAAR BACKEND :8000" cmd /k "cd /d C:\SIH\ibvap-backend && echo. && echo  [BACKEND] http://127.0.0.1:8000 && echo  [BACKEND] Docs: http://127.0.0.1:8000/docs && echo. && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"

ping -n 3 127.0.0.1 > nul

echo [2/2] Starting Frontend (Vite on port 5173)...
start "PRAHAAR FRONTEND :5173" cmd /k "cd /d C:\SIH\ibvap-frontend && echo. && echo  [FRONTEND] http://127.0.0.1:5173 && echo. && npm run dev"

ping -n 5 127.0.0.1 > nul

start "" "http://127.0.0.1:5173"

echo.
echo  ============================================================
echo   ALL SYSTEMS GO!
echo.
echo   Frontend  --  http://127.0.0.1:5173
echo   Backend   --  http://127.0.0.1:8000
echo   API Docs  --  http://127.0.0.1:8000/docs
echo.
echo   Close the two CMD windows to stop services.
echo  ============================================================
echo.
pause
