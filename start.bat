@echo off
title Absensi Reader - Multi Device
echo ================================================
echo   ABSENSI READER v3.0 - Multi-Device
echo   Biotronix (x2) + Chiyu (x2)
echo ================================================
echo.

echo [1] Memeriksa Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python tidak ditemukan!
    echo Silakan install Python 3.10+
    pause
    exit /b 1
)
echo [OK] Python ditemukan

echo.
echo [2] Memeriksa dependencies...
pip show customtkinter >nul 2>&1
if errorlevel 1 (
    echo [INFO] Menginstall dependencies...
    pip install -r requirements.txt
)
echo [OK] Dependencies siap

echo.
echo [3] Menjalankan aplikasi...
echo ================================================
echo.

python main.py

pause
