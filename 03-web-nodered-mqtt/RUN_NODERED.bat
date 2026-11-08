@echo off
title Smart Plant Node-RED Dashboard & MQTT (Paket 3)
echo ============================================================
echo   SMART PLANT NODE-RED DASHBOARD (PAKET 3 - PENS)
echo   Workshop Mikrokontroler Lanjut & Teknik Antarmuka
echo   Rassya Aditia (2124600097) ^| 3 D4 Teknik Elektronika
echo ============================================================
echo.

:: 1. Pastikan flow Smart Plant terpasang di Node-RED
python setup_flow.py

:: 2. Pastikan service Mosquitto berjalan
sc query mosquitto | find "RUNNING" >nul
if %ERRORLEVEL% NEQ 0 (
    echo [INFO] Menyalakan service Mosquitto MQTT broker...
    net start mosquitto
) else (
    echo [OK] Broker Mosquitto MQTT aktif di port 1883.
)

:: 3. Buka Dashboard di browser
echo [INFO] Membuka Dashboard di browser: http://localhost:1880/ui/
start "" http://localhost:1880/ui/

:: 4. Opsi buka MQTTX jika ada
if exist "C:\Program Files\MQTTX\MQTTX.exe" (
    echo [INFO] Membuka MQTTX client...
    start "" "C:\Program Files\MQTTX\MQTTX.exe"
)

:: 5. Jalankan Node-RED
echo.
echo ============================================================
echo   NODE-RED SEDANG BERJALAN
echo   Tekan Ctrl+C di jendela ini untuk mematikan Node-RED.
echo ============================================================
echo.
node-red
pause
