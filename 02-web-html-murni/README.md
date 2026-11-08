# 🌐 Model 2: Standalone Web Dashboard (HTML5 Murni & Canvas)

Implementasi antarmuka web modern mandiri (*standalone web dashboard*) yang dibangun menggunakan **HTML5 semantik, CSS3 grid/flexbox, dan JavaScript murni**. Sepenuhnya beroperasi secara **100% Offline-First** tanpa bergantung pada pustaka eksternal (CDN) atau koneksi internet.

---

## ✨ Fitur Utama
1. **100% Offline-First**: Tidak memuat CDN eksternal (Chart.js, Tailwind, atau webfonts), sehingga aman dan stabil digunakan saat laptop terhubung ke WiFi SoftAP ESP32.
2. **Visualisasi Canvas Real-Time Hi-DPI**: Tiga kanvas grafik bergulir (*rolling window* 50 data point) yang dirender menggunakan HTML5 2D Context terakselerasi perangkat keras dengan latency pembaruan ultra-rendah (1–3 ms).
3. **Peringatan Audio Web Audio API**: Menghasilkan nada peringatan suara (*sine wave beep* frekuensi 1200 Hz) secara lokal dari browser saat ambang batas bahaya terlampaui.
4. **Ekspor CSV Langsung**: Menyimpan rekaman data telemetri ke format `.csv` berstandar Excel (delimiter titik-koma `;`, encoding UTF-8-SIG) langsung melalui browser.
5. **Jembatan Lokal HTTP/SSE (server.py)**: Server lokal berbasis pustaka standar Python yang menjembatani browser dengan soket TCP ESP32 (`192.168.4.1:5000`) dan membalas `ACK` instan untuk menjaga akurasi RTT mikrokontroler.

---

## 🚀 Cara Menjalankan

### Mode A: Demo Simulasi Cepat (Tanpa Server / Double-Click)
Cukup klik ganda berkas:
```
index.html
```
Halaman dashboard akan terbuka langsung di browser (Chrome / Edge / Firefox). Klik tombol hijau **`▶ HUBUNGKAN & STREAM`** untuk melihat data sintetis dinamis bergerak.

### Mode B: Menghubungkan ke ESP32 Fisik (WiFi TCP)
1. Sambungkan WiFi laptop ke Access Point ESP32:
   - **SSID:** `SmartPlant_Paket2`
   - **Password:** `monitoring32`
2. Klik ganda berkas:
   ```cmd
   RUN_HTML.bat
   ```
3. Browser akan membuka alamat `http://localhost:8080/`. Pilih Sumber Data: **ESP32 WiFi TCP (192.168.4.1)** lalu klik **`▶ HUBUNGKAN & STREAM`**.
