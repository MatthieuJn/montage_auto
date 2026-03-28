@echo off
chcp 65001 >nul
echo.
echo  ====================================
echo   Analyse des videos pour le montage
echo  ====================================
echo.
cd /d "%~dp0"
set "PROJECT_ROOT=%~dp0.."

if exist "%PROJECT_ROOT%\.venv\Scripts\python.exe" (
	"%PROJECT_ROOT%\.venv\Scripts\python.exe" "%PROJECT_ROOT%\outil\analyse.py"
) else if exist "%PROJECT_ROOT%\venv\Scripts\python.exe" (
	"%PROJECT_ROOT%\venv\Scripts\python.exe" "%PROJECT_ROOT%\outil\analyse.py"
) else if exist "%PROJECT_ROOT%\env\Scripts\python.exe" (
	"%PROJECT_ROOT%\env\Scripts\python.exe" "%PROJECT_ROOT%\outil\analyse.py"
) else (
	python "%PROJECT_ROOT%\outil\analyse.py"
)
pause
