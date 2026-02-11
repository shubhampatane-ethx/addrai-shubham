@echo off
echo ============================================
echo Address Validation Platform - Startup
echo ============================================
echo.

REM Check if Docker is running
docker --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Docker is not installed or not running
    echo Please install Docker Desktop from: https://www.docker.com/products/docker-desktop
    pause
    exit /b 1
)

echo [OK] Docker is installed
echo.

REM Check if .env exists
if not exist .env (
    echo Creating .env from template...
    copy .env.example .env
    echo [OK] .env file created
) else (
    echo [OK] .env file exists
)

echo.
echo Building and starting containers...
echo This may take 3-5 minutes on first run
echo.

docker-compose up --build -d

echo.
echo Waiting for services to be ready...
timeout /t 10 /nobreak >nul

echo.
echo ============================================
echo System is STARTING!
echo ============================================
echo.
echo Access Points:
echo   Frontend:  http://localhost
echo   API Docs:  http://localhost:8000/api/docs
echo   Health:    http://localhost:8000/api/v1/health
echo.
echo Quick Start:
echo   1. Visit: http://localhost
echo   2. Upload Excel file
echo   3. Click 'Start Validation'
echo.
echo Useful Commands:
echo   View logs:    docker-compose logs -f
echo   Stop:         docker-compose down
echo   Restart:      docker-compose restart
echo.
echo Setup complete!
echo.
pause
