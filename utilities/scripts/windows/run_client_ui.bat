@echo off
REM Run Blackjack UI Client (Streamlit)

cd /d "%~dp0..\..\.."
echo Starting Blackjack UI Client...
streamlit run client/ui.py

pause
