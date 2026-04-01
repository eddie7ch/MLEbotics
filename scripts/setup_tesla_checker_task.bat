@echo off
:: Creates a Windows Task Scheduler job to run the Tesla inventory checker daily at 9:00 AM

set SCRIPT_PATH=d:\MLEbotics\scripts\tesla_inventory_checker.py
set TASK_NAME=TeslaInventoryChecker

echo Setting up daily Tesla inventory check at 9:00 AM...

schtasks /create ^
  /tn "%TASK_NAME%" ^
  /tr "python \"%SCRIPT_PATH%\"" ^
  /sc daily ^
  /st 09:00 ^
  /f ^
  /rl highest

if %ERRORLEVEL% EQU 0 (
    echo.
    echo SUCCESS: Task "%TASK_NAME%" created.
    echo It will run daily at 9:00 AM.
    echo.
    echo To view:   schtasks /query /tn "%TASK_NAME%" /fo list
    echo To run now: schtasks /run /tn "%TASK_NAME%"
    echo To delete: schtasks /delete /tn "%TASK_NAME%" /f
) else (
    echo FAILED: Could not create task. Try running this as Administrator.
)

pause
