import os
from dataclasses import dataclass, field
from enum import Enum

# ─── Load .env file ──────────────────────────────────────────
# Environment variable dari system/bat file lebih prioritas dari .env
_ENV_FILE = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(_ENV_FILE):
    with open(_ENV_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                # setdefault = hanya set jika BELUM ada di environment
                os.environ.setdefault(key.strip(), value.strip())

# ─── Environment Mode ────────────────────────────────────────
APP_MODE = os.environ.get("APP_MODE", "production").lower().strip()
IS_DEVELOPMENT = APP_MODE == "development"
IS_PRODUCTION = APP_MODE == "production"

# ─── Aplikasi ────────────────────────────────────────────────
APP_NAME = "Absensi Canang Indah"
APP_VERSION = "3.0.0"
WINDOW_WIDTH = 1100
WINDOW_HEIGHT = 720

# ─── Network Defaults ────────────────────────────────────────
CONNECTION_TIMEOUT = 8      
READ_TIMEOUT = 90          
MAX_RETRIES = 3           
RETRY_DELAY = 2            
PING_TIMEOUT = 3            

# ─── Export ──────────────────────────────────────────────────
EXPORT_FOLDER = os.path.join(os.path.dirname(__file__), "data", "exports")
os.makedirs(EXPORT_FOLDER, exist_ok=True)

# ─── Logging ─────────────────────────────────────────────────
LOG_FOLDER = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(LOG_FOLDER, exist_ok=True)


# ─── Machine Types ───────────────────────────────────────────
class MachineType(Enum):
    """Tipe mesin."""
    BIOTRONIX = "biotronix"   
    CHIYU = "chiyu"           


@dataclass
class MachineConfig:
    """Konfigurasi mesin fingerprint."""
    name: str             
    ip: str                 
    port: int               
    machine_type: MachineType
    enabled: bool = True
    password: int = 0      
    username: str = ""      
    web_password: str = ""  


# ─── Daftar Mesin ────────────────────────────────────────────
MACHINES: list[MachineConfig] = [
    MachineConfig(
        name="Chiyu - HRM",
        ip="192.168.3.83",
        port=80,
        machine_type=MachineType.CHIYU,
        username="admin",
        web_password="admin",
    ),
    MachineConfig(
        name="Biotronix 6600 - MDF",
        ip="192.168.3.85",
        port=80,
        machine_type=MachineType.CHIYU,  
        username="admin",
        web_password="admin",
    ),
    MachineConfig(
        name="Chiyu - PB-1000",
        ip="192.168.3.86",
        port=80,
        machine_type=MachineType.CHIYU,
        username="admin",
        web_password="admin",
    ),
    MachineConfig(
        name="Biotronix 6600 - Sanding PB-Line",
        ip="192.168.3.87",
        port=80,
        machine_type=MachineType.CHIYU,  
        username="admin",
        web_password="admin",
    ),
    MachineConfig(
        name="Chiyu - Kontraktor",
        ip="192.168.3.240",
        port=80,
        machine_type=MachineType.CHIYU,
        username="admin",
        web_password="admin",
    ),
]
