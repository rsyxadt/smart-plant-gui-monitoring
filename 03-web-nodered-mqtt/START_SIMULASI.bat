@echo off
title Simulasi Smart Plant: Mock ESP32 -> MQTT Bridge
echo ============================================================
echo   SIMULASI SMART PLANT (MOCK ESP32 -> MQTT BRIDGE)
echo   Untuk demo tanpa hardware fisik ESP32.
echo ============================================================
echo.

:: Jalankan Mock ESP32 di jendela terpisah
start "Mock ESP32 TCP Server (Port 5000)" python mock_esp32.py

:: Tunggu 2 detik
timeout /t 2 /nobreak >nul

:: Jalankan Bridge menuju Mock Server di localhost
echo [INFO] Menjalankan bridge TCP (127.0.0.1:5000) -> MQTT (127.0.0.1:1883)...
python esp32_mqtt_bridge.py --host 127.0.0.1 --port 5000
pause
