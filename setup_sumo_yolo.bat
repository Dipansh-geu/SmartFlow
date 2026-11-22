@echo off
setlocal
py -m venv .venv
call .venv\Scripts\activate
py -m pip install --upgrade pip
py -m pip install -r requirements.txt
echo.
echo Set SUMO_HOME to your SUMO installation directory, then reopen this terminal.
echo Example: SUMO_HOME=C:\Program Files (x86)\Eclipse\Sumo
pause
