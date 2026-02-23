@echo off
REM Run Blackjack Server

cd /d "%~dp0..\..\.."
echo Starting Blackjack Server...
python -m server.server

pause
