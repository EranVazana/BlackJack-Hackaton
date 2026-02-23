@echo off
REM Run Blackjack CLI Client

cd /d "%~dp0..\..\.."
echo Starting Blackjack CLI Client...
python -m client.cli

pause
