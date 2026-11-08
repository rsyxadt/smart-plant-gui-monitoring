@echo off
title Smart Plant ESP32 Hardware -> MQTT Bridge
echo ============================================================
echo   SMART PLANT ESP32 HARDWARE -> MQTT BRIDGE
echo   Pastikan WiFi laptop telah terhubung ke ESP32:
echo     SSID: SmartPlant_Paket2
echo     Pass: monitoring32
echo ============================================================
echo.

echo [INFO] Menghubungkan ke ESP32 (192.168.4.1:5000) dan MQTT (127.0.0.1:1883)...
python esp32_mqtt_bridge.py --host 192.168.4.1 --port 5000 --aht-mode fast
pause
