# 🌱 Smart Plant Telemetry & GUI Monitoring Dashboard

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python: 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![HTML5: Offline](https://img.shields.io/badge/HTML5-Canvas%20Hi--DPI-orange.svg)](https://developer.mozilla.org/en-US/docs/Web/API/Canvas_API)
[![MQTT: Mosquitto](https://img.shields.io/badge/MQTT-Mosquitto%20v2.0-red.svg)](https://mosquitto.org/)
[![Node-RED: v5.0](https://img.shields.io/badge/Node--RED-v5.0.8-darkred.svg)](https://nodered.org/)

Repositori ini memuat implementasi komprehensif **Multi-Platform Graphical User Interface (GUI) Monitoring** untuk sistem telemetri nirkabel *Smart Plant* berbasis mikrokontroler **ESP32 (Protocol 4 Newline-Delimited JSON over TCP)**.

Proyek ini dikembangkan sebagai bagian dari praktikum **Paket 3 — GUI Monitoring** pada mata kuliah **Workshop Mikrokontroler Lanjut & Teknik Antarmuka (WMLTA)**, Program Studi Sarjana Terapan (D4) Teknik Elektronika, **Politeknik Elektronika Negeri Surabaya (PENS)**.

---

## 👥 Tim Pengembang
* **Rassya Aditia** (NRP: 2124600097) — [GitHub Profile](https://github.com/rsyxadt)
* **Enzilana Afwa** (NRP: 2124600092)
* **Adrian Indra Pratama** (NRP: 2124600110)
* **Dosen Pengampu:** Dr. Ir. Hary Oktavianto, S.T., M.Eng.

---

## 📊 Matriks Perbandingan 3 Model GUI

Repositori ini menyajikan **3 model antarmuka yang berbeda** untuk membandingkan kinerja, keandalan parsing, latensi antarmuka, serta kemudahan integrasi sistem:

| Aspek Evaluasi | Model 1: Desktop Python Tkinter | Model 2: Standalone HTML5 Canvas | Model 3: Node-RED + MQTT |
|---|---|---|---|
| **Platform Antarmuka** | Python 3 (Desktop Tkinter) | HTML5, CSS3, JS Murni (Browser) | Web Browser (Dashboard v1) |
| **Arsitektur Komunikasi** | Klien Soket TCP Langsung | HTTP / SSE via Jembatan Lokal | TCP Gateway ➔ MQTT Broker (Pub/Sub) |
| **Visualisasi Grafik** | Matplotlib FigureCanvasTkAgg | HTML5 2D Context Canvas (Hi-DPI) | Angular/Chart.js Node-RED |
| **Metode Peringatan Alarm** | Visual Red Highlight + Windows Beep | Animasi Pulse + Web Audio API (1200 Hz)| Banner Teks Dinamis |
| **Dependensi Eksternal** | Matplotlib (`pip install matplotlib`) | **100% Zero-Dependency (Offline-First)**| Node-RED, Mosquitto, Paho-MQTT |
| **Alat Bantu Verifikasi** | CMD Live Packet Logs | Browser DevTools / Web Storage | MQTTX Desktop Client |
| **Kemudahan Eksekusi** | Klik `RUN_GUI.bat` | Klik ganda `index.html` / `RUN_HTML.bat` | Klik `RUN_NODERED.bat` |

---

## 📁 Struktur Direktori Repositori

```text
smart-plant-gui-monitoring/
│
├── .gitignore                      # Pengecualian berkas cache, log CSV, dan env
├── .env.example                    # Template variabel konfigurasi jaringan & broker
├── LICENSE                         # Lisensi Open-Source MIT
├── README.md                       # Dokumentasi utama proyek
│
├── 01-desktop-tkinter/             # [MODEL 1] Desktop GUI Monitoring Python Tkinter
│   ├── gui_monitor.py              # Aplikasi GUI desktop utama
│   ├── test_gui_engine.py          # Unit testing validasi headless parser
│   ├── generate_test_datasets.py   # Generator dataset pengujian Uji 1, 2, 3
│   ├── RUN_GUI.bat                 # Launcher batch 1-klik
│   └── README.md                   # Panduan teknis Model 1
│
├── 02-web-html-murni/              # [MODEL 2] Standalone Web Dashboard (HTML5 Murni)
│   ├── index.html                  # Struktur semantik antarmuka web
│   ├── style.css                   # Styling modern tema gelap (100% offline)
│   ├── app.js                      # Engine grafik canvas, Web Audio, dan simulasi
│   ├── server.py                   # Server web lokal & jembatan TCP ESP32
│   ├── mock_esp32.py               # Simulator TCP Protocol 4 mandiri
│   ├── RUN_HTML.bat                # Launcher batch 1-klik server web
│   ├── START_MOCK_ESP32.bat        # Launcher simulator TCP
│   └── README.md                   # Panduan teknis Model 2
│
├── 03-web-nodered-mqtt/            # [MODEL 3] Node-RED Dashboard + MQTT Pub/Sub
│   ├── flows_smartplant.json       # Definisi flow Node-RED dashboard
│   ├── esp32_mqtt_bridge.py        # Gateway TCP ke MQTT Broker + logger CSV
│   ├── mock_esp32.py               # Simulator TCP Protocol 4 mandiri
│   ├── setup_flow.py               # Pemasang aman flow ke ~/.node-red/flows.json
│   ├── RUN_NODERED.bat             # Launcher batch 1-klik Node-RED
│   ├── START_SIMULASI.bat          # Launcher mode simulasi MQTT
│   ├── START_ESP32_HARDWARE.bat    # Launcher mode hardware fisik ESP32
│   └── README.md                   # Panduan teknis Model 3
│
└── docs/                           # Dokumentasi Akademis & Bahan Presentasi
    ├── paket 3.docx                # Laporan praktikum resmi 9 tahapan pembuatan GUI
    ├── Paket 3 - GUI Monitoring.pptx # Slide presentasi 8 halaman sesuai silabus
    └── PANDUAN_PAKET3.md           # Panduan lengkap pengujian & evaluasi Slide 6
```

---

## 📡 Protokol Komunikasi (Protocol 4 Newline-Delimited JSON)

ESP32 beroperasi sebagai WiFi Access Point (`SSID: SmartPlant_Paket2`, port `5000`) dan mentransmisikan data berformat Newline-Delimited JSON:

```json
{
  "type": "data",
  "protocol": 4,
  "boot_id": "esp32_boot_01",
  "stream_id": "str_104820",
  "seq": 15,
  "esp_ms": 12850,
  "send_start_us": 12850420,
  "packet_interval_ms": 84.95,
  "soil": {
    "sample": 120, "value": 2150.0, "second": 42.5, "status": "ok",
    "read_us": 980, "period_us": 1052, "age_ms": 2, "overwritten_since_packet": 65
  },
  "aht": {
    "sample": 15, "value": 28.65, "second": 64.8, "status": "ok",
    "read_us": 82000, "period_us": 85000, "age_ms": 4, "overwritten_since_packet": 0
  },
  "ultrasonic": {
    "sample": 18, "value": 24.2, "second": null, "status": "ok",
    "read_us": 2400, "period_us": 65000, "age_ms": 3, "overwritten_since_packet": 1
  }
}
```

Setiap GUI mengimplementasikan mekanisme balasan pengakuan penerimaan instan berupa perintah:
```text
ACK,{stream_id},{seq}\n
```
segera setelah frame diterima agar mikrokontroler dapat mengukur nilai Round-Trip Time (RTT) nirkabel secara presisi tanpa terdistorsi oleh waktu render tampilan antarmuka laptop.

---

## 📈 Rekapitulasi Hasil Pengujian (Sesuai Slide 6 PPT)

| Parameter Pengujian | Uji 1 (Interval Lambat) | Uji 2 (Interval Sedang) | Uji 3 (Interval Cepat) |
|---|:---:|:---:|:---:|
| **Konfigurasi Mode Sensor** | AHT10 Recommended (~2000 ms) | Interval Sedang (~500 ms) | AHT10 Fast (~85 ms) |
| **Interval Pembaruan Rata-rata** | **2.014,8 ms** | **501,8 ms** | **85,7 ms** |
| **Data Berhasil Diterima** | **50 baris** | **100 baris** | **250 baris** |
| **Data Gagal Parsing** | **0 baris (0,0%)** | **0 baris (0,0%)** | **0 baris (0,0%)** |
| **Respons Latensi Tampilan UI** | **8,21 ms** (Tkinter) / **1,45 ms** (Canvas) | **8,21 ms** / **1,62 ms** | **8,21 ms** / **1,85 ms** |
| **Pembaruan Grafik Real-Time** | Ya (Mulus tanpa jeda) | Ya (Lancar responsif) | Ya (Mulus real-time) |
| **Kepatuhan Ambang Alarm** | Ya (Terdeteksi saat Suhu > 32°C)| Ya (Sesuai ambang) | Ya (Deteksi instan) |
| **Pencatatan Log CSV** | Ya (Tersimpan otomatis di `logs/`)| Ya (Tersimpan otomatis) | Ya (Tersimpan otomatis) |
| **Kestabilan Jangka Panjang** | Ya (100% stabil, tanpa crash) | Ya (100% stabil) | Ya (100% stabil) |

---

## 📜 Lisensi

Proyek ini dilisensikan di bawah [Lisensi MIT](LICENSE) — bebas digunakan dan dimodifikasi untuk tujuan akademik, riset, maupun pengembangan sistem Internet of Things (IoT).
