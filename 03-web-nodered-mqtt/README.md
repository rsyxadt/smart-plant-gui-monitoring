# 📡 Model 3: Node-RED Dashboard + MQTT Publish/Subscribe + MQTTX

Implementasi antarmuka berbasis arsitektur **Internet of Things (IoT) Publish & Subscribe** standar industri menggunakan **Node-RED Dashboard**, **Mosquitto MQTT Broker**, dan diverifikasi menggunakan **MQTTX Desktop Client**.

---

## 🏗️ Arsitektur Aliran Data (Pub/Sub)
```
[ ESP32 Fisik / Mock Server ]
     (TCP Stream Protocol 4)
              │
              ▼
   [ esp32_mqtt_bridge.py ]  ──▶ Otomatis simpan CSV log di logs/
              │
   (MQTT Publish ke Port 1883)
              │
              ▼
   [ Mosquitto MQTT Broker ]  (localhost:1883)
              │
      ┌───────┴────────────────────────┐
      │ (MQTT Subscribe)               │ (MQTT Subscribe)
      ▼                                ▼
[ Node-RED Dashboard HTML ]       [ MQTTX Desktop Client ]
  http://localhost:1880/ui/        Monitor visual pesan real-time
  - 4x Gauge Sensor                - smartplant/suhu
  - 3x Chart Time-series           - smartplant/kelembapan
  - Panel Status & Alarm           - smartplant/soil
                                   - smartplant/jarak
                                   - smartplant/alarm
                                   - smartplant/rtt
```

---

## 🚀 Cara Menjalankan

### Langkah 1: Jalankan Node-RED
Klik ganda berkas:
```cmd
RUN_NODERED.bat
```
- Skrip akan memverifikasi status service broker Mosquitto.
- Membuka halaman dashboard di browser: `http://localhost:1880/ui/`.
- Membuka aplikasi desktop MQTTX (jika terpasang).

### Langkah 2A: Mode Simulasi Offline (Tanpa ESP32 Fisik)
Klik ganda:
```cmd
START_SIMULASI.bat
```
Jendela Mock ESP32 TCP server dan bridge Python akan berjalan bersamaan untuk mempublikasikan data sensor sintetis ke broker MQTT secara berkala.

### Langkah 2B: Mode Hardware ESP32 Nyata
1. Hubungkan WiFi laptop ke ESP32: `SmartPlant_Paket2` (Pass: `monitoring32`).
2. Klik ganda:
   ```cmd
   START_ESP32_HARDWARE.bat
   ```

---

## 🔍 Monitoring Topik di MQTTX
1. Buka MQTTX, buat koneksi ke `127.0.0.1` port `1883`.
2. Tambahkan subscription baru ke topik `smartplant/#` (QoS 0).
3. Anda akan melihat seluruh paket telemetri per detik masuk secara transparan.
