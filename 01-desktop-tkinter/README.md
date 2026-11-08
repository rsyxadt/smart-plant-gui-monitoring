# 🖥️ Model 1: Desktop GUI Monitoring (Python Tkinter)

Implementasi Graphical User Interface (GUI) desktop berbasis **Python Tkinter** dan **Matplotlib** untuk sistem pemantauan nirkabel *Smart Plant* mikrokontroler ESP32.

---

## ✨ Fitur Utama
1. **Komunikasi Nirkabel TCP Langsung**: Terhubung ke ESP32 SoftAP (`192.168.4.1:5000`) menggunakan Protocol 4 Newline-Delimited JSON.
2. **Mode Simulasi Mandiri (Offline Demo)**: Mensimulasikan dinamika sensor sintetis secara offline tanpa ketergantungan perangkat keras.
3. **Kartu Sensor Real-Time (KPI Cards)**: Tampilan nilai terkini Suhu (°C), Kelembapan Udara (%RH), Kelembapan Tanah (%), dan Jarak Objek (cm) dengan indikasi visual warna.
4. **Grafik Multi-Kurva Real-Time**: Tiga subplot Matplotlib (*scrolling window* 50 sampel) yang digambar mulus tanpa membekukan antarmuka (*thread-safe queue*).
5. **Sistem Ambang Batas Alarm Konfigurabel**: Ambang batas numerik yang dapat disesuaikan sewaktu-waktu disertai peringatan suara (*audio beep*).
6. **Data Logging Otomatis**: Menyimpan seluruh rekaman telemetri 39 kolom ke berkas `.csv` (berstandar Excel) di folder `logs/`.
7. **Generator Tabel Slide 6**: Dialog modal khusus untuk merekapitulasi parameter pengujian (interval, baris diterima, baris gagal parsing, respons UI) dan menyalinnya ke clipboard.

---

## 🚀 Cara Menjalankan

### Cara 1: Menggunakan Launcher Batch (1-Klik)
Cukup klik ganda berkas:
```cmd
RUN_GUI.bat
```

### Cara 2: Menjalankan via Command Prompt / Terminal
```bash
python gui_monitor.py
```

---

## 🧪 Pengujian Mandiri (Unit Testing)
Untuk memverifikasi parser JSON Protocol 4, perhitungan latensi UI, dan integritas logging secara headless:
```bash
python test_gui_engine.py
```
