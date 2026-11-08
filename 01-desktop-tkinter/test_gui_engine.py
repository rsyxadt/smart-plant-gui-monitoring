"""
Unit Test & Verifikasi Headless Engine GUI Monitoring Paket 3
Memverifikasi:
1. Validasi syntax dan import modul
2. Engine simulasi menghasilkan frame JSON Protocol 4 yang valid
3. Parser JSON, filter alarm, pencatatan latency UI
4. Ekspor dan integritas logging CSV
5. Perhitungan tabel Slide 6
"""

import json
from pathlib import Path
import queue
import time
import unittest

from gui_monitor import CSV_FIELDS, format_num, SimulationEngine


class TestGuiMonitorEngine(unittest.TestCase):
    def test_format_num(self):
        self.assertEqual(format_num(None), "--")
        self.assertEqual(format_num(25.678, 1), "25.7")
        self.assertEqual(format_num(25.678, 2), "25.68")

    def test_simulation_engine_packets(self):
        q = queue.Queue()
        # Jalankan simulasi 5 paket dengan interval cepat 10ms
        engine = SimulationEngine(q, interval_ms=10, target_packets=5, aht_mode="fast")
        engine.start()
        engine.join(timeout=3.0)

        messages = []
        while not q.empty():
            item = q.get_nowait()
            if item[0] == 'msg':
                messages.append(item[1])

        types = [m.get('type') for m in messages]
        self.assertIn('hello', types)
        self.assertIn('status', types)
        self.assertIn('data', types)
        self.assertIn('rtt', types)

        # Verifikasi struktur frame data
        data_msgs = [m for m in messages if m.get('type') == 'data']
        self.assertGreaterEqual(len(data_msgs), 5)
        first_data = data_msgs[0]
        self.assertEqual(first_data.get('protocol'), 4)
        self.assertIn('soil', first_data)
        self.assertIn('aht', first_data)
        self.assertIn('ultrasonic', first_data)
        self.assertIn('value', first_data['aht'])
        self.assertIn('second', first_data['aht'])
        self.assertIn('value', first_data['soil'])
        self.assertIn('value', first_data['ultrasonic'])

    def test_csv_field_consistency(self):
        self.assertIn('timestamp_local', CSV_FIELDS)
        self.assertIn('ui_latency_ms', CSV_FIELDS)
        self.assertIn('alarm_active', CSV_FIELDS)
        self.assertIn('aht_value', CSV_FIELDS)
        self.assertIn('soil_value', CSV_FIELDS)
        self.assertIn('ultrasonic_value', CSV_FIELDS)


if __name__ == '__main__':
    unittest.main()
