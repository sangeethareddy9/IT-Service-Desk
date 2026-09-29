@echo off
cd /d "%~dp0"
py -3 scripts\setup.py --demo
if errorlevel 1 (
  echo Setup stopped. Please read the error above and START_HERE.md.
) else (
  echo Save the generated login passwords shown above, then open START_WINDOWS.bat.
)
pause
