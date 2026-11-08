"""
Mock ESP32 Protocol 4 TCP Server
Workshop Mikrokontroler Lanjut & Teknik Antarmuka (PENS)
Mensimulasikan ESP32 SoftAP (port 5000) untuk pengujian Node-RED secara offline.
Mendukung handshake hello, stream kontinu/target paket, ACK queue, dan perhitungan RTT.
"""

from datetime import datetime
import json
import math
import random
import socket
import sys
import threading
import time

HOST = "0.0.0.0"
PORT = 5000


def run_mock_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        server.bind((HOST, PORT))
    except Exception as e:
        print(f"[ERROR] Gagal bind ke {HOST}:{PORT}: {e}")
        sys.exit(1)

    server.listen(1)
    print("=" * 60)
    print("  MOCK ESP32 PROTOCOL 4 TCP SERVER")
    print(f"  Mendengarkan di {HOST}:{PORT}...")
    print("  Tekan Ctrl+C untuk menghentikan server.")
    print("=" * 60)

    try:
        while True:
            client, addr = server.accept()
            print(f"\n[INFO] Klien terhubung dari {addr[0]}:{addr[1]}")
            client.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            handle_client(client)
    except KeyboardInterrupt:
        print("\n[INFO] Menghentikan mock server...")
    finally:
        server.close()


def handle_client(sock):
    sock.settimeout(0.5)
    boot_id = f"mock_boot_{int(time.time())}"
    stream_id = None
    running = False
    aht_mode = "fast"
    target_packets = 0
    seq = 1

    # 1. Kirim frame Hello
    hello_msg = json.dumps({"type": "hello", "protocol": 4, "boot_id": boot_id}) + "\n"
    sock.sendall(hello_msg.encode('ascii'))
    print(f"[TX] Hello dikirim: {boot_id}")

    buffer = b""
    last_send = time.monotonic()
    start_stream_time = None

    try:
        while True:
            # Baca perintah dari klien (STREAM / ACK / STOP)
            try:
                chunk = sock.recv(1024)
                if not chunk:
                    print("[INFO] Klien menutup koneksi.")
                    break
                buffer += chunk
                while b'\n' in buffer:
                    line, buffer = buffer.split(b'\n', 1)
                    cmd = line.decode('ascii', errors='ignore').strip()
                    if not cmd:
                        continue
                    if cmd.startswith("STREAM"):
                        parts = cmd.split(',')
                        aht_mode = parts[1] if len(parts) > 1 else "fast"
                        target_packets = int(parts[2]) if len(parts) > 2 else 0
                        stream_id = f"str_{int(time.time()*1000)%1000000}"
                        running = True
                        seq = 1
                        start_stream_time = time.monotonic()
                        last_send = time.monotonic()

                        status_msg = json.dumps({
                            "type": "status", "protocol": 4, "boot_id": boot_id,
                            "stream_id": stream_id, "state": "running",
                            "aht_mode": aht_mode, "packets": target_packets
                        }) + "\n"
                        sock.sendall(status_msg.encode('ascii'))
                        print(f"[RX] Perintah STREAM ({aht_mode}, target={target_packets}) -> stream_id: {stream_id}")

                    elif cmd.startswith("ACK"):
                        parts = cmd.split(',')
                        if len(parts) >= 3:
                            ack_seq = int(parts[2])
                            rtt_val = random.uniform(32.0, 48.0)
                            rtt_msg = json.dumps({
                                "type": "rtt", "stream_id": stream_id,
                                "seq": ack_seq, "rtt_ms": round(rtt_val, 2)
                            }) + "\n"
                            sock.sendall(rtt_msg.encode('ascii'))

                    elif cmd == "STOP":
                        print("[RX] Perintah STOP diterima.")
                        running = False
                        done_msg = json.dumps({
                            "type": "status", "protocol": 4, "boot_id": boot_id,
                            "stream_id": stream_id, "state": "done", "sent": seq - 1,
                            "measurement_ms": int((time.monotonic() - (start_stream_time or time.monotonic())) * 1000)
                        }) + "\n"
                        sock.sendall(done_msg.encode('ascii'))
                        break
            except socket.timeout:
                pass

            # Jika stream aktif, kirim data secara berkala
            if running:
                now = time.monotonic()
                interval_target = 0.085 if aht_mode == "fast" else 2.0
                if now - last_send >= interval_target:
                    elapsed = now - start_stream_time
                    interval_ms = (now - last_send) * 1000.0 if seq > 1 else None
                    last_send = now

                    temp = 28.5 + 4.5 * math.sin(elapsed * 0.15) + random.uniform(-0.3, 0.3)
                    hum = 65.0 - 10.0 * math.sin(elapsed * 0.15) + random.uniform(-0.5, 0.5)
                    dist = max(5.0, 28.0 + 16.0 * math.cos(elapsed * 0.18) + random.uniform(-0.4, 0.4))
                    soil_adc = 2100 + 400 * math.sin(elapsed * 0.08) + random.uniform(-20, 20)
                    soil_pct = max(0.0, min(100.0, (1.0 - (soil_adc - 1500) / 1500) * 100.0))

                    frame = {
                        "type": "data",
                        "protocol": 4,
                        "boot_id": boot_id,
                        "stream_id": stream_id,
                        "seq": seq,
                        "esp_ms": int(elapsed * 1000),
                        "send_start_us": int(elapsed * 1000000),
                        "packet_interval_ms": interval_ms,
                        "soil": {
                            "sample": seq * 15, "value": round(soil_adc, 0), "second": round(soil_pct, 1),
                            "status": "ok", "completed_ms": int(elapsed * 1000), "read_us": 980,
                            "period_us": 1052, "age_ms": 2, "overwritten_since_packet": 14
                        },
                        "aht": {
                            "sample": seq, "value": round(temp, 2), "second": round(hum, 1),
                            "status": "ok", "completed_ms": int(elapsed * 1000), "read_us": 82000,
                            "period_us": int(interval_target * 1000000), "age_ms": 3, "overwritten_since_packet": 0
                        },
                        "ultrasonic": {
                            "sample": seq * 2, "value": round(dist, 1), "second": None,
                            "status": "ok", "completed_ms": int(elapsed * 1000), "read_us": 2400,
                            "period_us": 66666, "age_ms": 2, "overwritten_since_packet": 1
                        }
                    }

                    line = json.dumps(frame) + "\n"
                    sock.sendall(line.encode('ascii'))
                    print(f"[TX] Pkt #{seq} | T={temp:.1f}C | H={hum:.1f}% | Soil={soil_pct:.1f}% | Dist={dist:.1f}cm")

                    seq += 1
                    if target_packets > 0 and seq > target_packets:
                        print(f"[INFO] Target {target_packets} paket tercapai.")
                        running = False
                        done_msg = json.dumps({
                            "type": "status", "protocol": 4, "boot_id": boot_id,
                            "stream_id": stream_id, "state": "done", "sent": seq - 1,
                            "measurement_ms": int((time.monotonic() - start_stream_time) * 1000)
                        }) + "\n"
                        sock.sendall(done_msg.encode('ascii'))
                        break

    except (ConnectionResetError, ConnectionAbortedError, BrokenPipeError) as e:
        print(f"[INFO] Koneksi klien terputus: {e}")
    finally:
        sock.close()


if __name__ == "__main__":
    run_mock_server()
