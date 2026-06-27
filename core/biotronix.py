"""
Handler koneksi mesin Biotronix (protokol ZKTeco via pyzk).
Mendukung TCP dan UDP (auto-detect), dengan retry dan berbagai fallback.
"""
import logging
import time
import socket
from typing import Optional

from zk import ZK

from config import MachineConfig, CONNECTION_TIMEOUT, MAX_RETRIES, RETRY_DELAY
from core.machine import BaseMachine, AttendanceRecord, ConnectionStatus

logger = logging.getLogger(__name__)

# Strategi koneksi yang akan dicoba berurutan
CONNECTION_STRATEGIES = [
    {"force_udp": True,  "ommit_ping": True,  "desc": "UDP + skip ping"},
    {"force_udp": True,  "ommit_ping": False, "desc": "UDP + ping"},
    {"force_udp": False, "ommit_ping": True,  "desc": "TCP + skip ping"},
    {"force_udp": False, "ommit_ping": False, "desc": "TCP + ping"},
]


class BiotronixMachine(BaseMachine):
    """
    Koneksi ke mesin Biotronix via protokol ZKTeco.
    Mencoba berbagai strategi koneksi (UDP/TCP, dengan/tanpa ping)
    untuk menangani variasi firmware dan model mesin.
    """

    def __init__(self, config: MachineConfig):
        super().__init__(config)
        self._zk: Optional[ZK] = None
        self._conn = None
        self._working_strategy: Optional[dict] = None

    def connect(self) -> tuple[bool, str]:
        """
        Connect ke mesin Biotronix.
        Mencoba beberapa strategi koneksi secara berurutan:
        1. UDP + skip ping (paling umum untuk mesin baru)
        2. UDP + ping
        3. TCP + skip ping
        4. TCP + ping
        """
        self.status = ConnectionStatus.CONNECTING

        # Jika sudah pernah berhasil, pakai strategi yang sama
        strategies = (
            [self._working_strategy] if self._working_strategy
            else CONNECTION_STRATEGIES
        )

        all_errors = []

        for strategy in strategies:
            for attempt in range(1, MAX_RETRIES + 1):
                try:
                    protocol = "UDP" if strategy["force_udp"] else "TCP"
                    logger.info(
                        f"[{self.name}] Attempt {attempt}/{MAX_RETRIES} "
                        f"via {strategy['desc']} to {self.ip}:{self.port}..."
                    )

                    # Cek port dulu sebelum coba connect (quick fail)
                    if not strategy["force_udp"]:
                        if not self._check_port_open():
                            raise ConnectionError(
                                f"Port {self.port} tidak bisa diakses (TCP)"
                            )

                    self._zk = ZK(
                        self.ip,
                        port=self.port,
                        timeout=CONNECTION_TIMEOUT,
                        password=self.config.password,
                        force_udp=strategy["force_udp"],
                        ommit_ping=strategy["ommit_ping"],
                    )
                    self._conn = self._zk.connect()

                    # Verifikasi koneksi berhasil
                    firmware = self._conn.get_firmware_version()
                    serial = self._conn.get_serialnumber()

                    # Berhasil! Simpan strategi yang berhasil
                    self._working_strategy = strategy
                    self.status = ConnectionStatus.CONNECTED

                    msg = (
                        f"Terhubung ke {self.name}\n"
                        f"  IP: {self.ip}:{self.port} ({strategy['desc']})\n"
                        f"  Firmware: {firmware}\n"
                        f"  Serial: {serial}"
                    )
                    logger.info(f"[{self.name}] ✅ Connected via {strategy['desc']}")
                    return True, msg

                except Exception as e:
                    error_str = str(e)
                    self._last_error = error_str
                    all_errors.append(f"{strategy['desc']} attempt {attempt}: {error_str}")
                    logger.warning(
                        f"[{self.name}] {strategy['desc']} attempt {attempt} failed: {e}"
                    )

                    # Cleanup
                    self._cleanup()

                    if attempt < MAX_RETRIES:
                        time.sleep(RETRY_DELAY)

            # Strategi ini gagal semua, lanjut ke strategi berikutnya
            logger.info(f"[{self.name}] Strategy '{strategy['desc']}' exhausted, trying next...")

        # SEMUA strategi gagal
        self.status = ConnectionStatus.ERROR
        error_msg = (
            f"Gagal terhubung ke {self.name} ({self.ip}:{self.port})\n"
            f"\n"
            f"Semua strategi koneksi gagal:\n"
            + "\n".join(f"  • {e}" for e in all_errors[-4:])  # Show last 4 errors
            + f"\n\n"
            f"Troubleshooting:\n"
            f"  1. Pastikan mesin menyala & kabel LAN terpasang\n"
            f"  2. Cek IP di menu mesin (Communication > IP Address)\n"
            f"  3. Ping: ping {self.ip}\n"
            f"  4. Cek port: mungkin mesin pakai port 80 bukan 4370\n"
            f"  5. Matikan firewall Windows sementara untuk test\n"
            f"  6. Pastikan tidak ada software lain (ZKTime, dll) yang\n"
            f"     sedang terkoneksi ke mesin ini\n"
            f"  7. Restart mesin fingerprint"
        )
        return False, error_msg

    def _check_port_open(self) -> bool:
        """Quick check apakah TCP port bisa diakses."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            result = sock.connect_ex((self.ip, self.port))
            sock.close()
            return result == 0
        except Exception:
            return False

    def _cleanup(self):
        """Cleanup connection objects."""
        try:
            if self._conn:
                self._conn.disconnect()
        except Exception:
            pass
        self._conn = None
        self._zk = None

    def disconnect(self):
        """Tutup koneksi ke mesin Biotronix."""
        if self._conn:
            try:
                self._conn.disconnect()
                logger.info(f"[{self.name}] Disconnected")
            except Exception as e:
                logger.warning(f"[{self.name}] Disconnect error: {e}")
            finally:
                self._conn = None
                self._zk = None
                self.status = ConnectionStatus.DISCONNECTED

    def test_connection(self) -> tuple[bool, str]:
        """Test koneksi: connect → info → disconnect."""
        success, msg = self.connect()
        if success:
            self.disconnect()
        return success, msg

    def get_attendance_logs(self) -> tuple[list[AttendanceRecord], str]:
        """
        Tarik semua attendance log dari mesin Biotronix.
        """
        if not self._conn:
            success, msg = self.connect()
            if not success:
                return [], msg

        self.status = ConnectionStatus.FETCHING

        try:
            # Disable device sementara
            self._conn.disable_device()
            logger.info(f"[{self.name}] Device disabled untuk baca data...")

            # Ambil user list untuk mapping nama
            users = self._conn.get_users()
            user_map = {}
            for user in users:
                user_map[str(user.user_id)] = user.name or f"User-{user.user_id}"

            logger.info(f"[{self.name}] {len(user_map)} users loaded")

            # Ambil attendance log
            raw_attendance = self._conn.get_attendance()

            # Enable device kembali
            self._conn.enable_device()
            logger.info(f"[{self.name}] Device enabled kembali")

            if not raw_attendance:
                self.status = ConnectionStatus.CONNECTED
                return [], f"[{self.name}] Tidak ada data attendance di mesin."

            # Konversi ke AttendanceRecord
            records = []
            for att in raw_attendance:
                record = AttendanceRecord(
                    user_id=str(att.user_id),
                    name=user_map.get(str(att.user_id), f"ID-{att.user_id}"),
                    timestamp=att.timestamp,
                    status=att.status if hasattr(att, "status") else 0,
                    punch=att.punch if hasattr(att, "punch") else 0,
                    machine_name=self.name,
                )
                records.append(record)

            self.status = ConnectionStatus.CONNECTED
            msg = f"[{self.name}] Berhasil: {len(records)} record"
            logger.info(msg)
            return records, msg

        except Exception as e:
            try:
                self._conn.enable_device()
            except Exception:
                pass

            self.status = ConnectionStatus.ERROR
            self._last_error = str(e)
            error_msg = f"[{self.name}] Error baca data: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return [], error_msg

        finally:
            self.disconnect()
