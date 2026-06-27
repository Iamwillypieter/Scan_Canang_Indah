"""
Konfigurasi aplikasi multi-device.
Mendukung 4 mesin fingerprint (Biotronix + Chiyu) secara bersamaan.
"""
import os
from dataclasses import dataclass, field
from enum import Enum

# ─── Aplikasi ────────────────────────────────────────────────
APP_NAME = "Absensi Canang Indah"
APP_VERSION = "3.0.0"
WINDOW_WIDTH = 1100
WINDOW_HEIGHT = 720

# ─── Network Defaults ────────────────────────────────────────
CONNECTION_TIMEOUT = 8      # detik - timeout koneksi awal
READ_TIMEOUT = 90           # detik - timeout baca data (search bisa lama)
MAX_RETRIES = 3             # jumlah percobaan ulang
RETRY_DELAY = 2            # detik delay antar retry
PING_TIMEOUT = 3            # detik - timeout ping check

# ─── Export ──────────────────────────────────────────────────
EXPORT_FOLDER = os.path.join(os.path.dirname(__file__), "data", "exports")
os.makedirs(EXPORT_FOLDER, exist_ok=True)

# ─── Logging ─────────────────────────────────────────────────
LOG_FOLDER = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(LOG_FOLDER, exist_ok=True)


# ─── Machine Types ───────────────────────────────────────────
class MachineType(Enum):
    """Tipe mesin yang didukung."""
    BIOTRONIX = "biotronix"   # ZKTeco protocol via pyzk (TCP port 4370)
    CHIYU = "chiyu"           # Web CGI interface via HTTP (port 80)


@dataclass
class MachineConfig:
    """Konfigurasi untuk satu mesin fingerprint."""
    name: str               # Nama display (misal: "Biotronix Lantai 1")
    ip: str                 # IP Address
    port: int               # Port (4370 untuk Biotronix, 80 untuk Chiyu)
    machine_type: MachineType
    enabled: bool = True
    password: int = 0       # Password mesin (Biotronix only)
    username: str = ""      # Username login (Chiyu only)
    web_password: str = ""  # Password login (Chiyu only)


# ─── Daftar Mesin ────────────────────────────────────────────
# Semua 4 mesin menggunakan web interface CGI (HTTP port 80).
# Mesin "Biotronix FingerPlus 6600" ternyata pakai interface Chiyu (if.cgi).
MACHINES: list[MachineConfig] = [
    MachineConfig(
        name="Chiyu - Mesin 1",
        ip="192.168.3.83",
        port=80,
        machine_type=MachineType.CHIYU,
        username="admin",
        web_password="admin",
    ),
    MachineConfig(
        name="Biotronix 6600 - Mesin 1",
        ip="192.168.3.85",
        port=80,
        machine_type=MachineType.CHIYU,  # Biotronix BXFP6600 pakai CGI interface
        username="admin",
        web_password="admin",
    ),
    MachineConfig(
        name="Chiyu - Mesin 2",
        ip="192.168.3.86",
        port=80,
        machine_type=MachineType.CHIYU,
        username="admin",
        web_password="admin",
    ),
    MachineConfig(
        name="Biotronix 6600 - Mesin 2",
        ip="192.168.3.87",
        port=80,
        machine_type=MachineType.CHIYU,  # Biotronix BXFP6600 pakai CGI interface
        username="admin",
        web_password="admin",
    ),
]
