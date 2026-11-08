"""
ESP32 TCP to MQTT Bridge & CSV Logger - Paket 3
Workshop Mikrokontroler Lanjut & Teknik Antarmuka (PENS)
Menghubungkan ESP32 SoftAP (192.168.4.1:5000) atau Mock Server ke Mosquitto MQTT Broker (127.0.0.1:1883).
Mendukung Protocol 4, ACK instan untuk RTT, publikasi topik MQTT terstruktur, dan pencatatan CSV.
"""

import csv
from datetime import datetime, timezone
import json
from pathlib import Path
import random
import socket
import sys
import threading
import time

import paho.mqtt.client as mqtt

BASE_DIR = Path(__file__).resolve().parent
LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_ESP32_HOST = "192.168.4.1"
DEFAULT_ESP32_PORT = 5000
DEFAULT_MQTT_HOST = "127.0.0.1"
DEFAULT_MQTT_PORT = 1883

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


class Esp32MqttBridge:
    def __init__(self, esp_host, esp_port, mqtt_host, mqtt_port, aht_mode="fast", packets=0):
        self.esp_host = esp_host
        self.esp_port = esp_port
        self.mqtt_host = mqtt_host
        self.mqtt_port = mqtt_port
        self.aht_mode = aht_mode
        self.packets = packets

        self.running = False
        self.sock = None
        self.stream_id = None
        self.boot_id = None
        self.seq_count = 0

        # Inisialisasi MQTT Client (Paho v2)
        try:
            self.mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="esp32-bridge-wmlta")
        except Exception:
            self.mqtt_client = mqtt.Client(client_id="esp32-bridge-wmlta")

        self.csv_file = None
        self.csv_writer = None

    def start(self):
        print("=" * 65)
        print("  ESP32 TCP -> MQTT BRIDGE & LOGGER (PAKET 3)")
        print(f"  Target ESP32 : {self.esp_host}:{self.esp_port}")
        print(f"  Target MQTT  : {self.mqtt_host}:{self.mqtt_port}")
        print(f"  Mode AHT10   : {self.aht_mode} | Target: {self.packets or 'Kontinu'}")
        print("=" * 65)

        # 1. Hubungkan ke Broker MQTT
        try:
            self.mqtt_client.connect(self.mqtt_host, self.mqtt_port, keepalive=60)
            self.mqtt_client.loop_start()
            print("[OK] Terhubung ke Broker Mosquitto MQTT!")
        except Exception as e:
            print(f"[ERROR] Gagal terhubung ke Mosquitto ({self.mqtt_host}:{self.mqtt_port}): {e}")
            print("Pastikan service Mosquitto sedang berjalan (net start mosquitto).")
            return

        # 2. Inisialisasi CSV Logging
        t_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_path = LOGS_DIR / f"log_mqtt_{t_str}.csv"
        try:
            self.csv_file = open(csv_path, 'w', newline='', encoding='utf-8-sig')
            self.csv_writer = csv.DictWriter(self.csv_file, fieldnames=CSV_FIELDS, delimiter=';')
            self.csv_writer.writeheader()
            print(f"[OK] File log CSV siap: {csv_path.name}")
        except Exception as e:
            print(f"[WARN] Gagal membuat CSV log: {e}")

        # 3. Hubungkan ke ESP32 TCP
        self.running = True
        print(f"[INFO] Menghubungkan ke TCP {self.esp_host}:{self.esp_port}...")
        try:
            self.sock = socket.create_connection((self.esp_host, self.esp_port), timeout=8.0)
            self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            self.sock.settimeout(0.3)
            print("[OK] Terhubung ke ESP32 TCP Socket!")
            self.mqtt_client.publish("smartplant/status", "CONNECTED", qos=1, retain=True)
            self.process_tcp_stream()
        except Exception as e:
            print(f"[ERROR] Koneksi ke ESP32 gagal: {e}")
            self.mqtt_client.publish("smartplant/status", f"DISCONNECTED: {e}", qos=1, retain=True)
        finally:
            self.stop()

    def process_tcp_stream(self):
        buffer = b""
        while self.running:
            try:
                chunk = self.sock.recv(4096)
                if not chunk:
                    print("[INFO] ESP32 menutup koneksi.")
                    break
                buffer += chunk
                while b'\n' in buffer:
                    line, buffer = buffer.split(b'\n', 1)
                    line_str = line.decode('utf-8', errors='replace').strip()
                    if not line_str:
                        continue
                    try:
                        msg = json.loads(line_str)
                    except Exception:
                        continue

                    msg_type = msg.get('type')
                    if msg_type == 'hello':
                        self.boot_id = msg.get('boot_id')
                        cmd = f"STREAM,{self.aht_mode},{self.packets}\n".encode('ascii')
                        self.sock.sendall(cmd)
                        print(f"[TX ESP32] STREAM,{self.aht_mode},{self.packets} dikirim")

                    elif msg_type == 'status':
                        if msg.get('state') == 'running':
                            self.stream_id = msg.get('stream_id')
                            print(f"[INFO] Stream Berjalan: {self.stream_id}")
                            self.mqtt_client.publish("smartplant/status", "STREAMING", qos=1)
                        elif msg.get('state') == 'done':
                            print("[INFO] ESP32 selesai mengirim target paket.")
                            self.mqtt_client.publish("smartplant/status", "DONE", qos=1)
                            self.running = False
                            break

                    elif msg_type == 'data':
                        # BALAS ACK SEGERA agar RTT ESP32 tetap presisi
                        cur_stream = self.stream_id or msg.get('stream_id', '')
                        seq_num = msg.get('seq', 0)
                        try:
                            ack_cmd = f"ACK,{cur_stream},{seq_num}\n".encode('ascii')
                            self.sock.sendall(ack_cmd)
                        except Exception:
                            pass

                        self.seq_count += 1
                        self.publish_and_log(msg, len(line) + 1)

                    elif msg_type == 'rtt':
                        rtt_val = msg.get('rtt_ms')
                        if rtt_val is not None:
                            self.mqtt_client.publish("smartplant/rtt", str(rtt_val), qos=0)

            except socket.timeout:
                continue
            except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError):
                print("[INFO] Koneksi TCP terputus.")
                break
            except Exception as e:
                print(f"[ERROR] Stream error: {e}")
                break

    def publish_and_log(self, msg, raw_bytes):
        soil = msg.get('soil', {})
        aht = msg.get('aht', {})
        dist = msg.get('ultrasonic', {})

        temp = aht.get('value')
        hum = aht.get('second')
        soil_adc = soil.get('value')
        soil_pct = soil.get('second')
        dist_cm = dist.get('value')
        seq = msg.get('seq')

        # Evaluasi Alarm Sederhana
        alarm_active = 0
        reasons = []
        if temp is not None and temp > 32.0:
            alarm_active = 1
            reasons.append(f"Suhu {temp:.1f}C > 32C")
        if dist_cm is not None and dist_cm < 15.0:
            alarm_active = 1
            reasons.append(f"Jarak {dist_cm:.1f}cm < 15cm")
        if soil_pct is not None and soil_pct < 20.0:
            alarm_active = 1
            reasons.append("Tanah Kering")

        # Publikasi ke MQTT Topics
        if temp is not None:
            self.mqtt_client.publish("smartplant/suhu", f"{temp:.2f}", qos=0)
        if hum is not None:
            self.mqtt_client.publish("smartplant/kelembapan", f"{hum:.1f}", qos=0)
        if soil_pct is not None:
            self.mqtt_client.publish("smartplant/soil", f"{soil_pct:.1f}", qos=0)
        elif soil_adc is not None:
            self.mqtt_client.publish("smartplant/soil", f"{soil_adc:.0f}", qos=0)
        if dist_cm is not None:
            self.mqtt_client.publish("smartplant/jarak", f"{dist_cm:.1f}", qos=0)

        # Publikasi Status Alarm & Paket Lengkap
        alarm_str = "ALARM: " + ", ".join(reasons) if alarm_active else "NORMAL"
        self.mqtt_client.publish("smartplant/alarm", alarm_str, qos=0)
        self.mqtt_client.publish("smartplant/seq", str(seq), qos=0)
        self.mqtt_client.publish("smartplant/raw", json.dumps(msg), qos=0)

        # Output Ringkas ke Terminal
        print(f"[MQTT PUB #{seq}] Suhu: {temp}°C | RH: {hum}% | Soil: {soil_pct}% | Jarak: {dist_cm}cm | {alarm_str}")

        # Tulis ke CSV
        if self.csv_writer:
            try:
                row_dict = {
                    'timestamp_local': datetime.now().isoformat(timespec='milliseconds'),
                    'received_at_utc': datetime.now(timezone.utc).isoformat(timespec='milliseconds'),
                    'boot_id': msg.get('boot_id'),
                    'stream_id': msg.get('stream_id'),
                    'seq': seq,
                    'esp_ms': msg.get('esp_ms'),
                    'send_start_us': msg.get('send_start_us'),
                    'packet_interval_ms': msg.get('packet_interval_ms'),
                    'packet_bytes': raw_bytes,
                    'ui_latency_ms': 0,
                    'alarm_active': alarm_active,
                    'alarm_reasons': ";".join(reasons)
                }
                for s_name in SENSORS:
                    s_data = msg.get(s_name, {})
                    for f_name in SENSOR_FIELDS:
                        row_dict[f'{s_name}_{f_name}'] = s_data.get(f_name)
                self.csv_writer.writerow(row_dict)
                if seq % 5 == 0:
                    self.csv_file.flush()
            except Exception:
                pass

    def stop(self):
        self.running = False
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
            self.sock = None

        if self.csv_file:
            try:
                self.csv_file.flush()
                self.csv_file.close()
            except Exception:
                pass
            self.csv_file = None

        try:
            self.mqtt_client.publish("smartplant/status", "DISCONNECTED", qos=1, retain=True)
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()
        except Exception:
            pass
        print("[INFO] Bridge dimatikan dengan aman.")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="ESP32 TCP to MQTT Bridge")
    parser.add_argument("--host", default=DEFAULT_ESP32_HOST, help="ESP32 IP (default 192.168.4.1 atau 127.0.0.1)")
    parser.add_argument("--port", type=int, default=DEFAULT_ESP32_PORT, help="ESP32 Port (default 5000)")
    parser.add_argument("--mqtt-host", default=DEFAULT_MQTT_HOST, help="MQTT Broker IP (default 127.0.0.1)")
    parser.add_argument("--mqtt-port", type=int, default=DEFAULT_MQTT_PORT, help="MQTT Broker Port (default 1883)")
    parser.add_argument("--aht-mode", default="fast", choices=["fast", "recommended"])
    parser.add_argument("--packets", type=int, default=0, help="Target paket (0 = kontinu)")

    args = parser.parse_args()
    bridge = Esp32MqttBridge(args.host, args.port, args.mqtt_host, args.mqtt_port, args.aht_mode, args.packets)
    try:
        bridge.start()
    except KeyboardInterrupt:
        print("\n[INFO] Menghentikan bridge via Ctrl+C...")
        bridge.stop()
