@echo off
cd /d "%~dp0"
start /B "" "C:\Users\user\AppData\Local\Programs\Python\Python313\Scripts\streamlit.exe" run app.py --server.headless true
timeout /t 5 /nobreak > nul
start "" "http://localhost:8501"
echo.
echo App is running at http://localhost:8501
echo Close this window to stop the app.
pause > nul
