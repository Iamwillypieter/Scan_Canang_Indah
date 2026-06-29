import os
from dataclasses import dataclass, field
from enum import Enum

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
        machine_type=MachineType.CHIYU,  
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
        machine_type=MachineType.CHIYU,  
        username="admin",
        web_password="admin",
    ),
    MachineConfig(
        name="Chiyu - Mesin 3",
        ip="192.168.3.240",
        port=80,
        machine_type=MachineType.CHIYU,
        username="admin",
        web_password="admin",
    ),
]
