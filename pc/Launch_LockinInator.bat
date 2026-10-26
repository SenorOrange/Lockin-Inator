@echo off
where pythonw >nul 2>nul
if %errorlevel% equ 0 (
    start "" pythonw "%~dp0main.py"
) else (
    start "" pyw "%~dp0main.py"
)
