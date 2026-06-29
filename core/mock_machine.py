"""
Mock Machine — Simulator data untuk mode development.
Menghasilkan dummy attendance log yang strukturnya identik dengan data asli
sehingga semua fitur (filter, grouping, export) bisa diuji tanpa koneksi LAN.
"""
import logging
import random
import time
from datetime import datetime, date, timedelta
from typing import Optional

from config import MachineConfig
from core.machine import BaseMachine, AttendanceRecord, ConnectionStatus

logger = logging.getLogger(__name__)

# ─── Dummy Employee Database ─────────────────────────────────
_MOCK_EMPLOYEES = [
    {"card_id": "0016539426", "employee_id": "1001", "name": "Ahmad Fauzi", "dept": "Produksi"},
    {"card_id": "0016539436", "employee_id": "1002", "name": "Budi Santoso", "dept": "Produksi"},
    {"card_id": "0016539109", "employee_id": "1003", "name": "Citra Dewi", "dept": "Admin"},
    {"card_id": "0016533630", "employee_id": "1004", "name": "Dedi Kurniawan", "dept": "Produksi"},
    {"card_id": "0016539193", "employee_id": "1936", "name": "Eka Pratama", "dept": "Warehouse"},
    {"card_id": "0016537415", "employee_id": "1244", "name": "Fitri Handayani", "dept": "Admin"},
    {"card_id": "0025348554", "employee_id": "0989", "name": "Gunawan Wibowo", "dept": "Produksi"},
    {"card_id": "0016539394", "employee_id": "1005", "name": "Hendra Saputra", "dept": "Produksi"},
    {"card_id": "0016536746", "employee_id": "1006", "name": "Indah Permata", "dept": "HRD"},
    {"card_id": "0016539383", "employee_id": "1945", "name": "Joko Widodo", "dept": "Produksi"},
    {"card_id": "0016539392", "employee_id": "1464", "name": "Kartini Sari", "dept": "Admin"},
    {"card_id": "0025353128", "employee_id": "1663", "name": "Lukman Hakim", "dept": "Warehouse"},
    {"card_id": "0015612912", "employee_id": "1243", "name": "Maria Ulfa", "dept": "Produksi"},
    {"card_id": "0010045462", "employee_id": "1007", "name": "Naufal Rizki", "dept": "Produksi"},
    {"card_id": "0010045820", "employee_id": "1008", "name": "Olivia Putri", "dept": "Admin"},
    {"card_id": "0010034242", "employee_id": "1009", "name": "Purnomo Adi", "dept": "Warehouse"},
    {"card_id": "0010045807", "employee_id": "1010", "name": "Qorina Zahra", "dept": "HRD"},
    {"card_id": "0025333370", "employee_id": "1185", "name": "Rudi Hermawan", "dept": "Produksi"},
    {"card_id": "0016540001", "employee_id": "1011", "name": "Siti Aminah", "dept": "Produksi"},
    {"card_id": "0016540002", "employee_id": "1012", "name": "Tono Sugiarto", "dept": "Warehouse"},
]

# Nama terminal/door yang realistis
_MOCK_DOORS = ["MAIN", "SIDE", "BACK", "GATE-A", "GATE-B"]


def _generate_mock_records(
    machine_name: str,
    start_date: date,
    end_date: date,
    records_per_day_range: tuple[int, int] = (30, 80),
) -> list[AttendanceRecord]:
    """
    Generate dummy attendance records yang realistis.
    
    Logika:
    - Setiap hari, sebagian karyawan hadir (70-95%)
    - Setiap karyawan yang hadir punya 1-4 tap (masuk, istirahat keluar/masuk, pulang)
    - Jam masuk: 06:30 - 08:30
    - Jam pulang: 16:00 - 18:30
    - Tap tengah hari: 11:30 - 13:30
    """
    records = []
    current = start_date

    while current <= end_date:
        # Pilih berapa karyawan yang hadir hari ini (70-95%)
        attendance_rate = random.uniform(0.70, 0.95)
        employees_today = random.sample(
            _MOCK_EMPLOYEES,
            k=int(len(_MOCK_EMPLOYEES) * attendance_rate)
        )

        for emp in employees_today:
            door = random.choice(_MOCK_DOORS)

            # TAP 1: Masuk pagi (06:30 - 08:30)
            hour_in = random.randint(6, 8)
            min_in = random.randint(0, 59)
            sec_in = random.randint(0, 59)
            if hour_in == 8:
                min_in = random.randint(0, 30)
            ts_in = datetime(current.year, current.month, current.day,
                             hour_in, min_in, sec_in)

            records.append(AttendanceRecord(
                user_id=emp["employee_id"],
                name=emp["name"],
                timestamp=ts_in,
                status=0,  # Check-In
                punch=random.choice([1, 2]),  # Fingerprint atau Card
                machine_name=machine_name,
                card_id=emp["card_id"],
                department=emp["dept"],
                door=door,
            ))

            # TAP 2 (optional 60%): Keluar istirahat (11:30-12:30)
            if random.random() < 0.6:
                ts_break_out = datetime(current.year, current.month, current.day,
                                        random.randint(11, 12),
                                        random.randint(0, 59),
                                        random.randint(0, 59))
                records.append(AttendanceRecord(
                    user_id=emp["employee_id"],
                    name=emp["name"],
                    timestamp=ts_break_out,
                    status=1,  # Check-Out (break)
                    punch=random.choice([1, 2]),
                    machine_name=machine_name,
                    card_id=emp["card_id"],
                    department=emp["dept"],
                    door=door,
                ))

                # TAP 3: Masuk dari istirahat (12:30-13:30)
                ts_break_in = datetime(current.year, current.month, current.day,
                                       random.randint(12, 13),
                                       random.randint(0, 59),
                                       random.randint(0, 59))
                if ts_break_in > ts_break_out:
                    records.append(AttendanceRecord(
                        user_id=emp["employee_id"],
                        name=emp["name"],
                        timestamp=ts_break_in,
                        status=0,  # Check-In (back from break)
                        punch=random.choice([1, 2]),
                        machine_name=machine_name,
                        card_id=emp["card_id"],
                        department=emp["dept"],
                        door=door,
                    ))

            # TAP terakhir: Pulang (16:00-18:30)
            hour_out = random.randint(16, 18)
            min_out = random.randint(0, 59)
            sec_out = random.randint(0, 59)
            if hour_out == 18:
                min_out = random.randint(0, 30)
            ts_out = datetime(current.year, current.month, current.day,
                              hour_out, min_out, sec_out)

            records.append(AttendanceRecord(
                user_id=emp["employee_id"],
                name=emp["name"],
                timestamp=ts_out,
                status=1,  # Check-Out
                punch=random.choice([1, 2]),
                machine_name=machine_name,
                card_id=emp["card_id"],
                department=emp["dept"],
                door=door,
            ))

        current += timedelta(days=1)

    return records


class MockMachine(BaseMachine):
    """
    Simulator mesin fingerprint untuk mode development.
    Tidak melakukan koneksi jaringan — semua data di-generate lokal.
    """

    def __init__(self, config: MachineConfig):
        super().__init__(config)

    def connect(self) -> tuple[bool, str]:
        """Simulasi koneksi berhasil (instant, tanpa jaringan)."""
        # Simulasi delay kecil agar terasa realistis di UI
        time.sleep(0.3)
        self.status = ConnectionStatus.CONNECTED
        msg = (
            f"[MOCK] Terhubung ke {self.name}\n"
            f"  IP: {self.ip}:{self.port} (simulated)\n"
            f"  Mode: Development/Mock"
        )
        logger.info(f"[{self.name}] MOCK connected")
        return True, msg

    def disconnect(self):
        """Simulasi disconnect."""
        self.status = ConnectionStatus.DISCONNECTED

    def test_connection(self) -> tuple[bool, str]:
        """Simulasi test koneksi berhasil."""
        time.sleep(0.2)
        return True, f"[MOCK] {self.name}: Koneksi OK (simulated)"

    def get_attendance_logs(self) -> tuple[list[AttendanceRecord], str]:
        """Generate dummy data untuk 30 hari terakhir."""
        today = date.today()
        start = today.replace(day=1)
        return self._generate(start, today)

    def get_attendance_by_date(
        self, start_month: int, start_day: int, start_year: int,
        end_month: int, end_day: int, end_year: int
    ) -> tuple[list[AttendanceRecord], str]:
        """Generate dummy data sesuai rentang tanggal yang diminta."""
        full_year = 2000 + start_year
        start_d = date(full_year, start_month, start_day)

        full_year_end = 2000 + end_year
        end_d = date(full_year_end, end_month, end_day)

        return self._generate(start_d, end_d)

    def _generate(self, start_d: date, end_d: date) -> tuple[list[AttendanceRecord], str]:
        """Internal: generate mock records untuk rentang tanggal."""
        self.status = ConnectionStatus.FETCHING
        # Simulasi delay baca data
        time.sleep(random.uniform(0.5, 1.5))

        records = _generate_mock_records(
            machine_name=self.name,
            start_date=start_d,
            end_date=end_d,
        )

        self.status = ConnectionStatus.CONNECTED
        msg = f"[MOCK][{self.name}] Generated {len(records)} dummy records ({start_d} - {end_d})"
        logger.info(msg)
        return records, msg

    def ping(self) -> tuple[bool, str]:
        """Mock ping selalu berhasil."""
        time.sleep(0.1)
        return True, f"[MOCK] Host {self.ip} reachable (simulated)"
