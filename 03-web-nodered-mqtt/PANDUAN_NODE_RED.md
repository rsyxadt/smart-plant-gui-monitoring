# Panduan Penggunaan GUI HTML (Node-RED + MQTT + MQTTX) — Paket 3
**Workshop Mikrokontroler Lanjut & Teknik Antarmuka (WMLTA)**  
**D4 Teknik Elektronika — Politeknik Elektronika Negeri Surabaya (PENS)**  
**Penyusun:** Rassya Aditia (2124600097), Enzilana Afwa (2124600092), Adrian Indra Pratama (2124600110)  
**Dosen Pengampu:** Dr. Ir. Hary Oktavianto, S.T., M.Eng.

---

## 1. Arsitektur Sistem Publish & Subscribe

Sistem ini mengimplementasikan arsitektur IoT modern berbasis broker pesan **MQTT (Message Queuing Telemetry Transport)** yang dipadukan dengan **Node-RED Dashboard HTML**:

```
[ ESP32 Fisik / Mock Server ]
     (TCP Stream Protocol 4)
              │
              ▼
   [ esp32_mqtt_bridge.py ]  ──▶ Mencatat CSV log di folder logs/
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

## 2. Cara Menjalankan untuk Demonstrasi

### Langkah 1: Jalankan Node-RED Dashboard
Cukup klik ganda file:
```cmd
RUN_NODERED.bat
```
- Skrip ini otomatis mengecek service Mosquitto MQTT.
- Membuka halaman **Dashboard HTML** di browser: `http://localhost:1880/ui/`
- Membuka aplikasi desktop **MQTTX** secara otomatis.

---

### Langkah 2A: Demonstrasi Mode Simulasi (Tanpa Hardware ESP32)
Jika sedang presentasi di kelas tanpa menyalakan modul ESP32, klik ganda:
```cmd
START_SIMULASI.bat
```
- Jendela Mock ESP32 akan menyala di latar belakang pada port 5000.
- Bridge otomatis mengirimkan data sensor sintetis dinamis ke Mosquitto MQTT.
- Perhatikan jarum Gauge dan kurva Chart di browser `http://localhost:1880/ui/` langsung bergerak secara real-time!

---

### Langkah 2B: Pengujian dengan Hardware ESP32 Nyata
1. Nyalakan modul ESP32 Smart Plant (Protocol 4).
2. Hubungkan WiFi laptop ke Access Point:
   - **SSID:** `SmartPlant_Paket2`
   - **Password:** `monitoring32`
3. Klik ganda file:
   ```cmd
   START_ESP32_HARDWARE.bat
   ```
4. Data sensor asli dari AHT10, Capacitive Soil, dan HC-SR04 akan langsung mengalir ke broker MQTT dan tampil di Dashboard HTML serta MQTTX!

---

## 3. Konfigurasi Monitoring di MQTTX (Bukti Pub/Sub ke Dosen)

Untuk menunjukkan kepada dosen bahwa data benar-benar mengalir lewat mekanisme **Publish & Subscribe**:
1. Buka aplikasi **MQTTX** (sudah terinstall di laptop kamu).
2. Buat koneksi baru (*New Connection*):
   - **Name:** `Smart Plant Local`
   - **Host:** `127.0.0.1` (atau `localhost`)
   - **Port:** `1883`
   - Klik tombol **Connect** (ikon hijau di pojok kanan atas).
3. Tambahkan Subscription baru (*New Subscription*):
   - **Topic:** `smartplant/#`
   - **QoS:** `0`
   - Klik **Confirm**.
4. Anda akan melihat seluruh paket pesan sensor masuk per detik:
   - `smartplant/suhu` : contoh `29.45`
   - `smartplant/kelembapan` : contoh `63.2`
   - `smartplant/soil` : contoh `48.7`
   - `smartplant/jarak` : contoh `22.4`
   - `smartplant/rtt` : contoh `38.5`
   - `smartplant/alarm` : contoh `NORMAL` atau `ALARM: Suhu > 32C`

---

## 4. Keunggulan Teknis yang Dapat Dijelaskan ke Dosen

1. **Firmware ESP32 Tidak Diubah (Protocol 4 Asli Tetap Utuh)**:
   - ESP32 tetap menjalankan firmware Paket 2 yang andal dengan FreeRTOS multithreaded buffering.
   - Mekanisme balasan `ACK` instan dipertahankan oleh bridge sebelum proses serialisasi MQTT, sehingga kalkulasi Round-Trip Time (RTT) mikrokontroler tetap akurat.
2. **Arsitektur Standar Industri IoT (Decoupled Microservices)**:
   - Pemisahan antara *Data Gateway* (Bridge), *Message Broker* (Mosquitto), dan *Display Consumer* (Node-RED HTML Dashboard + MQTTX).
   - Jika browser ditutup atau laptop direstart, data logger CSV tetap berjalan mandiri di latar belakang tanpa kehilangan sampel.
3. **Penyimpanan Data Historis Otomatis**:
   - Seluruh baris data tersimpan rapi di direktori `logs/` dalam format `.csv` berstandar Excel (delimiter titik-koma `;`, encoding UTF-8-SIG).
