@echo off
echo ===================================================
echo   Starting DDR Web Application
echo ===================================================

:: Activate Python Environment
echo [1/3] Activating Virtual Environment...
call ddr_generator\venv\Scripts\activate.bat

:: Start Backend in Background
echo [2/3] Starting Backend Server (FastAPI)...
start /B python ddr_generator/server.py
timeout /t 5 >nul

:: Start Frontend
echo [3/3] Starting Frontend (React)...
cd frontend
npm run dev

pause
