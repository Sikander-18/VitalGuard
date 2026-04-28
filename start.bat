@echo off
echo ============================================
echo   VitalGuard v2 - Starting All Services
echo ============================================
echo.

:: 0. Kill old instances to avoid port conflicts
taskkill /F /FI "WINDOWTITLE eq VitalGuard Backend*" >nul 2>&1
taskkill /F /FI "WINDOWTITLE eq BLE Relay*" >nul 2>&1
taskkill /F /FI "WINDOWTITLE eq VitalGuard Frontend*" >nul 2>&1
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING 2^>nul') do taskkill /F /PID %%a >nul 2>&1
timeout /t 1 /nobreak >nul

:: 1. Backend (FastAPI + 5-Agent LangGraph + Rule Engine)
echo [1/3] Starting Backend (FastAPI + AI Pipeline)...
start "VitalGuard Backend" cmd /k "pushd "d:\VitalGuard 2.0\server" & python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000"

timeout /t 3 /nobreak >nul

:: 2. BLE Hardware Relay (optional - for real sensor data)
echo [2/3] Starting BLE Relay (optional)...
start "BLE Relay" cmd /k "pushd "d:\VitalGuard 2.0\ble-relay" & python relay.py"

timeout /t 2 /nobreak >nul

:: 3. Frontend (React + Vite)
echo [3/3] Starting Frontend (React Dashboard)...
start "VitalGuard Frontend" cmd /k "pushd "d:\VitalGuard 2.0\frontend" & npm run dev"

timeout /t 3 /nobreak >nul

:: 4. Seed demo data
echo.
echo Seeding demo data...
curl -s -X POST http://localhost:8000/simulate/seed >nul 2>&1
echo Done!

echo.
echo ============================================
echo   All services started!
echo ============================================
echo.
echo   Backend   -^> http://localhost:8000
echo   BLE Relay -^> http://localhost:5000
echo   Frontend  -^> http://localhost:8080
echo.
echo   API Docs  -^> http://localhost:8000/docs
echo   Health    -^> http://localhost:8000/system/status
echo.
echo   Test: curl -X POST "http://localhost:8000/simulate/scenario?scenario=critical&user_id=U002"
echo ============================================
