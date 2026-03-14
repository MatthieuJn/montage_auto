@echo off
chcp 65001 >nul
echo.
echo  ====================================
echo   Analyse des videos pour le montage
echo  ====================================
echo.
cd /d "%~dp0"
python "../outil/analyse.py"
pause
