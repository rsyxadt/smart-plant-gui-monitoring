"""
Server Web & TCP Bridge ke ESP32 - GUI HTML Murni (Paket 3)
Workshop Mikrokontroler Lanjut & Teknik Antarmuka (PENS)
Menyajikan halaman index.html di http://localhost:8080/
Menghubungkan browser ke soket TCP ESP32 (192.168.4.1:5000) via Server-Sent Events (SSE).
Mendukung Protocol 4, ACK instan untuk RTT, dan pencatatan otomatis CSV di folder logs/.
"""

import csv
from datetime import datetime, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import queue
import socket
import sys
import threading
import time
import urllib.parse

PORT = 8080
BASE_DIR = Path(__file__).resolve().parent
LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

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

active_bridge = None
bridge_lock = threading.Lock()


class Esp32TcpWorker(threading.Thread):
    def __init__(self, host, port, aht_mode, packets, out_queue):
        super().__init__(daemon=True)
        self.host = host
        self.port = port
        self.aht_mode = aht_mode
        self.packets = packets
        self.out_queue = out_queue
        self.stop_event = threading.Event()
        self.sock = None
        self.stream_id = None
        self.boot_id = None
        self.csv_file = None
        self.csv_writer = None

    def run(self):
        t_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_path = LOGS_DIR / f"log_web_esp32_{t_str}.csv"
        try:
            self.csv_file = open(csv_path, 'w', newline='', encoding='utf-8-sig')
            self.csv_writer = csv.DictWriter(self.csv_file, fieldnames=CSV_FIELDS, delimiter=';')
            self.csv_writer.writeheader()
        except Exception:
            self.csv_file = None
            self.csv_writer = None

        buffer = b""
        try:
            self.out_queue.put(('info', f"Menghubungkan ke ESP32 ({self.host}:{self.port})..."))
            self.sock = socket.create_connection((self.host, self.port), timeout=6.0)
            self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            self.sock.settimeout(0.2)
            self.out_queue.put(('connected', f"Terhubung ke {self.host}:{self.port}"))

            while not self.stop_event.is_set():
                try:
                    chunk = self.sock.recv(4096)
                except socket.timeout:
                    continue
                except (ConnectionResetError, ConnectionAbortedError, OSError) as e:
                    self.out_queue.put(('disconnected', f"Koneksi terputus: {e}"))
                    break

                if not chunk:
                    self.out_queue.put(('disconnected', "Koneksi ditutup oleh ESP32"))
                    break

                buffer += chunk
                while b'\n' in buffer:
                    line, buffer = buffer.split(b'\n', 1)
                    raw_len = len(line) + 1
                    try:
                        msg = json.loads(line.decode('utf-8', errors='replace'))
                        if not isinstance(msg, dict):
                            self.out_queue.put(('invalid_frame', raw_len))
                            continue
                    except Exception:
                        self.out_queue.put(('invalid_frame', raw_len))
                        continue

                    msg_type = msg.get('type')
                    if msg_type == 'hello':
                        self.boot_id = msg.get('boot_id')
                        cmd = f"STREAM,{self.aht_mode},{self.packets}\n".encode('ascii')
                        self.sock.sendall(cmd)
                        self.out_queue.put(('msg', msg, raw_len))

                    elif msg_type == 'status':
                        if msg.get('state') == 'running':
                            self.stream_id = msg.get('stream_id')
                        self.out_queue.put(('msg', msg, raw_len))
                        if msg.get('state') == 'done':
                            self.stop_event.set()

                    elif msg_type == 'data':
                        # Balas ACK instan
                        cur_stream = self.stream_id or msg.get('stream_id', '')
                        seq_num = msg.get('seq', 0)
                        try:
                            ack_payload = f"ACK,{cur_stream},{seq_num}\n".encode('ascii')
                            self.sock.sendall(ack_payload)
                        except Exception:
                            pass

                        self.out_queue.put(('msg', msg, raw_len))

                        # Log ke CSV
                        if self.csv_writer:
                            try:
                                row_dict = {
                                    'timestamp_local': datetime.now().isoformat(timespec='milliseconds'),
                                    'received_at_utc': datetime.now(timezone.utc).isoformat(timespec='milliseconds'),
                                    'boot_id': msg.get('boot_id'),
                                    'stream_id': msg.get('stream_id'),
                                    'seq': seq_num,
                                    'esp_ms': msg.get('esp_ms'),
                                    'send_start_us': msg.get('send_start_us'),
                                    'packet_interval_ms': msg.get('packet_interval_ms'),
                                    'packet_bytes': raw_len,
                                    'ui_latency_ms': 0,
                                    'alarm_active': 0,
                                    'alarm_reasons': ""
                                }
                                for s_name in SENSORS:
                                    s_data = msg.get(s_name, {})
                                    for f_name in SENSOR_FIELDS:
                                        row_dict[f'{s_name}_{f_name}'] = s_data.get(f_name)
                                self.csv_writer.writerow(row_dict)
                                if seq_num % 5 == 0:
                                    self.csv_file.flush()
                            except Exception:
                                pass

                    elif msg_type == 'rtt':
                        self.out_queue.put(('msg', msg, raw_len))

        except socket.timeout:
            self.out_queue.put(('disconnected', "Timeout menghubungkan ke ESP32"))
        except Exception as e:
            self.out_queue.put(('disconnected', f"Gagal: {e}"))
        finally:
            if self.sock:
                try:
                    if self.stream_id:
                        self.sock.sendall(b"STOP\n")
                except Exception:
                    pass
                try:
                    self.sock.close()
                except Exception:
                    pass
            if self.csv_file:
                try:
                    self.csv_file.flush()
                    self.csv_file.close()
                except Exception:
                    pass
            self.out_queue.put(('disconnected', "Koneksi ditutup"))

    def stop(self):
        self.stop_event.set()
        if self.sock:
            try:
                self.sock.sendall(b"STOP\n")
            except Exception:
                pass


class WebRequestHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(BASE_DIR), **kwargs)

    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        super().end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/api/status":
            global active_bridge
            with bridge_lock:
                is_active = active_bridge is not None and active_bridge.is_alive()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'running': is_active}).encode('utf-8'))
            return

        elif path == "/api/stop":
            with bridge_lock:
                if active_bridge:
                    active_bridge.stop()
                    active_bridge = None
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'stopped': True}).encode('utf-8'))
            return

        elif path == "/api/stream":
            self.handle_sse(parsed)
            return

        elif path == "/":
            self.send_response(302)
            self.send_header('Location', '/index.html')
            self.end_headers()
            return

        super().do_GET()

    def handle_sse(self, parsed):
        global active_bridge
        query = urllib.parse.parse_qs(parsed.query)
        host = query.get('host', ['192.168.4.1'])[0]
        port = int(query.get('port', [5000])[0])
        aht_mode = query.get('aht_mode', ['fast'])[0]
        packets = int(query.get('packets', [0])[0])

        out_queue = queue.Queue()

        with bridge_lock:
            if active_bridge and active_bridge.is_alive():
                active_bridge.stop()
            active_bridge = Esp32TcpWorker(host, port, aht_mode, packets, out_queue)
            active_bridge.start()

        self.send_response(200)
        self.send_header('Content-Type', 'text/event-stream; charset=utf-8')
        self.send_header('Connection', 'keep-alive')
        self.end_headers()

        try:
            while True:
                try:
                    item = out_queue.get(timeout=0.5)
                except queue.Empty:
                    # Heartbeat
                    self.wfile.write(b": ping\n\n")
                    self.wfile.flush()
                    continue

                tag = item[0]
                payload = {}
                if tag == 'msg':
                    payload = {'event': 'message', 'data': item[1], 'bytes': item[2]}
                elif tag == 'connected':
                    payload = {'event': 'connected', 'message': item[1]}
                elif tag == 'disconnected':
                    payload = {'event': 'disconnected', 'message': item[1]}
                    self.wfile.write(f"data: {json.dumps(payload)}\n\n".encode('utf-8'))
                    self.wfile.flush()
                    break
                elif tag == 'invalid_frame':
                    payload = {'event': 'invalid_frame', 'bytes': item[1]}
                elif tag == 'info':
                    payload = {'event': 'info', 'message': item[1]}

                data_str = json.dumps(payload)
                self.wfile.write(f"data: {data_str}\n\n".encode('utf-8'))
                self.wfile.flush()

        except (BrokenPipeError, ConnectionResetError):
            pass
        finally:
            with bridge_lock:
                if active_bridge:
                    active_bridge.stop()
                    active_bridge = None


def main():
    server = ThreadingHTTPServer(('0.0.0.0', PORT), WebRequestHandler)
    print("=" * 60)
    print("  SMART PLANT WEB SERVER (PAKET 3 - HTML MURNI)")
    print(f"  Akses Dashboard di Browser: http://localhost:{PORT}/")
    print("  Tekan Ctrl+C untuk menghentikan server.")
    print("=" * 60)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nMenutup server...")
        server.server_close()


if __name__ == '__main__':
    main()
