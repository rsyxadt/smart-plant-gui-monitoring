"""
GUI Monitoring Smart Plant - Paket 3
Workshop Mikrokontroler Lanjut & Teknik Antarmuka (WMLTA)
D4 Teknik Elektronika - Politeknik Elektronika Negeri Surabaya (PENS)
Tim: Rassya Aditia (2124600097), Enzilana Afwa (2124600092), Adrian Indra Pratama (2124600110)
Dosen Pengampu: Dr. Ir. Hary Oktavianto, S.T., M.Eng.

Fitur Utama:
1. Komunikasi Nirkabel TCP (Protocol 4 ESP32 SoftAP 192.168.4.1:5000)
2. Mode Simulasi Sintetis (Demo Offline tanpa hardware) untuk Uji 1, 2, 3
3. Parsing Data JSON & Validasi Kesalahan Frame Real-time
4. Visualisasi Kartu Metrik Sensor & Indikator Status
5. Grafik Multi-Kurva Real-time (Suhu, Kelembapan Udara & Tanah, Jarak Objek)
6. Sistem Ambang Batas Alarm Konfigurabel (Visual & Audio Alert)
7. Deteksi Disconnect & Auto-recovery
8. Pencatatan Data (Data Logging) ke CSV & Tabel Riwayat Live
9. Panel Rekap Hasil Pengujian Otomatis sesuai Format Slide 6 PPT
"""

import collections
import csv
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import queue
import random
import socket
import sys
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

# Matplotlib untuk visualisasi grafik real-time
import matplotlib
matplotlib.use('TkAgg')
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

# Audio alert untuk Windows
try:
    import winsound
    HAS_WINSOUND = True
except ImportError:
    HAS_WINSOUND = False

# Konfigurasi Default & Konstanta
DEFAULT_HOST = "192.168.4.1"
DEFAULT_PORT = 5000
SENSORS = ('soil', 'aht', 'ultrasonic')
SENSOR_FIELDS = (
    'sample', 'value', 'second', 'status', 'completed_ms',
    'read_us', 'period_us', 'age_ms', 'overwritten_since_packet'
)
CSV_FIELDS = [
    'timestamp_local', 'received_at_utc', 'boot_id', 'stream_id', 'seq',
    'esp_ms', 'send_start_us', 'packet_interval_ms', 'packet_bytes', 'ui_latency_ms',
    'alarm_active', 'alarm_reasons'
] + [f'{name}_{field}' for name in SENSORS for field in SENSOR_FIELDS]

BASE_DIR = Path(__file__).resolve().parent
LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)


def format_num(val, decimals=2, fallback="--"):
    """Format angka numerik dengan fallback jika None."""
    if val is None or (isinstance(val, float) and (math.isnan(val) or math.isinf(val))):
        return fallback
    try:
        return f"{float(val):.{decimals}f}"
    except (ValueError, TypeError):
        return fallback


def get_utc_timestamp():
    return datetime.now(timezone.utc).isoformat(timespec='milliseconds')


# ==============================================================================
# ENGINE SIMULASI DATA PROTOKOL 4 (OFFLINE DEMO)
# ==============================================================================
class SimulationEngine(threading.Thread):
    """
    Menghasilkan aliran data JSON Protocol 4 sintetis yang realistis.
    Memungkinkan pengujian GUI dan pengisian tabel Slide 6 (Uji 1, 2, 3)
    tanpa harus terhubung ke ESP32 fisik.
    """
    def __init__(self, out_queue, interval_ms=85, target_packets=0, aht_mode="fast"):
        super().__init__(daemon=True)
        self.out_queue = out_queue
        self.interval_ms = interval_ms
        self.target_packets = target_packets
        self.aht_mode = aht_mode
        self.stop_event = threading.Event()
        self.boot_id = f"sim_boot_{int(time.time())}"
        self.stream_id = f"sim_str_{int(time.time() * 1000) % 1000000}"

    def run(self):
        # 1. Kirim hello frame
        hello = {"type": "hello", "protocol": 4, "boot_id": self.boot_id}
        self.out_queue.put(('msg', hello, len(json.dumps(hello))))

        # 2. Kirim running status
        time.sleep(0.05)
        status = {
            "type": "status", "protocol": 4, "boot_id": self.boot_id,
            "stream_id": self.stream_id, "state": "running", "aht_mode": self.aht_mode
        }
        self.out_queue.put(('msg', status, len(json.dumps(status))))

        seq = 1
        start_time = time.monotonic()
        last_send_time = time.monotonic()
        soil_sample = 1
        aht_sample = 1
        dist_sample = 1

        while not self.stop_event.is_set():
            now = time.monotonic()
            elapsed = now - start_time
            actual_interval = (now - last_send_time) * 1000 if seq > 1 else None
            last_send_time = now

            # Sintesis nilai sensor yang dinamis & realistis
            # Suhu: fluktuasi 27.5 - 34.0 °C (sesekali memicu alarm jika > 32 °C)
            temp = 28.5 + 4.5 * math.sin(elapsed * 0.15) + random.uniform(-0.3, 0.3)
            # Kelembapan udara: 55 - 75 %RH
            hum = 65.0 - 10.0 * math.sin(elapsed * 0.15) + random.uniform(-0.5, 0.5)
            # Jarak ultrasonik: 12 - 45 cm (sesekali memicu alarm jika < 15 cm)
            dist = 28.0 + 16.0 * math.cos(elapsed * 0.18) + random.uniform(-0.4, 0.4)
            dist = max(5.0, dist)
            # Soil Moisture ADC: 1800 - 2800 ADC
            soil_adc = 2100 + 400 * math.sin(elapsed * 0.08) + random.uniform(-20, 20)
            soil_pct = max(0.0, min(100.0, (1.0 - (soil_adc - 1500) / 1500) * 100.0))

            soil_sample += int(random.uniform(10, 80))
            aht_sample += 1
            dist_sample += int(random.uniform(1, 3))

            data_frame = {
                "type": "data",
                "protocol": 4,
                "boot_id": self.boot_id,
                "stream_id": self.stream_id,
                "seq": seq,
                "esp_ms": int(elapsed * 1000),
                "send_start_us": int(elapsed * 1000000),
                "packet_interval_ms": actual_interval,
                "soil": {
                    "sample": soil_sample,
                    "value": round(soil_adc, 0),
                    "second": round(soil_pct, 1),
                    "status": "ok",
                    "completed_ms": int(elapsed * 1000),
                    "read_us": int(random.uniform(900, 1100)),
                    "period_us": int(1000000 / 950),
                    "age_ms": int(random.uniform(1, 5)),
                    "overwritten_since_packet": random.randint(5, 75)
                },
                "aht": {
                    "sample": aht_sample,
                    "value": round(temp, 2),
                    "second": round(hum, 1),
                    "status": "ok",
                    "completed_ms": int(elapsed * 1000),
                    "read_us": int(random.uniform(80000, 85000)),
                    "period_us": int(self.interval_ms * 1000),
                    "age_ms": int(random.uniform(2, 10)),
                    "overwritten_since_packet": 0
                },
                "ultrasonic": {
                    "sample": dist_sample,
                    "value": round(dist, 1),
                    "second": None,
                    "status": "ok",
                    "completed_ms": int(elapsed * 1000),
                    "read_us": int(random.uniform(1500, 4000)),
                    "period_us": int(1000000 / 15),
                    "age_ms": int(random.uniform(1, 8)),
                    "overwritten_since_packet": random.randint(0, 2)
                }
            }

            raw_bytes = len(json.dumps(data_frame)) + 1
            self.out_queue.put(('msg', data_frame, raw_bytes))

            # RTT sintetis (30 - 55 ms di Uji Cepat/Sedang, 120-180 ms jika ada halangan)
            rtt_val = random.uniform(32.0, 48.0) if self.interval_ms < 500 else random.uniform(40.0, 80.0)
            rtt_frame = {
                "type": "rtt",
                "stream_id": self.stream_id,
                "seq": seq,
                "rtt_ms": round(rtt_val, 2)
            }
            self.out_queue.put(('msg', rtt_frame, len(json.dumps(rtt_frame))))

            seq += 1
            if self.target_packets > 0 and seq > self.target_packets:
                break

            # Tunggu sesuai interval yang dipilih
            sleep_sec = max(0.01, (self.interval_ms / 1000.0) * random.uniform(0.95, 1.05))
            time.sleep(sleep_sec)

        # Kirim status selesai
        done_status = {
            "type": "status", "protocol": 4, "boot_id": self.boot_id,
            "stream_id": self.stream_id, "state": "done",
            "sent": seq - 1, "measurement_ms": int((time.monotonic() - start_time) * 1000)
        }
        self.out_queue.put(('msg', done_status, len(json.dumps(done_status))))

    def stop(self):
        self.stop_event.set()


# ==============================================================================
# ENGINE KOMUNIKASI TCP ESP32 AKTIF (WIFI PROTOCOL 4)
# ==============================================================================
class TcpReceiverThread(threading.Thread):
    """
    Menangani soket TCP client ke ESP32 Access Point (192.168.4.1:5000).
    Mendukung handshaking hello, perintah STREAM, penerimaan frame data JSON,
    pengiriman ACK, penerimaan RTT, dan penutupan bersih dengan STOP.
    """
    def __init__(self, host, port, out_queue, aht_mode="fast", packets=0):
        super().__init__(daemon=True)
        self.host = host
        self.port = port
        self.out_queue = out_queue
        self.aht_mode = aht_mode
        self.packets = packets
        self.stop_event = threading.Event()
        self.sock = None
        self.stream_id = None
        self.boot_id = None

    def run(self):
        buffer = b""
        try:
            self.out_queue.put(('log_event', f"Menghubungkan ke ESP32 ({self.host}:{self.port})..."))
            self.sock = socket.create_connection((self.host, self.port), timeout=6.0)
            self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            self.sock.settimeout(0.2)
            self.out_queue.put(('status_change', 'connected', f"Terhubung ke {self.host}:{self.port}"))

            while not self.stop_event.is_set():
                try:
                    chunk = self.sock.recv(4096)
                except socket.timeout:
                    continue
                except (ConnectionResetError, ConnectionAbortedError, OSError) as e:
                    self.out_queue.put(('status_change', 'disconnected', f"Koneksi terputus: {e}"))
                    break

                if not chunk:
                    self.out_queue.put(('status_change', 'disconnected', "Koneksi ditutup oleh ESP32."))
                    break

                buffer += chunk
                if len(buffer) > 131072:
                    self.out_queue.put(('error', "Ukuran frame melebihi batas buffer (128KB)"))
                    break

                while b'\n' in buffer:
                    line, buffer = buffer.split(b'\n', 1)
                    raw_len = len(line) + 1
                    try:
                        message = json.loads(line.decode('utf-8', errors='replace'))
                        if not isinstance(message, dict):
                            self.out_queue.put(('invalid_frame', line, raw_len))
                            continue
                    except (ValueError, UnicodeError):
                        self.out_queue.put(('invalid_frame', line, raw_len))
                        continue

                    msg_type = message.get('type')
                    if msg_type == 'hello':
                        self.boot_id = message.get('boot_id')
                        cmd = f"STREAM,{self.aht_mode},{self.packets}\n".encode('ascii')
                        self.sock.sendall(cmd)
                        self.out_queue.put(('log_event', f"Handshake HELLO diterima -> STREAM,{self.aht_mode},{self.packets} dikirim"))
                        self.out_queue.put(('msg', message, raw_len))

                    elif msg_type == 'status':
                        if message.get('state') == 'running':
                            self.stream_id = message.get('stream_id')
                            self.out_queue.put(('log_event', f"ESP32 Stream Aktif: {self.stream_id}"))
                        self.out_queue.put(('msg', message, raw_len))
                        if message.get('state') == 'done':
                            self.out_queue.put(('log_event', "ESP32 melaporkan target paket selesai (state: done)."))

                    elif msg_type == 'data':
                        # Balas ACK sesegera mungkin agar kalkulasi RTT di ESP32 tidak ter-inflasi
                        cur_stream = self.stream_id or message.get('stream_id', '')
                        seq_num = message.get('seq', 0)
                        try:
                            ack_payload = f"ACK,{cur_stream},{seq_num}\n".encode('ascii')
                            self.sock.sendall(ack_payload)
                        except Exception as ack_err:
                            self.out_queue.put(('log_event', f"Peringatan ACK gagal: {ack_err}"))

                        self.out_queue.put(('msg', message, raw_len))

                    elif msg_type == 'rtt':
                        self.out_queue.put(('msg', message, raw_len))

                    elif msg_type == 'error':
                        self.out_queue.put(('error', f"ESP32 Error: {message.get('message')}"))
                        self.out_queue.put(('msg', message, raw_len))

        except socket.timeout:
            self.out_queue.put(('status_change', 'disconnected', "Waktu koneksi habis (Timeout menghubungkan ke ESP32)."))
        except Exception as e:
            self.out_queue.put(('status_change', 'disconnected', f"Gagal terhubung: {e}"))
        finally:
            if self.sock:
                try:
                    # Kirim STOP jika masih terhubung
                    if self.stream_id and not self.stop_event.is_set():
                        self.sock.sendall(b"STOP\n")
                except Exception:
                    pass
                try:
                    self.sock.close()
                except Exception:
                    pass
            self.out_queue.put(('status_change', 'disconnected', "Koneksi telah ditutup."))

    def stop(self):
        self.stop_event.set()
        if self.sock:
            try:
                self.sock.sendall(b"STOP\n")
            except Exception:
                pass


# ==============================================================================
# JENDELA UTAMA GUI MONITORING SMART PLANT (TKINTER + MATPLOTLIB)
# ==============================================================================
class SmartPlantGUI(tk.Tk):
    """
    Antarmuka GUI Desktop Lengkap untuk Praktikum Paket 3:
    - Menampilkan data real-time, grafik multi-parameter, indikator status,
      pemicu alarm ambang batas, data logging otomatis, serta generator tabel
      pengujian sesuai spesifikasi PPT Slide 6.
    """
    def __init__(self):
        super().__init__()
        self.title("GUI Monitoring Smart Plant — Workshop Mikrokontroler Lanjut & Teknik Antarmuka (PENS)")
        self.geometry("1280x850")
        self.minsize(1050, 720)

        # Atur Style Tampilan
        self.style = ttk.Style(self)
        try:
            self.style.theme_use('clam')
        except Exception:
            pass

        # Data queues & threads
        self.comm_queue = queue.Queue()
        self.worker_thread = None
        self.is_running = False

        # Status & Statistik Pengujian (Untuk Slide 6)
        self.test_start_time = None
        self.total_received = 0
        self.total_invalid = 0
        self.seen_seqs = set()
        self.rtt_history = collections.deque(maxlen=100)
        self.interval_history = collections.deque(maxlen=100)
        self.ui_latencies = collections.deque(maxlen=100)
        self.current_rtt = None
        self.current_interval = None
        self.alarm_triggered_count = 0
        self.last_alarm_reasons = []

        # Buffer data untuk Grafik Matplotlib (Rolling window 50 titik)
        self.plot_limit = 50
        self.plot_x = collections.deque(maxlen=self.plot_limit)
        self.plot_temp = collections.deque(maxlen=self.plot_limit)
        self.plot_hum = collections.deque(maxlen=self.plot_limit)
        self.plot_soil_pct = collections.deque(maxlen=self.plot_limit)
        self.plot_dist = collections.deque(maxlen=self.plot_limit)

        # Logging CSV
        self.csv_file = None
        self.csv_writer = None
        self.current_log_path = None

        # Bangun Komponen GUI
        self._setup_ui()

        # Jadwalkan loop polling antrean komunikasi
        self.after(30, self._process_comm_queue)

    def _setup_ui(self):
        # 1. Header Frame
        header_frame = tk.Frame(self, bg="#1E3A8A", height=70)
        header_frame.pack(fill=tk.X, side=tk.TOP)
        header_frame.pack_propagate(False)

        title_lbl = tk.Label(
            header_frame,
            text="🌱 SMART PLANT MONITORING — GUI DASHBOARD (PAKET 3)",
            font=("Segoe UI", 14, "bold"),
            fg="#FFFFFF", bg="#1E3A8A"
        )
        title_lbl.pack(anchor="w", padx=16, pady=(8, 2))

        sub_lbl = tk.Label(
            header_frame,
            text="WMLTA 3 D4 ED PENS | Rassya Aditia (2124600097) • Enzilana Afwa (2124600092) • Adrian Indra P. (2124600110)",
            font=("Segoe UI", 9),
            fg="#93C5FD", bg="#1E3A8A"
        )
        sub_lbl.pack(anchor="w", padx=16)

        # 2. Main Content Frame (Terbagi: Kiri = Kontrol & Metrik, Kanan = Grafik & Tabel)
        main_paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        # Panel Kiri
        left_container = ttk.Frame(main_paned, width=380)
        main_paned.add(left_container, weight=0)

        # Panel Kanan
        right_container = ttk.Frame(main_paned)
        main_paned.add(right_container, weight=1)

        self._build_left_panel(left_container)
        self._build_right_panel(right_container)

        # 3. Status Bar di Bagian Bawah
        self.status_bar = tk.Frame(self, bg="#0F172A", height=32)
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM)
        self.status_bar.pack_propagate(False)

        self.conn_pill = tk.Label(
            self.status_bar, text="● DISCONNECTED",
            font=("Segoe UI", 9, "bold"), fg="#EF4444", bg="#0F172A", padx=8
        )
        self.conn_pill.pack(side=tk.LEFT, padx=8)

        self.status_text = tk.Label(
            self.status_bar, text="Siap menghubungkan ke ESP32 atau jalankan Mode Simulasi.",
            font=("Segoe UI", 9), fg="#94A3B8", bg="#0F172A"
        )
        self.status_text.pack(side=tk.LEFT, padx=6)

        self.alarm_banner = tk.Label(
            self.status_bar, text="SISTEM NORMAL",
            font=("Segoe UI", 9, "bold"), fg="#10B981", bg="#0F172A", padx=12
        )
        self.alarm_banner.pack(side=tk.RIGHT, padx=12)

    def _build_left_panel(self, parent):
        canvas = tk.Canvas(parent, borderwidth=0, highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # --- A. Konfigurasi Komunikasi ---
        cfg_box = ttk.LabelFrame(scrollable_frame, text=" ⚙️ Konfigurasi Komunikasi ", padding=10)
        cfg_box.pack(fill=tk.X, padx=6, pady=4)

        # Pilihan Mode
        ttk.Label(cfg_box, text="Sumber Data:").grid(row=0, column=0, sticky="w", pady=2)
        self.source_mode_var = tk.StringVar(value="sim")
        mode_cb = ttk.Combobox(
            cfg_box, textvariable=self.source_mode_var, state="readonly",
            values=["Mode Simulasi (Demo Offline)", "ESP32 WiFi TCP (192.168.4.1)"],
            width=26
        )
        mode_cb.current(0)
        mode_cb.grid(row=0, column=1, sticky="ew", pady=2)
        mode_cb.bind("<<ComboboxSelected>>", self._on_source_mode_changed)

        # Host & Port
        ttk.Label(cfg_box, text="IP / Host:").grid(row=1, column=0, sticky="w", pady=2)
        self.host_var = tk.StringVar(value=DEFAULT_HOST)
        self.host_entry = ttk.Entry(cfg_box, textvariable=self.host_var, width=16)
        self.host_entry.grid(row=1, column=1, sticky="w", pady=2)

        ttk.Label(cfg_box, text="Port TCP:").grid(row=2, column=0, sticky="w", pady=2)
        self.port_var = tk.StringVar(value=str(DEFAULT_PORT))
        self.port_entry = ttk.Entry(cfg_box, textvariable=self.port_var, width=8)
        self.port_entry.grid(row=2, column=1, sticky="w", pady=2)

        # Mode AHT10 & Target Paket
        ttk.Label(cfg_box, text="Mode AHT10:").grid(row=3, column=0, sticky="w", pady=2)
        self.aht_mode_var = tk.StringVar(value="fast")
        self.aht_cb = ttk.Combobox(
            cfg_box, textvariable=self.aht_mode_var, state="readonly",
            values=["fast (Konversi Cepat ~85ms)", "recommended (Stabil ~2000ms)"],
            width=26
        )
        self.aht_cb.current(0)
        self.aht_cb.grid(row=3, column=1, sticky="ew", pady=2)

        ttk.Label(cfg_box, text="Target Paket:").grid(row=4, column=0, sticky="w", pady=2)
        self.packets_var = tk.StringVar(value="0")
        self.packets_cb = ttk.Combobox(
            cfg_box, textvariable=self.packets_var,
            values=["0 (Kontinu / Terus menerus)", "20 (Standar Praktikum)", "50", "100"],
            width=26
        )
        self.packets_cb.current(0)
        self.packets_cb.grid(row=4, column=1, sticky="ew", pady=2)

        # Interval Simulasi (Hanya aktif jika mode simulasi)
        self.sim_lbl = ttk.Label(cfg_box, text="Interval Uji:")
        self.sim_lbl.grid(row=5, column=0, sticky="w", pady=2)
        self.sim_interval_var = tk.StringVar(value="85")
        self.sim_interval_cb = ttk.Combobox(
            cfg_box, textvariable=self.sim_interval_var, state="readonly",
            values=["85 ms (Uji 3: Cepat)", "500 ms (Uji 2: Sedang)", "2000 ms (Uji 1: Lambat)"],
            width=26
        )
        self.sim_interval_cb.current(0)
        self.sim_interval_cb.grid(row=5, column=1, sticky="ew", pady=2)

        # Tombol Start / Stop
        btn_frame = ttk.Frame(cfg_box)
        btn_frame.grid(row=6, column=0, columnspan=2, pady=(8, 2), sticky="ew")

        self.btn_start = tk.Button(
            btn_frame, text="▶ HUBUNGKAN & STREAM", font=("Segoe UI", 9, "bold"),
            bg="#16A34A", fg="#FFFFFF", activebackground="#15803D", activeforeground="#FFFFFF",
            relief="raised", cursor="hand2", command=self.start_stream
        )
        self.btn_start.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4))

        self.btn_stop = tk.Button(
            btn_frame, text="⏹ STOP", font=("Segoe UI", 9, "bold"),
            bg="#DC2626", fg="#FFFFFF", activebackground="#B91C1C", activeforeground="#FFFFFF",
            state=tk.DISABLED, relief="raised", cursor="hand2", command=self.stop_stream
        )
        self.btn_stop.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(4, 0))

        # --- B. Ambang Batas Alarm (Configurable Thresholds) ---
        alarm_box = ttk.LabelFrame(scrollable_frame, text=" 🔔 Konfigurasi Ambang Alarm ", padding=10)
        alarm_box.pack(fill=tk.X, padx=6, pady=4)

        ttk.Label(alarm_box, text="Suhu Max (°C):").grid(row=0, column=0, sticky="w", pady=2)
        self.thresh_temp_var = tk.DoubleVar(value=32.0)
        ttk.Entry(alarm_box, textvariable=self.thresh_temp_var, width=8).grid(row=0, column=1, sticky="e", pady=2)

        ttk.Label(alarm_box, text="Kelembapan Min (%RH):").grid(row=1, column=0, sticky="w", pady=2)
        self.thresh_hum_var = tk.DoubleVar(value=40.0)
        ttk.Entry(alarm_box, textvariable=self.thresh_hum_var, width=8).grid(row=1, column=1, sticky="e", pady=2)

        ttk.Label(alarm_box, text="Jarak Min (cm):").grid(row=2, column=0, sticky="w", pady=2)
        self.thresh_dist_var = tk.DoubleVar(value=15.0)
        ttk.Entry(alarm_box, textvariable=self.thresh_dist_var, width=8).grid(row=2, column=1, sticky="e", pady=2)

        ttk.Label(alarm_box, text="Soil Min (%):").grid(row=3, column=0, sticky="w", pady=2)
        self.thresh_soil_var = tk.DoubleVar(value=20.0)
        ttk.Entry(alarm_box, textvariable=self.thresh_soil_var, width=8).grid(row=3, column=1, sticky="e", pady=2)

        self.audio_alarm_var = tk.BooleanVar(value=True)
        chk_audio = ttk.Checkbutton(alarm_box, text="Aktifkan Audio Beep saat Alarm", variable=self.audio_alarm_var)
        chk_audio.grid(row=4, column=0, columnspan=2, sticky="w", pady=(4, 2))

        # --- C. Kartu Tampilan Sensor Real-Time (KPI Cards) ---
        kpi_box = ttk.LabelFrame(scrollable_frame, text=" 📊 Nilai Sensor Real-Time ", padding=8)
        kpi_box.pack(fill=tk.X, padx=6, pady=4)

        # Kartu Suhu
        self.card_temp = tk.Frame(kpi_box, bg="#F0FDF4", highlightbackground="#86EFAC", highlightthickness=1)
        self.card_temp.pack(fill=tk.X, pady=3, padx=2)
        tk.Label(self.card_temp, text="🌡️ SUHU UDARA (AHT10)", font=("Segoe UI", 8, "bold"), fg="#166534", bg="#F0FDF4").pack(anchor="w", padx=6, pady=(3, 0))
        self.lbl_temp_val = tk.Label(self.card_temp, text="-- °C", font=("Segoe UI", 18, "bold"), fg="#15803D", bg="#F0FDF4")
        self.lbl_temp_val.pack(anchor="w", padx=8)
        self.lbl_temp_stat = tk.Label(self.card_temp, text="Status: idle | Ambang: < 32.0°C", font=("Segoe UI", 7), fg="#4B5563", bg="#F0FDF4")
        self.lbl_temp_stat.pack(anchor="w", padx=8, pady=(0, 4))

        # Kartu Kelembapan Udara
        self.card_hum = tk.Frame(kpi_box, bg="#EFF6FF", highlightbackground="#93C5FD", highlightthickness=1)
        self.card_hum.pack(fill=tk.X, pady=3, padx=2)
        tk.Label(self.card_hum, text="💧 KELEMBAPAN UDARA (AHT10)", font=("Segoe UI", 8, "bold"), fg="#1E40AF", bg="#EFF6FF").pack(anchor="w", padx=6, pady=(3, 0))
        self.lbl_hum_val = tk.Label(self.card_hum, text="-- %RH", font=("Segoe UI", 18, "bold"), fg="#1D4ED8", bg="#EFF6FF")
        self.lbl_hum_val.pack(anchor="w", padx=8)
        self.lbl_hum_stat = tk.Label(self.card_hum, text="Status: idle | Ambang: > 40.0%", font=("Segoe UI", 7), fg="#4B5563", bg="#EFF6FF")
        self.lbl_hum_stat.pack(anchor="w", padx=8, pady=(0, 4))

        # Kartu Kelembapan Tanah
        self.card_soil = tk.Frame(kpi_box, bg="#FFFBEB", highlightbackground="#FDE68A", highlightthickness=1)
        self.card_soil.pack(fill=tk.X, pady=3, padx=2)
        tk.Label(self.card_soil, text="🌱 KELEMBAPAN TANAH (Capacitive)", font=("Segoe UI", 8, "bold"), fg="#92400E", bg="#FFFBEB").pack(anchor="w", padx=6, pady=(3, 0))
        self.lbl_soil_val = tk.Label(self.card_soil, text="-- %", font=("Segoe UI", 18, "bold"), fg="#B45309", bg="#FFFBEB")
        self.lbl_soil_val.pack(anchor="w", padx=8)
        self.lbl_soil_stat = tk.Label(self.card_soil, text="ADC: -- | Status: idle", font=("Segoe UI", 7), fg="#4B5563", bg="#FFFBEB")
        self.lbl_soil_stat.pack(anchor="w", padx=8, pady=(0, 4))

        # Kartu Jarak Ultrasonik
        self.card_dist = tk.Frame(kpi_box, bg="#FAF5FF", highlightbackground="#E9D5FF", highlightthickness=1)
        self.card_dist.pack(fill=tk.X, pady=3, padx=2)
        tk.Label(self.card_dist, text="📏 JARAK OBJEK (HC-SR04)", font=("Segoe UI", 8, "bold"), fg="#6B21A8", bg="#FAF5FF").pack(anchor="w", padx=6, pady=(3, 0))
        self.lbl_dist_val = tk.Label(self.card_dist, text="-- cm", font=("Segoe UI", 18, "bold"), fg="#7E22CE", bg="#FAF5FF")
        self.lbl_dist_val.pack(anchor="w", padx=8)
        self.lbl_dist_stat = tk.Label(self.card_dist, text="Status: idle | Ambang: > 15.0 cm", font=("Segoe UI", 7), fg="#4B5563", bg="#FAF5FF")
        self.lbl_dist_stat.pack(anchor="w", padx=8, pady=(0, 4))

        # --- D. Metrik Kinerja Jaringan & GUI (Slide 6) ---
        net_box = ttk.LabelFrame(scrollable_frame, text=" ⚡ Metrik Kinerja & Uji ", padding=8)
        net_box.pack(fill=tk.X, padx=6, pady=4)

        grid_net = ttk.Frame(net_box)
        grid_net.pack(fill=tk.X)

        ttk.Label(grid_net, text="Data Diterima:").grid(row=0, column=0, sticky="w")
        self.lbl_metric_rec = ttk.Label(grid_net, text="0 baris", font=("Segoe UI", 9, "bold"))
        self.lbl_metric_rec.grid(row=0, column=1, sticky="e")

        ttk.Label(grid_net, text="Gagal Parsing:").grid(row=1, column=0, sticky="w")
        self.lbl_metric_fail = ttk.Label(grid_net, text="0 baris", font=("Segoe UI", 9, "bold"), foreground="#10B981")
        self.lbl_metric_fail.grid(row=1, column=1, sticky="e")

        ttk.Label(grid_net, text="Interval Update:").grid(row=2, column=0, sticky="w")
        self.lbl_metric_intv = ttk.Label(grid_net, text="-- ms", font=("Segoe UI", 9, "bold"))
        self.lbl_metric_intv.grid(row=2, column=1, sticky="e")

        ttk.Label(grid_net, text="RTT Rata-rata:").grid(row=3, column=0, sticky="w")
        self.lbl_metric_rtt = ttk.Label(grid_net, text="-- ms", font=("Segoe UI", 9, "bold"))
        self.lbl_metric_rtt.grid(row=3, column=1, sticky="e")

        ttk.Label(grid_net, text="Respons UI:").grid(row=4, column=0, sticky="w")
        self.lbl_metric_ui = ttk.Label(grid_net, text="-- ms", font=("Segoe UI", 9, "bold"))
        self.lbl_metric_ui.grid(row=4, column=1, sticky="e")

        # Tombol Rekap Slide 6 & Aksi Cepat
        actions_frame = ttk.Frame(scrollable_frame)
        actions_frame.pack(fill=tk.X, padx=6, pady=6)

        btn_rekap = tk.Button(
            actions_frame, text="📋 LIHAT TABEL HASIL UJI (SLIDE 6)", font=("Segoe UI", 9, "bold"),
            bg="#3B82F6", fg="#FFFFFF", activebackground="#2563EB", activeforeground="#FFFFFF",
            relief="raised", cursor="hand2", command=self.show_slide6_dialog
        )
        btn_rekap.pack(fill=tk.X, pady=2)

        btn_log_folder = ttk.Button(actions_frame, text="📁 Buka Folder Log CSV", command=self.open_logs_folder)
        btn_log_folder.pack(fill=tk.X, pady=2)

    def _build_right_panel(self, parent):
        # Gunakan paned window vertikal untuk membagi Grafik (atas) dan Tabel Riwayat (bawah)
        right_paned = ttk.PanedWindow(parent, orient=tk.VERTICAL)
        right_paned.pack(fill=tk.BOTH, expand=True)

        # 1. Grafik Matplotlib Real-Time
        plot_frame = ttk.LabelFrame(right_paned, text=" 📈 Grafik Real-Time Sensor (Rolling Time-Series) ", padding=4)
        right_paned.add(plot_frame, weight=3)

        self.fig = Figure(figsize=(7, 4.2), dpi=95, facecolor="#F8FAFC")
        self.fig.subplots_adjust(left=0.08, right=0.96, top=0.92, bottom=0.12, hspace=0.35)

        # Subplot 1: Suhu Udara (°C)
        self.ax1 = self.fig.add_subplot(3, 1, 1)
        self.ax1.set_facecolor("#FFFFFF")
        self.ax1.set_title("Suhu Lingkungan (°C) vs Ambang Batas", fontsize=9, fontweight='bold', pad=3)
        self.ax1.grid(True, linestyle="--", alpha=0.6)
        self.line_temp, = self.ax1.plot([], [], color="#DC2626", linewidth=1.8, label="Suhu (°C)")
        self.line_temp_thresh = self.ax1.axhline(y=32.0, color="#B91C1C", linestyle=":", linewidth=1.2, label="Ambang Max")
        self.ax1.legend(loc="upper left", fontsize=7)
        self.ax1.tick_params(labelsize=7)

        # Subplot 2: Kelembapan Udara (%RH) & Tanah (%)
        self.ax2 = self.fig.add_subplot(3, 1, 2)
        self.ax2.set_facecolor("#FFFFFF")
        self.ax2.set_title("Kelembapan Udara (%RH) & Tanah (%)", fontsize=9, fontweight='bold', pad=3)
        self.ax2.grid(True, linestyle="--", alpha=0.6)
        self.line_hum, = self.ax2.plot([], [], color="#2563EB", linewidth=1.8, label="RH Udara (%)")
        self.line_soil, = self.ax2.plot([], [], color="#D97706", linewidth=1.8, label="Soil Moisture (%)")
        self.ax2.legend(loc="upper left", fontsize=7)
        self.ax2.tick_params(labelsize=7)

        # Subplot 3: Jarak Objek (cm)
        self.ax3 = self.fig.add_subplot(3, 1, 3)
        self.ax3.set_facecolor("#FFFFFF")
        self.ax3.set_title("Jarak Objek Ultrasonik (cm)", fontsize=9, fontweight='bold', pad=3)
        self.ax3.grid(True, linestyle="--", alpha=0.6)
        self.line_dist, = self.ax3.plot([], [], color="#7C3AED", linewidth=1.8, label="Jarak (cm)")
        self.line_dist_thresh = self.ax3.axhline(y=15.0, color="#6D28D9", linestyle=":", linewidth=1.2, label="Ambang Min")
        self.ax3.legend(loc="upper left", fontsize=7)
        self.ax3.tick_params(labelsize=7)
        self.ax3.set_xlabel("Nomor Urut Paket (Seq)", fontsize=8)

        self.canvas = FigureCanvasTkAgg(self.fig, master=plot_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # 2. Tabel Riwayat Data Diterima (Treeview)
        table_frame = ttk.LabelFrame(right_paned, text=" 📜 Riwayat Data Masuk (Live Packet Logs) ", padding=4)
        right_paned.add(table_frame, weight=2)

        cols = ("seq", "time", "temp", "hum", "soil_adc", "soil_pct", "dist", "rtt", "interval", "alarm")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings", height=6)
        self.tree.heading("seq", text="#Seq")
        self.tree.heading("time", text="Waktu Local")
        self.tree.heading("temp", text="Suhu (°C)")
        self.tree.heading("hum", text="RH (%)")
        self.tree.heading("soil_adc", text="Soil ADC")
        self.tree.heading("soil_pct", text="Soil (%)")
        self.tree.heading("dist", text="Jarak (cm)")
        self.tree.heading("rtt", text="RTT (ms)")
        self.tree.heading("interval", text="Interval (ms)")
        self.tree.heading("alarm", text="Status Alarm")

        self.tree.column("seq", width=55, anchor="center")
        self.tree.column("time", width=85, anchor="center")
        self.tree.column("temp", width=75, anchor="center")
        self.tree.column("hum", width=75, anchor="center")
        self.tree.column("soil_adc", width=75, anchor="center")
        self.tree.column("soil_pct", width=75, anchor="center")
        self.tree.column("dist", width=80, anchor="center")
        self.tree.column("rtt", width=70, anchor="center")
        self.tree.column("interval", width=85, anchor="center")
        self.tree.column("alarm", width=120, anchor="w")

        tree_scroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=tree_scroll.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)

    def _on_source_mode_changed(self, event=None):
        mode = self.source_mode_var.get()
        if "Simulasi" in mode:
            self.host_entry.configure(state=tk.DISABLED)
            self.port_entry.configure(state=tk.DISABLED)
            self.sim_interval_cb.configure(state="readonly")
        else:
            self.host_entry.configure(state=tk.NORMAL)
            self.port_entry.configure(state=tk.NORMAL)
            self.sim_interval_cb.configure(state=tk.DISABLED)

    def start_stream(self):
        """Memulai streaming data dari ESP32 atau Engine Simulasi."""
        if self.is_running:
            return

        # Validasi target paket
        try:
            val_p = self.packets_var.get().split()[0]
            packets = int(val_p)
            if packets < 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Format Salah", "Target paket harus berupa bilangan bulat >= 0.")
            return

        # Bersihkan riwayat pengujian
        self.test_start_time = time.monotonic()
        self.total_received = 0
        self.total_invalid = 0
        self.seen_seqs.clear()
        self.rtt_history.clear()
        self.interval_history.clear()
        self.ui_latencies.clear()
        self.alarm_triggered_count = 0
        self.current_rtt = None
        self.current_interval = None

        self.plot_x.clear()
        self.plot_temp.clear()
        self.plot_hum.clear()
        self.plot_soil_pct.clear()
        self.plot_dist.clear()

        for item in self.tree.get_children():
            self.tree.delete(item)

        # Inisialisasi File CSV Logging
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        mode_prefix = "simulasi" if "Simulasi" in self.source_mode_var.get() else "esp32"
        log_filename = f"log_gui_{mode_prefix}_{timestamp_str}.csv"
        self.current_log_path = LOGS_DIR / log_filename
        try:
            self.csv_file = self.current_log_path.open('w', newline='', encoding='utf-8-sig')
            self.csv_writer = csv.DictWriter(self.csv_file, fieldnames=CSV_FIELDS, delimiter=';')
            self.csv_writer.writeheader()
        except Exception as e:
            messagebox.showwarning("Peringatan Log", f"Gagal membuat file log CSV: {e}")
            self.csv_file = None
            self.csv_writer = None

        # Mulai Thread sesuai pilihan mode
        self.is_running = True
        self.btn_start.configure(state=tk.DISABLED)
        self.btn_stop.configure(state=tk.NORMAL)

        mode_choice = self.source_mode_var.get()
        aht_mode = self.aht_mode_var.get().split()[0]

        if "Simulasi" in mode_choice:
            # Mode Simulasi
            interval_str = self.sim_interval_var.get().split()[0]
            try:
                sim_interval = int(interval_str)
            except ValueError:
                sim_interval = 85
            self.worker_thread = SimulationEngine(
                self.comm_queue, interval_ms=sim_interval,
                target_packets=packets, aht_mode=aht_mode
            )
            self._update_conn_pill("connected", f"● SIMULASI AKTIF ({sim_interval} ms)")
            self.status_text.configure(text=f"Simulasi Protocol 4 berjalan (Interval ~{sim_interval} ms)")
            self.worker_thread.start()
        else:
            # Mode WiFi ESP32
            host = self.host_var.get().strip()
            try:
                port = int(self.port_var.get().strip())
            except ValueError:
                messagebox.showerror("Error Port", "Port harus berupa angka numerik valid.")
                self.stop_stream()
                return

            self._update_conn_pill("connecting", "● MENGHUBUNGKAN...")
            self.status_text.configure(text=f"Menghubungkan ke ESP32 TCP {host}:{port}...")
            self.worker_thread = TcpReceiverThread(
                host, port, self.comm_queue, aht_mode=aht_mode, packets=packets
            )
            self.worker_thread.start()

    def stop_stream(self):
        """Menghentikan streaming data secara aman."""
        if not self.is_running:
            return

        if self.worker_thread:
            self.worker_thread.stop()
            self.worker_thread = None

        if self.csv_file:
            try:
                self.csv_file.flush()
                self.csv_file.close()
            except Exception:
                pass
            self.csv_file = None
            self.csv_writer = None

        self.is_running = False
        self.btn_start.configure(state=tk.NORMAL)
        self.btn_stop.configure(state=tk.DISABLED)
        self._update_conn_pill("disconnected", "● TERPUTUS")
        self.status_text.configure(text="Streaming dihentikan. Data tersimpan di log CSV.")

    def _update_conn_pill(self, state, text):
        if state == "connected":
            self.conn_pill.configure(text=text, fg="#10B981")
        elif state == "connecting":
            self.conn_pill.configure(text=text, fg="#F59E0B")
        else:
            self.conn_pill.configure(text=text, fg="#EF4444")

    def _process_comm_queue(self):
        """Memproses data dari worker thread tanpa membekukan antarmuka GUI."""
        batch_limit = 25
        count = 0
        while count < batch_limit:
            try:
                item = self.comm_queue.get_nowait()
            except queue.Empty:
                break

            count += 1
            tag = item[0]

            if tag == 'msg':
                msg = item[1]
                raw_bytes = item[2]
                self._handle_message(msg, raw_bytes)
            elif tag == 'invalid_frame':
                self.total_invalid += 1
                self.lbl_metric_fail.configure(text=f"{self.total_invalid} baris", foreground="#DC2626")
            elif tag == 'status_change':
                state, desc = item[1], item[2]
                self._update_conn_pill(state, f"● {desc[:25]}")
                self.status_text.configure(text=desc)
                if state == 'disconnected' and self.is_running:
                    self.stop_stream()
            elif tag == 'log_event':
                self.status_text.configure(text=item[1])
            elif tag == 'error':
                messagebox.showerror("Koneksi Error", item[1])

        # Jadwalkan panggilan berikutnya
        self.after(30, self._process_comm_queue)

    def _handle_message(self, message, raw_bytes):
        msg_type = message.get('type')

        if msg_type == 'rtt':
            rtt_val = message.get('rtt_ms')
            if rtt_val is not None:
                self.current_rtt = float(rtt_val)
                self.rtt_history.append(self.current_rtt)
                mean_rtt = sum(self.rtt_history) / len(self.rtt_history)
                self.lbl_metric_rtt.configure(text=f"{mean_rtt:.1f} ms")

        elif msg_type == 'status':
            if message.get('state') == 'done':
                self.status_text.configure(text="ESP32 selesai mengirimkan seluruh target paket.")
                self.stop_stream()

        elif msg_type == 'data':
            t_ui_start = time.perf_counter()
            self.total_received += 1
            seq = message.get('seq', self.total_received)
            self.seen_seqs.add(seq)

            # Ekstrak data sensor
            soil = message.get('soil', {})
            aht = message.get('aht', {})
            dist = message.get('ultrasonic', {})

            temp_val = aht.get('value')
            hum_val = aht.get('second')
            soil_adc = soil.get('value')
            soil_pct = soil.get('second')
            dist_val = dist.get('value')

            interval_val = message.get('packet_interval_ms')
            if interval_val is not None and interval_val > 0:
                self.current_interval = float(interval_val)
                self.interval_history.append(self.current_interval)
                mean_intv = sum(self.interval_history) / len(self.interval_history)
                self.lbl_metric_intv.configure(text=f"{mean_intv:.1f} ms")

            # Evaluasi Logika Alarm Ambang Batas (Configurable Thresholds)
            alarm_active = False
            reasons = []

            # Ambang Suhu Max
            t_thresh = self.thresh_temp_var.get()
            if temp_val is not None and temp_val > t_thresh:
                alarm_active = True
                reasons.append(f"Suhu {temp_val:.1f}°C > {t_thresh:.1f}°C")
                self.card_temp.configure(bg="#FEE2E2", highlightbackground="#EF4444")
                self.lbl_temp_val.configure(fg="#DC2626", bg="#FEE2E2")
                self.lbl_temp_stat.configure(text=f"⚠️ ALARM: Melebihi {t_thresh:.1f}°C", fg="#DC2626", bg="#FEE2E2")
            else:
                self.card_temp.configure(bg="#F0FDF4", highlightbackground="#86EFAC")
                self.lbl_temp_val.configure(fg="#15803D", bg="#F0FDF4")
                self.lbl_temp_stat.configure(text=f"Status: {aht.get('status','ok')} | Ambang: < {t_thresh:.1f}°C", fg="#4B5563", bg="#F0FDF4")

            # Ambang Kelembapan Min
            h_thresh = self.thresh_hum_var.get()
            if hum_val is not None and hum_val < h_thresh:
                alarm_active = True
                reasons.append(f"RH {hum_val:.1f}% < {h_thresh:.1f}%")
                self.card_hum.configure(bg="#FEE2E2", highlightbackground="#EF4444")
                self.lbl_hum_val.configure(fg="#DC2626", bg="#FEE2E2")
                self.lbl_hum_stat.configure(text=f"⚠️ ALARM: Terlalu Kering (< {h_thresh:.1f}%)", fg="#DC2626", bg="#FEE2E2")
            else:
                self.card_hum.configure(bg="#EFF6FF", highlightbackground="#93C5FD")
                self.lbl_hum_val.configure(fg="#1D4ED8", bg="#EFF6FF")
                self.lbl_hum_stat.configure(text=f"Status: {aht.get('status','ok')} | Ambang: > {h_thresh:.1f}%", fg="#4B5563", bg="#EFF6FF")

            # Ambang Jarak Min
            d_thresh = self.thresh_dist_var.get()
            if dist_val is not None and dist_val < d_thresh:
                alarm_active = True
                reasons.append(f"Jarak {dist_val:.1f}cm < {d_thresh:.1f}cm")
                self.card_dist.configure(bg="#FEE2E2", highlightbackground="#EF4444")
                self.lbl_dist_val.configure(fg="#DC2626", bg="#FEE2E2")
                self.lbl_dist_stat.configure(text=f"⚠️ ALARM: Objek Terlalu Dekat (< {d_thresh:.1f}cm)", fg="#DC2626", bg="#FEE2E2")
            else:
                self.card_dist.configure(bg="#FAF5FF", highlightbackground="#E9D5FF")
                self.lbl_dist_val.configure(fg="#7E22CE", bg="#FAF5FF")
                self.lbl_dist_stat.configure(text=f"Status: {dist.get('status','ok')} | Ambang: > {d_thresh:.1f} cm", fg="#4B5563", bg="#FAF5FF")

            # Ambang Kelembapan Tanah Min
            s_thresh = self.thresh_soil_var.get()
            if soil_pct is not None and soil_pct < s_thresh:
                alarm_active = True
                reasons.append(f"Soil {soil_pct:.1f}% < {s_thresh:.1f}%")
                self.card_soil.configure(bg="#FEE2E2", highlightbackground="#EF4444")
                self.lbl_soil_val.configure(fg="#DC2626", bg="#FEE2E2")
                self.lbl_soil_stat.configure(text=f"⚠️ ALARM: Tanah Kering (< {s_thresh:.1f}%)", fg="#DC2626", bg="#FEE2E2")
            else:
                self.card_soil.configure(bg="#FFFBEB", highlightbackground="#FDE68A")
                self.lbl_soil_val.configure(fg="#B45309", bg="#FFFBEB")
                soil_txt = f"ADC: {format_num(soil_adc, 0)} | Status: {soil.get('status','ok')}"
                self.lbl_soil_stat.configure(text=soil_txt, fg="#4B5563", bg="#FFFBEB")

            # Perbarui Teks Nilai Kartu
            self.lbl_temp_val.configure(text=f"{format_num(temp_val, 1)} °C")
            self.lbl_hum_val.configure(text=f"{format_num(hum_val, 1)} %RH")
            self.lbl_soil_val.configure(text=f"{format_num(soil_pct, 1)} %" if soil_pct is not None else f"ADC {format_num(soil_adc, 0)}")
            self.lbl_dist_val.configure(text=f"{format_num(dist_val, 1)} cm")

            # Perbarui Banner Status Alarm
            if alarm_active:
                self.alarm_triggered_count += 1
                self.last_alarm_reasons = reasons
                alarm_summary = " | ".join(reasons)
                self.alarm_banner.configure(text=f"⚠️ ALARM AKTIF: {alarm_summary[:45]}", fg="#EF4444")
                if self.audio_alarm_var.get() and HAS_WINSOUND and (self.total_received % 3 == 0):
                    try:
                        winsound.Beep(1200, 80)
                    except Exception:
                        pass
            else:
                self.alarm_banner.configure(text="SISTEM NORMAL", fg="#10B981")

            # Perbarui Counter Metrik
            self.lbl_metric_rec.configure(text=f"{self.total_received} baris")

            # Tambahkan Data ke Buffer Grafik Matplotlib
            self.plot_x.append(seq)
            if temp_val is not None:
                self.plot_temp.append(temp_val)
            if hum_val is not None:
                self.plot_hum.append(hum_val)
            if soil_pct is not None:
                self.plot_soil_pct.append(soil_pct)
            elif soil_adc is not None:
                # Normalisasi kasar 0-100 jika persen belum dikalibrasi
                self.plot_soil_pct.append(max(0, min(100, (4095 - soil_adc) / 40.95)))
            if dist_val is not None:
                self.plot_dist.append(dist_val)

            # Redraw Grafik Real-time
            self._update_plots(seq)

            # Catat Latency UI (Respons Tampilan ms)
            t_ui_end = time.perf_counter()
            ui_latency_ms = (t_ui_end - t_ui_start) * 1000.0
            self.ui_latencies.append(ui_latency_ms)
            mean_ui_lat = sum(self.ui_latencies) / len(self.ui_latencies)
            self.lbl_metric_ui.configure(text=f"{mean_ui_lat:.1f} ms")

            # Catat ke Tabel Riwayat Masuk (Treeview)
            local_time_str = datetime.now().strftime("%H:%M:%S")
            alarm_str = "⚠️ " + ", ".join(reasons) if alarm_active else "NORMAL"
            row_vals = (
                seq, local_time_str, format_num(temp_val, 1), format_num(hum_val, 1),
                format_num(soil_adc, 0), format_num(soil_pct, 1), format_num(dist_val, 1),
                format_num(self.current_rtt, 1), format_num(self.current_interval, 1), alarm_str
            )
            item_id = self.tree.insert("", 0, values=row_vals)
            # Batasi baris tabel maksimal 40 baris agar ringan
            children = self.tree.get_children()
            if len(children) > 40:
                self.tree.delete(children[-1])

            # Tulis ke File CSV Logging (Jika aktif)
            if self.csv_writer:
                try:
                    row_dict = {
                        'timestamp_local': datetime.now().isoformat(timespec='milliseconds'),
                        'received_at_utc': get_utc_timestamp(),
                        'boot_id': message.get('boot_id'),
                        'stream_id': message.get('stream_id'),
                        'seq': seq,
                        'esp_ms': message.get('esp_ms'),
                        'send_start_us': message.get('send_start_us'),
                        'packet_interval_ms': message.get('packet_interval_ms'),
                        'packet_bytes': raw_bytes,
                        'ui_latency_ms': round(ui_latency_ms, 2),
                        'alarm_active': 1 if alarm_active else 0,
                        'alarm_reasons': ";".join(reasons)
                    }
                    for s_name in SENSORS:
                        s_data = message.get(s_name, {})
                        for f_name in SENSOR_FIELDS:
                            row_dict[f'{s_name}_{f_name}'] = s_data.get(f_name)
                    self.csv_writer.writerow(row_dict)
                    if self.total_received % 5 == 0:
                        self.csv_file.flush()
                except Exception as csv_err:
                    pass

    def _update_plots(self, current_seq):
        """Memperbarui ketiga kurva subplot pada canvas Matplotlib."""
        if not self.plot_x:
            return

        x_vals = list(self.plot_x)

        # 1. Update Plot Suhu
        if len(self.plot_temp) == len(x_vals):
            self.line_temp.set_data(x_vals, list(self.plot_temp))
            t_thresh = self.thresh_temp_var.get()
            self.line_temp_thresh.set_ydata([t_thresh, t_thresh])
            self.ax1.set_xlim(min(x_vals), max(max(x_vals), min(x_vals) + 10))
            min_y = min(min(self.plot_temp), t_thresh - 2)
            max_y = max(max(self.plot_temp), t_thresh + 2)
            self.ax1.set_ylim(min_y - 1, max_y + 1)

        # 2. Update Plot Kelembapan
        if len(self.plot_hum) == len(x_vals):
            self.line_hum.set_data(x_vals, list(self.plot_hum))
            if len(self.plot_soil_pct) == len(x_vals):
                self.line_soil.set_data(x_vals, list(self.plot_soil_pct))
            self.ax2.set_xlim(min(x_vals), max(max(x_vals), min(x_vals) + 10))
            self.ax2.set_ylim(0, 100)

        # 3. Update Plot Jarak
        if len(self.plot_dist) == len(x_vals):
            self.line_dist.set_data(x_vals, list(self.plot_dist))
            d_thresh = self.thresh_dist_var.get()
            self.line_dist_thresh.set_ydata([d_thresh, d_thresh])
            self.ax3.set_xlim(min(x_vals), max(max(x_vals), min(x_vals) + 10))
            max_d = max(max(self.plot_dist), d_thresh + 10)
            self.ax3.set_ylim(0, max_d + 5)

        self.canvas.draw_idle()

    def show_slide6_dialog(self):
        """
        Membuka dialog popup yang menampilkan tabel hasil pengujian
        sesuai persis dengan format Slide 6 PPT (Paket 3 - GUI Monitoring).
        """
        dlg = tk.Toplevel(self)
        dlg.title("Rekapitulasi Hasil Pengujian GUI (Sesuai Slide 6 PPT)")
        dlg.geometry("750x480")
        dlg.transient(self)
        dlg.grab_set()

        # Header Dialog
        hdr = tk.Frame(dlg, bg="#1E3A8A", height=50)
        hdr.pack(fill=tk.X, side=tk.TOP)
        hdr.pack_propagate(False)
        tk.Label(
            hdr, text="📊 TABEL PENGUJIAN GUI MONITORING (SLIDE 6)",
            font=("Segoe UI", 12, "bold"), fg="#FFFFFF", bg="#1E3A8A"
        ).pack(anchor="w", padx=16, pady=12)

        content = ttk.Frame(dlg, padding=12)
        content.pack(fill=tk.BOTH, expand=True)

        ttk.Label(
            content,
            text="Nilai parameter berikut diekstraksi dari pengujian aktual yang sedang berjalan / baru saja selesai:",
            font=("Segoe UI", 9)
        ).pack(anchor="w", pady=(0, 8))

        # Kalkulasi Parameter
        mean_intv = sum(self.interval_history) / len(self.interval_history) if self.interval_history else 0.0
        mean_ui = sum(self.ui_latencies) / len(self.ui_latencies) if self.ui_latencies else 0.0
        grafik_ok = "Ya (Lancar tanpa freeze)" if self.total_received > 0 else "Belum diuji"
        alarm_ok = f"Ya ({self.alarm_triggered_count}x terdeteksi)" if self.alarm_triggered_count > 0 else "Ya (Sesuai ambang)"
        log_ok = f"Ya ({self.current_log_path.name})" if self.current_log_path else "Tidak"
        stabil_ok = "Ya (Tidak ada crash)" if self.total_received > 0 else "Belum diuji"

        # Tabel Parameter Slide 6
        table_box = ttk.Frame(content)
        table_box.pack(fill=tk.BOTH, expand=True, pady=6)

        t_cols = ("param", "val_curr", "desc")
        t_view = ttk.Treeview(table_box, columns=t_cols, show="headings", height=9)
        t_view.heading("param", text="Parameter Slide 6")
        t_view.heading("val_curr", text="Hasil Pengujian Saat Ini")
        t_view.heading("desc", text="Keterangan / Standar Acuan")

        t_view.column("param", width=220, anchor="w")
        t_view.column("val_curr", width=200, anchor="center")
        t_view.column("desc", width=280, anchor="w")

        data_rows = [
            ("Interval pembaruan (ms)", f"{mean_intv:.1f} ms", "Diukur dari selisih waktu paket MCU/simulasi"),
            ("Data diterima (baris)", f"{self.total_received} baris", f"Total frame valid (Seq unik: {len(self.seen_seqs)})"),
            ("Data gagal parsing (baris)", f"{self.total_invalid} baris", "Frame JSON korup / malformed"),
            ("Respons tampilan (ms)", f"{mean_ui:.2f} ms", "Durasi redraw widget & Matplotlib canvas"),
            ("Grafik diperbarui", grafik_ok, "Subplot Suhu, RH, Tanah, & Jarak real-time"),
            ("Alarm sesuai ambang", alarm_ok, "Evaluasi ambang batas Suhu, RH, Jarak, & Soil"),
            ("Logging tersimpan", log_ok, "Tersimpan otomatis dalam format .csv"),
            ("Apakah GUI stabil lama?", stabil_ok, "Thread-safe queue & exception isolation")
        ]

        for r in data_rows:
            t_view.insert("", tk.END, values=r)

        t_view.pack(fill=tk.BOTH, expand=True)

        # Tombol Salin ke Clipboard & Tutup
        btn_box = ttk.Frame(content)
        btn_box.pack(fill=tk.X, pady=(10, 0))

        def copy_to_clipboard():
            csv_lines = ["Parameter\tHasil Pengujian"]
            for r in data_rows:
                csv_lines.append(f"{r[0]}\t{r[1]}")
            text_to_copy = "\n".join(csv_lines)
            self.clipboard_clear()
            self.clipboard_append(text_to_copy)
            messagebox.showinfo("Berhasil Disalin", "Tabel pengujian berhasil disalin ke clipboard!\nAnda dapat langsung paste (Ctrl+V) ke PowerPoint atau Word.")

        btn_copy = tk.Button(
            btn_box, text="📋 Salin Nilai ke Clipboard (Tabel)", font=("Segoe UI", 9, "bold"),
            bg="#16A34A", fg="#FFFFFF", relief="raised", cursor="hand2", command=copy_to_clipboard
        )
        btn_copy.pack(side=tk.LEFT, padx=(0, 6))

        btn_close = ttk.Button(btn_box, text="Tutup", command=dlg.destroy)
        btn_close.pack(side=tk.RIGHT)

    def open_logs_folder(self):
        """Membuka folder logs di Windows Explorer."""
        try:
            import os
            os.startfile(str(LOGS_DIR))
        except Exception as e:
            messagebox.showinfo("Folder Log", f"Folder log berada di:\n{LOGS_DIR}")


# ==============================================================================
# MAIN ENTRY POINT
# ==============================================================================
if __name__ == "__main__":
    app = SmartPlantGUI()
    app.mainloop()
