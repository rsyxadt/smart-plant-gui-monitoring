@echo off
title Smart Plant Web Dashboard - HTML Murni (Paket 3)
echo ============================================================
echo   SMART PLANT WEB DASHBOARD - HTML MURNI (PAKET 3 - PENS)
echo   Workshop Mikrokontroler Lanjut & Teknik Antarmuka
echo   Rassya Aditia (2124600097) ^| 3 D4 Teknik Elektronika
echo ============================================================
echo.
echo Menjalankan Web Server di http://localhost:8080 ...
echo.

:: Buka browser secara otomatis
start "" http://localhost:8080/

:: Jalankan server Python
python server.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [INFO] Python tidak ditemukan atau server ditutup.
    echo Anda tetap dapat membuka index.html secara langsung (double-click) untuk Mode Simulasi.
    pause
)
