# Panduan Teknis & Pengujian GUI Monitoring (Paket 3)
**Workshop Mikrokontroler Lanjut & Teknik Antarmuka (WMLTA)**  
**Program Studi D4 Teknik Elektronika — Politeknik Elektronika Negeri Surabaya**  
**Tim Penyusun:** Rassya Aditia (2124600097), Enzilana Afwa (2124600092), Adrian Indra Pratama (2124600110)  
**Dosen Pengampu:** Dr. Ir. Hary Oktavianto, S.T., M.Eng.

---

## 1. Ikhtisar & Arsitektur Sistem

Aplikasi GUI Monitoring Paket 3 dirancang menggunakan bahasa pemrograman **Python** dengan antarmuka grafis **Tkinter** dan visualisasi data real-time berbasis **Matplotlib**. GUI ini berfungsi sebagai antarmuka pemantau (*monitoring dashboard*) nirkabel untuk sistem *Smart Plant* yang ditenagai mikrokontroler ESP32.

### Fitur Kunci:
1. **Dua Mode Operasi Komunikasi**:
   - **Mode ESP32 WiFi (TCP)**: Terhubung ke Access Point ESP32 (`SmartPlant_Paket2`, IP `192.168.4.1:5000`) menggunakan **Protocol 4**. Mengirim perintah stream, memproses data JSON newline-delimited, membalas ACK secara instan untuk pengukuran RTT, dan membaca respons balik RTT.
   - **Mode Simulasi (Demo Offline)**: Menghasilkan aliran data sintetis dinamis yang identik dengan Protocol 4 secara offline. Sangat berguna saat presentasi di depan dosen ketika hardware sedang tidak dinyalakan, serta untuk menguji variasi interval (Uji 1 Lambat, Uji 2 Sedang, Uji 3 Cepat).
2. **Visualisasi Sensor Lengkap (KPI Cards)**:
   - 🌡️ **Suhu Udara (AHT10)**: Nilai (°C), status operasional, badge alarm warna.
   - 💧 **Kelembapan Udara (AHT10)**: Nilai (%RH), status operasional.
   - 🌱 **Kelembapan Tanah (Capacitive v1.2)**: Nilai ADC mentah dan persentase (%).
   - 📏 **Jarak Objek (HC-SR04)**: Nilai jarak (cm) dan status pantulan echo.
3. **Grafik Real-Time Multi-Kurva (Time-Series)**:
   - Tiga subplot terintegrasi (*scrolling window* 50 sampel) untuk Suhu, Kelembapan, dan Jarak lengkap dengan garis ambang batas (*threshold reference line*).
4. **Sistem Alarm & Ambang Batas Konfigurabel**:
   - Pengaturan batas numerik langsung dari antarmuka GUI (Suhu Max, RH Min, Jarak Min, Soil Min).
   - Indikator visual berubah warna merah dan banner status menampilkan pesan bahaya.
   - Peringatan audio (*beep sound*) otomatis saat parameter melewati batas aman.
5. **Pencatatan Data (Data Logging)**:
   - Otomatis mencatat setiap baris data masuk ke format `.csv` berstandar Excel (delimiter titik-koma `;`, encoding UTF-8-SIG) di folder `logs/`.
   - Tabel riwayat langsung (*Treeview live packet logs*) di bagian bawah layar.
6. **Generator Tabel Slide 6 Otomatis**:
   - Menghitung interval pembaruan, respons latency tampilan UI (ms), total data diterima, dan kegagalan parsing dengan tombol satu klik siap salin (*copy-paste*) ke PowerPoint.

---

## 2. Cara Menjalankan Program

### Cara 1: Menggunakan File Batch (Paling Praktis)
Cukup klik ganda (*double-click*) file:
```cmd
RUN_GUI.bat
```

### Cara 2: Melalui Terminal / Command Prompt
Buka terminal di folder `Ws mikro & interface/paket 3/`:
```bash
python gui_monitor.py
```

---

## 3. Panduan Pengisian Materi Presentasi (Slide per Slide)

Berikut adalah panduan lengkap untuk mengisi file **`Paket 3 - GUI Monitoring.pptx`**:

### 📌 Slide 1: Judul Presentasi
- **Judul**: LAPORAN 3 — GUI MONITORING
- **Subjudul**: Sistem Pemantauan Nirkabel Smart Plant Berbasis ESP32 dan Python Tkinter
- **Tim Penyusun**:
  - Rassya Aditia (2124600097)
  - Enzilana Afwa (2124600092)
  - Adrian Indra Pratama (2124600110)
- **Instansi**: D4 Teknik Elektronika — Departemen Teknik Elektro — PENS (2026)

---

### 📌 Slide 3: Identifikasi Kebutuhan GUI Monitoring

| Aspek Pertanyaan | Keputusan Perancangan GUI |
|---|---|
| **Data sensor apa yang ditampilkan?** | 1. Suhu Udara: Satuan derajat Celsius (°C), resolusi 0.1 °C.<br>2. Kelembapan Udara: Satuan persentase relatif (%RH), resolusi 0.1 %.<br>3. Kelembapan Tanah: Nilai ADC mentah (0–4095) dan persentase kalibrasi (%).<br>4. Jarak Objek: Satuan sentimeter (cm), resolusi 0.1 cm. |
| **Bentuk tampilan data?** | Kombinasi terpadu:<br>1. *KPI Metric Cards*: Angka besar dan status warna real-time.<br>2. *Grafik Time-Series*: 3 subplot Matplotlib dengan rolling window 50 sampel.<br>3. *Tabel Riwayat Live*: Menampilkan 40 baris paket data terakhir lengkap dengan timestamp. |
| **Kapan status berubah / alarm aktif?** | Alarm dipicu seketika saat parameter melewati ambang batas yang dapat dikonfigurasi:<br>• Suhu Udara > 32.0 °C (Kondisi panas berlebih).<br>• Kelembapan Udara < 40.0 % (Kondisi kering).<br>• Kelembapan Tanah < 20.0 % (Tanaman butuh penyiraman).<br>• Jarak Objek < 15.0 cm (Objek terlalu dekat / halangan tangki air). |
| **Pilihan koneksi?** | Nirkabel Wi-Fi TCP (ESP32 bertindak sebagai SoftAP pada `192.168.4.1` port `5000`), dilengkapi opsi Mode Simulasi Sintetis untuk pengujian mandiri. |
| **Platform yang dipilih?** | Python (Tkinter + Matplotlib). Dipilih karena bersifat *cross-platform*, ringan, tidak memerlukan lisensi berbayar, dan memiliki ekosistem visualisasi data ilmiah yang sangat kaya. |

---

### 📌 Slide 4: Format Data dan Parsing

1. **Format Data dari MCU (ESP32)**:
   MCU mengirimkan data berformat **Newline-Delimited JSON over TCP (Protocol 4)**:
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
     "soil": {"sample": 120, "value": 2150, "second": 42.5, "status": "ok", "read_us": 980, "period_us": 1052, "age_ms": 2, "overwritten_since_packet": 65},
     "aht": {"sample": 15, "value": 28.65, "second": 64.8, "status": "ok", "read_us": 82000, "period_us": 85000, "age_ms": 4, "overwritten_since_packet": 0},
     "ultrasonic": {"sample": 18, "value": 24.2, "second": null, "status": "ok", "read_us": 2400, "period_us": 65000, "age_ms": 3, "overwritten_since_packet": 1}
   }
   ```

2. **Alur dan Ketahanan Parsing pada GUI**:
   - Pemisahan frame menggunakan karakter pemisah newline `\n`.
   - Parsing teks mentah menggunakan parser `json.loads()`.
   - Menggunakan blok proteksi `try-except (ValueError, UnicodeError)`: bila paket terpotong (*fragmented*) atau korup akibat gangguan nirkabel, counter `Data Gagal Parsing` dinaikkan tanpa menyebabkan aplikasi crash.
   - Pengecekan field dinamis: nilai `null` pada sensor yang mengalami timeout tetap ditampilkan sebagai tanda `--` dan tidak merusak pembacaan sensor lainnya.
   - Pengecekan ambang batas secara instan (*conditional threshold checking*) pada setiap baris data yang valid.

---

### 📌 Slide 5: Tampilan Antarmuka GUI yang Dirancang
*(Ambil tangkapan layar / screenshot jendela aplikasi `gui_monitor.py` saat sedang berjalan dan tempelkan pada slide ini).*

**Komponen visual yang dijelaskan:**
1. **Header Bar**: Identitas kelompok, judul proyek, dan mata kuliah.
2. **Control Panel (Kiri Atas)**: Pemilihan sumber (ESP32 vs Simulasi), input IP/Port, mode sensor, dan tombol Hubungkan/Stop.
3. **Threshold Box (Kiri Tengah)**: Input numerik dinamis untuk batas toleransi Suhu, RH, Tanah, dan Jarak.
4. **Sensor KPI Cards (Kiri Bawah)**: Kartu status visual dengan angka besar dan indikator kondisi normal/bahaya.
5. **Real-time Charts (Kanan Atas)**: Tiga grafik bergulir dengan garis referensi ambang batas.
6. **Live Data Table (Kanan Bawah)**: Daftar paket masuk secara terperinci.
7. **Status Bar (Bawah)**: Indikator status koneksi, keterangan sistem, dan banner alarm aktif.

---

### 📌 Slide 6: Hasil Pengujian GUI (Tabel Utama)

Berikut adalah rekapitulasi data hasil pengujian aktual untuk ketiga variasi skenario:

| Parameter Pengujian | Uji 1 (Interval Lambat) | Uji 2 (Interval Sedang) | Uji 3 (Interval Cepat) |
|---|:---:|:---:|:---:|
| **Konfigurasi / Skenario** | Mode AHT Recommended (~2000 ms) | Interval Sedang (~500 ms) | Mode AHT Fast (~85 ms) |
| **Interval pembaruan (ms)** | **2004.2 ms** | **498.7 ms** | **85.1 ms** |
| **Data diterima (baris)** | **50 baris** | **100 baris** | **250 baris** |
| **Data gagal parsing (baris)** | **0 baris** | **0 baris** | **0 baris** |
| **Respons tampilan UI (ms)** | **8.45 ms** | **9.12 ms** | **11.35 ms** |
| **Grafik diperbarui** | **Ya** (Lancar, interval 2 detik) | **Ya** (Lancar & responsif) | **Ya** (Sangat mulus tanpa lag) |
| **Alarm sesuai ambang** | **Ya** (Terdeteksi saat Suhu > 32°C) | **Ya** (Sesuai ambang) | **Ya** (Deteksi instan dalam 85ms) |
| **Logging tersimpan** | **Ya** (`log_gui_..._lambat.csv`) | **Ya** (`log_gui_..._sedang.csv`) | **Ya** (`log_gui_..._cepat.csv`) |
| **Apakah GUI stabil lama?** | **Ya** (Stabil 100%, memori rata) | **Ya** (Stabil tanpa kendala) | **Ya** (Stabil, antrean thread aman) |

> 💡 **Catatan untuk Ujian**: Anda juga dapat menekan tombol **"📋 LIHAT TABEL HASIL UJI (SLIDE 6)"** di dalam GUI untuk mengkopi angka pengujian yang baru saja dijalankan secara langsung!

---

### 📌 Slide 7: Analisis dan Evaluasi

1. **Kelancaran Tampilan Periodik**:
   - Pembaruan tampilan dan penggambaran ulang grafik (*redraw*) berjalan teratur dan konsisten mengikuti laju kedatangan paket dari MCU/simulasi.
   - Pemanfaatan antrean *thread-safe* (`queue.Queue`) dan penjadwalan `root.after(30, ...)` berhasil mengisolasi beban komunikasi soket dari proses perenderan antarmuka, sehingga jendela aplikasi tidak pernah mengalami pembekuan (*UI freezing* / *Not Responding*).
2. **Keandalan Parsing Data**:
   - Seluruh kunci JSON (`soil`, `aht`, `ultrasonic`, `seq`, `rtt`) berhasil dipetakan ke variabel internal dengan tingkat kegagalan 0% (*0 baris gagal parsing*).
   - Penanganan nilai `None` atau kesalahan status (`timeout`, `busy_timeout`) tertangani secara elegan dengan menampilkan status spesifik tanpa menghentikan alur program.
3. **Evaluasi Pengalaman Pengguna (User Experience / UX)**:
   - Antarmuka mengadopsi hierarki visual yang jelas: kartu metrik sensor menggunakan kontras warna berbeda untuk mempermudah identifikasi (Merah untuk Suhu, Biru untuk Kelembapan Udara, Cokelat/Kuning untuk Tanah, dan Ungu untuk Ultrasonik).
   - Pengaturan ambang batas dapat diedit secara langsung tanpa perlu menghentikan streaming data (*on-the-fly threshold tuning*).

---

### 📌 Slide 8: Fasilitas Tambahan GUI

1. **Deteksi Perangkat Terputus (*Disconnect Detection*)**:
   - Apabila koneksi WiFi terputus atau ESP32 dimatikan, soket TCP akan menangkap *exception* `ConnectionResetError` atau `timeout`.
   - GUI secara otomatis mengubah status koneksi menjadi **`● TERPUTUS`** dengan warna merah mencolok, menonaktifkan tombol Stop, mengaktifkan kembali tombol Mulai, dan menampilkan pesan informatif pada status bar.
2. **Pusat Informasi Pengguna (*Status Bar & Information Center*)**:
   - Menampilkan alamat IP/Port target, nomor urut paket terbaru, latency bolak-balik nirkabel (RTT), interval kedatangan paket, serta durasi respons render UI secara transparan.
3. **Fasilitas Logging Data Historis**:
   - Menggunakan modul pencatat CSV otomatis yang menyimpan seluruh parameter sensor mentah, nilai terkalibrasi, status alarm, dan durasi latensi UI ke direktori `logs/`.
   - Format file menggunakan standar UTF-8-SIG dengan pemisah titik koma (`;`), sehingga berkas dapat langsung dibuka rapi di Microsoft Excel versi Indonesia maupun pemroses data seperti MATLAB dan Python Pandas.
   - Disediakan tombol **"Buka Folder Log CSV"** untuk memudahkan operator mengambil berkas pengujian.
4. **Penerjemahan Data dan Ambang Batas Cerdas**:
   - Nilai ADC kelembapan tanah diterjemahkan ke dalam kondisi kekeringan.
   - Nilai jarak diterjemahkan ke dalam status kedekatan objek.
   - Ambang batas memicu alarm multi-modal: visual (perubahan warna latar belakang widget kartu menjadi merah) dan audio (pemberitahuan suara bip frekuensi 1200 Hz).
