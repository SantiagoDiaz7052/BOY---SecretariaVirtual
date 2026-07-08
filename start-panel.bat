@echo off
title BOY - Panel Secretaria

echo ========================================
echo   BOY - Secretaria Virtual
echo   Panel Administrativo
echo ========================================
echo.

cd /d "%~dp0"

echo [1/2] Iniciando servidor...
start /B uvicorn main:app --host 127.0.0.1 --port 8000 --reload > nul 2>&1

timeout /t 3 /nobreak > nul

echo [2/2] Abriendo panel en el navegador...
start http://127.0.0.1:8000/admin

echo.
echo Panel abierto en http://127.0.0.1:8000/admin
echo.
echo Para detener el servidor, presiona Ctrl+C en esta ventana
echo o cierrala.
echo.

pause > nul
