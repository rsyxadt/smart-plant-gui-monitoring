# Panduan Dashboard GUI HTML Murni (Paket 3)
**Workshop Mikrokontroler Lanjut & Teknik Antarmuka (WMLTA)**  
**D4 Teknik Elektronika — Politeknik Elektronika Negeri Surabaya (PENS)**  
**Penyusun:** Rassya Aditia (2124600097), Enzilana Afwa (2124600092), Adrian Indra Pratama (2124600110)  
**Dosen Pengampu:** Dr. Ir. Hary Oktavianto, S.T., M.Eng.

---

## 1. Ikhtisar & Arsitektur Sistem

Versi ini merupakan implementasi **GUI Monitoring berbasis Web (HTML Murni)** yang berdiri sendiri (*standalone*) tanpa bergantung pada platform pihak ketiga seperti Node-RED maupun koneksi internet (100% Offline-First).

```
┌──────────────────────────────────────────────┐
│ [ ESP32 Fisik (WiFi AP) / Mock TCP Server ]  │
│       TCP Stream Protocol 4 (:5000)          │
└──────────────────────┬───────────────────────┘
                       │ TCP Socket
                       ▼
┌──────────────────────────────────────────────┐
│ [ server.py (Python Standard Library) ]       │
│  - HTTP Web Server (Port 8080)               │
│  - TCP Client ke 192.168.4.1:5000            │
│  - Kirim ACK instan (menjaga akurasi RTT)    │
│  - SSE (Server-Sent Events) ke Browser       │
│  - Auto-logger CSV di folder logs/           │
└──────────────────────┬───────────────────────┘
                       │ HTTP / SSE
                       ▼
┌──────────────────────────────────────────────┐
│ [ Browser Web: index.html + style.css + app ]│
│  - 4x KPI Cards (Suhu, RH, Soil, Jarak)      │
│  - 3x Real-time Canvas Charts (Hi-DPI)       │
│  - Sistem Alarm Ambang Batas + Audio Beep    │
│  - Tabel Live Logs + Modal Rekap Slide 6     │
│  - Ekspor CSV Langsung dari Browser          │
│  - Mode Simulasi Internal Mandiri            │
└──────────────────────────────────────────────┘
```

---

## 2. Cara Menjalankan

### Cara 1: Mode Simulasi Tanpa Server (Paling Cepat / Double-Click)
Cukup klik ganda berkas:
```
index.html
```
- Terbuka langsung di Google Chrome / Microsoft Edge.
- Sumber Data sudah otomatis terpilih **Mode Simulasi (Demo Offline)**.
- Klik tombol hijau **`▶ HUBUNGKAN & STREAM`**.
- Seluruh grafik Canvas, kartu metrik, dan tabel log akan langsung bergerak secara real-time tanpa butuh server atau internet sama sekali!

---

### Cara 2: Menggunakan `RUN_HTML.bat` (Untuk ESP32 Fisik / Mock Server)
1. Klik ganda:
   ```cmd
   RUN_HTML.bat
   ```
2. Browser akan otomatis terbuka ke alamat: `http://localhost:8080/`.
3. **Jika menggunakan hardware ESP32 fisik:**
   - Hubungkan WiFi laptop ke:  
     SSID: `SmartPlant_Paket2` | Password: `monitoring32`
   - Pada GUI, pilih Sumber Data: **ESP32 WiFi TCP (192.168.4.1)**.
   - Klik **`▶ HUBUNGKAN & STREAM`**.
4. **Jika ingin menguji TCP dengan Mock Server:**
   - Jalankan `START_MOCK_ESP32.bat` di jendela terpisah.
   - Pada GUI, ubah IP ESP32 menjadi `127.0.0.1`.
   - Klik **`▶ HUBUNGKAN & STREAM`**.

---

## 3. Fitur Utama yang Disediakan

1. **4 Kartu Status Sensor Real-time**:
   - 🌡️ **Suhu Udara (AHT10)**: Nilai (°C), status sensor, badge ambang batas.
   - 💧 **Kelembapan Udara (AHT10)**: Nilai (%RH), status operasional.
   - 🌱 **Kelembapan Tanah (Capacitive)**: Nilai persentase (%) dan ADC mentah.
   - 📏 **Jarak Objek (HC-SR04)**: Nilai jarak (cm) dan pantulan echo.
   - Kartu otomatis berubah warna menjadi merah berkedip (*alarm-state*) saat parameter melewati batas aman.
2. **3 Grafik Multi-Kurva Real-Time (HTML5 Canvas Hi-DPI)**:
   - Digambar murni menggunakan HTML5 2D Context tanpa library eksternal (Chart.js/D3 tidak diperlukan).
   - Dilengkapi garis referensi ambang batas putus-putus merah (*reference threshold line*).
   - Menggunakan *rolling window* 50 sampel data terbaru.
3. **Sistem Ambang Batas Alarm Konfigurabel**:
   - Batas Suhu Max, RH Min, Jarak Min, dan Soil Min dapat diedit langsung saat data sedang mengalir (*on-the-fly*).
   - Dilengkapi nada peringatan suara (*audio beep*) menggunakan **Web Audio API** frekuensi 1200 Hz.
4. **Tabel Live Packet Logs**:
   - Menampilkan 40 baris paket terakhir lengkap dengan nomor sequence, timestamp, nilai sensor, latency RTT, interval, dan status alarm.
5. **Modal Rekapitulasi Slide 6 (Siap Copy ke PPT)**:
   - Klik tombol **`📋 LIHAT TABEL HASIL UJI (SLIDE 6)`** untuk melihat parameter pengujian:
     - Interval pembaruan rata-rata (ms)
     - Total baris data diterima
     - Total baris gagal parsing (0 baris)
     - Respons rendering antarmuka UI (ms)
     - Status kestabilan grafik dan alarm
   - Klik tombol hijau **`📋 Salin Nilai ke Clipboard (Tabel)`** lalu langsung tekan `Ctrl+V` di PowerPoint!
6. **Ekspor Data CSV Berstandar Excel**:
   - Klik tombol **`💾 UNDUH LOG CSV`** untuk menyimpan seluruh rekaman data ke berkas `.csv` (berstandar Excel Indonesia: delimiter titik-koma `;`, encoding UTF-8-SIG).
   - Di sisi `server.py`, data juga otomatis tersimpan di folder `logs/`.

---

## 4. Keunggulan Teknis untuk Dijelaskan ke Dosen

1. **100% Bebas Dependensi Eksternal**:
   - Tidak memerlukan koneksi internet, tidak memuat CDN pihak ketiga (aman digunakan saat WiFi laptop terhubung ke ESP32 SoftAP).
   - Menggunakan elemen standar HTML5, CSS3 Grid/Flexbox, dan JavaScript murni.
2. **Kepatuhan Protokol & Akurasi RTT (Protocol 4)**:
   - Skrip `server.py` membalas perintah `ACK` seketika sesaat setelah baris data diterima, sehingga penghitungan RTT di mikrokontroler tidak terdistorsi oleh waktu render browser.
3. **Isolasi Beban Komputasi**:
   - Proses komunikasi soket TCP berjalan pada thread terpisah di `server.py`.
   - Di sisi browser, rendering grafik menggunakan kanvas terakselerasi perangkat keras dengan latency pembaruan rata-rata hanya 1–3 milidetik.
