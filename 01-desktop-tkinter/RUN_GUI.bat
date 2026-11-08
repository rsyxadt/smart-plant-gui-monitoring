@echo off
title Smart Plant GUI Monitoring - Paket 3 (PENS)
echo ============================================================
echo   SMART PLANT MONITORING - GUI DASHBOARD PAKET 3
echo   Workshop Mikrokontroler Lanjut & Teknik Antarmuka (PENS)
echo   Rassya Aditia (2124600097) ^| 3 D4 Teknik Elektronika
echo ============================================================
echo.
echo Pastikan koneksi WiFi laptop telah terhubung ke:
echo   SSID: SmartPlant_Paket2
echo   Pass: monitoring32
echo.
echo Atau pilih [Mode Simulasi] di dalam GUI untuk demo offline.
echo.
python gui_monitor.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Terjadi kendala saat menjalankan program GUI.
    pause
)
