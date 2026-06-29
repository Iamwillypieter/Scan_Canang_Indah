"""
Module dasar untuk koneksi mesin fingerprint.
Berisi dataclass AttendanceRecord dan abstract base class BaseMachine.
"""
import logging
import subprocess
import platform
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional

from config import MachineConfig, PING_TIMEOUT

logger = logging.getLogger(__name__)


# ─── Enums ────────────────────────────────────────────────────

class ConnectionStatus(Enum):
    """Status koneksi mesin."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"
    FETCHING = "fetching"


# ─── Data Model ──────────────────────────────────────────────

@dataclass
class AttendanceRecord:
    """Representasi satu record absensi (universal untuk semua tipe mesin)."""
    user_id: str
    name: str
    timestamp: datetime
    status: int       # 0=Check-In, 1=Check-Out, 2=Break-Out, 3=Break-In
    punch: int        # 0=Password, 1=Fingerprint, 2=Card
    machine_name: str = ""   # Dari mesin mana record ini berasal
    card_id: str = ""        # Card ID (nomor kartu)
    department: str = ""     # Departemen karyawan
    door: str = ""           # Nama pintu/lokasi

    @property
    def status_text(self) -> str:
        status_map = {
            0: "Check-In",
            1: "Check-Out",
            2: "Break-Out",
            3: "Break-In",
            4: "OT-In",
            5: "OT-Out",
        }
        return status_map.get(self.status, f"Unknown ({self.status})")

    @property
    def punch_text(self) -> str:
        punch_map = {
            0: "Password",
            1: "Fingerprint",
            2: "Card",
        }
        return punch_map.get(self.punch, f"Other ({self.punch})")


# ─── Result Container ────────────────────────────────────────

@dataclass
class MachineResult:
    """Hasil operasi ke satu mesin."""
    machine_name: str
    success: bool
    message: str
    records: list  # list[AttendanceRecord]
    status: ConnectionStatus = ConnectionStatus.DISCONNECTED
    device_info: dict = None

    def __post_init__(self):
        if self.device_info is None:
            self.device_info = {}


# ─── Network Utility ─────────────────────────────────────────

def ping_host(ip: str, timeout: int = PING_TIMEOUT) -> tuple[bool, str]:
    """
    Ping IP untuk cek apakah host reachable di jaringan.
    Returns: (reachable: bool, message: str)
    """
    try:
        param = "-n" if platform.system().lower() == "windows" else "-c"
        timeout_param = "-w" if platform.system().lower() == "windows" else "-W"
        # Timeout di Windows dalam milidetik
        timeout_val = str(timeout * 1000) if platform.system().lower() == "windows" else str(timeout)

        result = subprocess.run(
            ["ping", param, "1", timeout_param, timeout_val, ip],
            capture_output=True,
            text=True,
            timeout=timeout + 2,
        )

        if result.returncode == 0:
            # Extract response time jika ada
            output = result.stdout
            if "time=" in output or "time<" in output:
                return True, f"Host {ip} reachable (ping OK)"
            return True, f"Host {ip} reachable"
        else:
            return False, f"Host {ip} tidak merespons ping"

    except subprocess.TimeoutExpired:
        return False, f"Ping ke {ip} timeout ({timeout}s)"
    except FileNotFoundError:
        return False, "Perintah ping tidak ditemukan di sistem"
    except Exception as e:
        return False, f"Ping error: {str(e)}"


# ─── Abstract Base Class ─────────────────────────────────────

class BaseMachine(ABC):
    """
    Abstract base class untuk semua tipe mesin fingerprint.
    Setiap brand mesin harus implement class ini.
    """

    def __init__(self, config: MachineConfig):
        self.config = config
        self.status = ConnectionStatus.DISCONNECTED
        self._last_error: str = ""

    @property
    def name(self) -> str:
        return self.config.name

    @property
    def ip(self) -> str:
        return self.config.ip

    @property
    def port(self) -> int:
        return self.config.port

    @property
    def last_error(self) -> str:
        return self._last_error

    @abstractmethod
    def connect(self) -> tuple[bool, str]:
        """Buka koneksi ke mesin."""
        pass

    @abstractmethod
    def disconnect(self):
        """Tutup koneksi."""
        pass

    @abstractmethod
    def test_connection(self) -> tuple[bool, str]:
        """Test koneksi. Returns (success, message)."""
        pass

    @abstractmethod
    def get_attendance_logs(self) -> tuple[list[AttendanceRecord], str]:
        """Tarik data log absensi."""
        pass

    def ping(self) -> tuple[bool, str]:
        """Ping mesin untuk cek reachability."""
        return ping_host(self.ip)
