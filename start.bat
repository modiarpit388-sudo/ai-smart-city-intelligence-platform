@echo off
REM One-command start for Windows:  double-click start.bat
cd /d "%~dp0backend"
if not exist .venv (
  echo Creating Python virtual environment ...
  python -m venv .venv
)
call .venv\Scripts\activate.bat
pip install -q -r requirements.txt
if not exist static\index.html (
  where npm >nul 2>nul
  if %errorlevel%==0 (
    echo Building the React frontend ...
    pushd ..\frontend
    call npm install --no-audit --no-fund
    call npm run build
    popd
  ) else (
    echo npm not found - the API will run without the UI.
  )
)
python run.py
pause
