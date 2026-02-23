@echo off
REM Run Blackjack Statistics Dashboard (Streamlit)

cd /d "%~dp0..\..\.."
echo Starting Blackjack Statistics Dashboard...
streamlit run statistics_dashboard/app.py

pause
