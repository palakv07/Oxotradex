@echo off
REM ==============================================================================
REM Oxotradex: Autonomous Options Alpha Agent - Windows Runner
REM ==============================================================================

echo [INFO] Starting Oxotradex Autonomous Options Alpha Agent...

REM Check if .env exists
if not exist .env (
    echo [WARNING] .env not found! Copying .env.example to .env...
    copy .env.example .env
    echo [IMPORTANT] Please update .env with your Alpaca Paper API Keys!
)

REM Run agent
python src\main.py %*
