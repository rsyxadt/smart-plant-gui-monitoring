"""
Skrip Pemasang Aman Flow Smart Plant ke Node-RED
Workshop Mikrokontroler Lanjut & Teknik Antarmuka (PENS)
- Membackup flows.json asli sebelum modifikasi
- Menambahkan tab 'Smart Plant (Paket 3)' tanpa mengganggu flows lama
- Menghindari duplikasi node jika dijalankan berulang kali
"""

from datetime import datetime
import json
import os
from pathlib import Path
import shutil
import sys

USER_PROFILE = os.environ.get("USERPROFILE", "")
NODE_RED_DIR = Path(USER_PROFILE) / ".node-red"
FLOWS_PATH = NODE_RED_DIR / "flows.json"
BASE_DIR = Path(__file__).resolve().parent
SMARTPLANT_FLOWS_PATH = BASE_DIR / "flows_smartplant.json"


def setup_flows():
    print("=" * 60)
    print("  PEMASANG FLOW SMART PLANT KE NODE-RED (PAKET 3)")
    print("=" * 60)

    if not FLOWS_PATH.exists():
        print(f"[ERROR] Berkas flows.json tidak ditemukan di: {FLOWS_PATH}")
        sys.exit(1)

    # 1. Buat Backup Otomatis
    t_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = NODE_RED_DIR / f"flows_backup_before_smartplant_{t_str}.json"
    shutil.copy2(FLOWS_PATH, backup_path)
    print(f"[OK] Berkas asli berhasil dibackup ke:\n     {backup_path.name}")

    # 2. Baca flows.json lama
    with open(FLOWS_PATH, 'r', encoding='utf-8') as f:
        existing_flows = json.load(f)

    # 3. Baca flows_smartplant.json baru
    with open(SMARTPLANT_FLOWS_PATH, 'r', encoding='utf-8') as f:
        sp_flows = json.load(f)

    sp_node_ids = {n['id'] for n in sp_flows}

    # 4. Hapus node Smart Plant versi sebelumnya jika ada (agar idempotent/tidak dobel)
    filtered_flows = [n for n in existing_flows if n.get('id') not in sp_node_ids]

    # 5. Gabungkan flow baru
    merged_flows = filtered_flows + sp_flows

    # 6. Tulis kembali ke flows.json
    with open(FLOWS_PATH, 'w', encoding='utf-8') as f:
        json.dump(merged_flows, f, indent=2, ensure_ascii=False)

    print(f"[OK] Berhasil memasang tab 'Smart Plant (Paket 3)' ke Node-RED!")
    print(f"     Total nodes di flows.json: {len(merged_flows)} (lama: {len(existing_flows)})")
    print("\nLangkah selanjutnya:")
    print("1. Jalankan 'RUN_NODERED.bat' untuk menyalakan Node-RED dan membuka dashboard.")
    print("2. Akses dashboard di browser: http://localhost:1880/ui/")


if __name__ == "__main__":
    setup_flows()
