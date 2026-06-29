import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, Optional
from dataclasses import dataclass

from config import MACHINES, MachineConfig, MachineType, IS_DEVELOPMENT
from core.machine import (
    BaseMachine,
    AttendanceRecord,
    MachineResult,
    ConnectionStatus,
    ping_host,
)
from core.biotronix import BiotronixMachine
from core.chiyu import ChiyuMachine
from core.mock_machine import MockMachine

logger = logging.getLogger(__name__)


def create_machine(config: MachineConfig) -> BaseMachine:
    """
    Factory function: buat instance mesin sesuai tipe dan mode.
    Development mode → selalu MockMachine (tanpa koneksi jaringan).
    Production mode  → mesin asli (Biotronix/Chiyu via LAN).
    """
    if IS_DEVELOPMENT:
        return MockMachine(config)

    if config.machine_type == MachineType.BIOTRONIX:
        return BiotronixMachine(config)
    elif config.machine_type == MachineType.CHIYU:
        return ChiyuMachine(config)
    else:
        raise ValueError(f"Tipe mesin tidak dikenal: {config.machine_type}")


class MultiDeviceManager:
    def __init__(self, machines: list[MachineConfig] = None):
        self._configs = machines or MACHINES
        self._max_workers = len(self._configs)

    @property
    def machine_configs(self) -> list[MachineConfig]:
        return self._configs

    def ping_all(
        self, progress_callback: Optional[Callable[[str, bool, str], None]] = None
    ) -> list[tuple[str, bool, str]]:
      
        results = []

        with ThreadPoolExecutor(max_workers=self._max_workers) as executor:
            futures = {}
            for config in self._configs:
                if not config.enabled:
                    continue
                if IS_DEVELOPMENT:
                    future = executor.submit(
                        lambda ip=config.ip: (True, f"[MOCK] Host {ip} reachable (simulated)")
                    )
                else:
                    future = executor.submit(ping_host, config.ip)
                futures[future] = config

            for future in as_completed(futures):
                config = futures[future]
                try:
                    reachable, msg = future.result()
                    results.append((config.name, reachable, msg))
                    if progress_callback:
                        progress_callback(config.name, reachable, msg)
                except Exception as e:
                    results.append((config.name, False, f"Error: {e}"))
                    if progress_callback:
                        progress_callback(config.name, False, f"Error: {e}")

        return results

    def test_all_connections(
        self, progress_callback: Optional[Callable[[str, bool, str], None]] = None
    ) -> list[MachineResult]:
        results = []

        with ThreadPoolExecutor(max_workers=self._max_workers) as executor:
            futures = {}
            for config in self._configs:
                if not config.enabled:
                    continue
                future = executor.submit(self._test_single, config)
                futures[future] = config

            for future in as_completed(futures):
                config = futures[future]
                try:
                    result = future.result()
                    results.append(result)
                    if progress_callback:
                        progress_callback(config.name, result.success, result.message)
                except Exception as e:
                    error_result = MachineResult(
                        machine_name=config.name,
                        success=False,
                        message=f"Unexpected error: {e}",
                        records=[],
                        status=ConnectionStatus.ERROR,
                    )
                    results.append(error_result)
                    if progress_callback:
                        progress_callback(config.name, False, str(e))

        return results

    def fetch_all_attendance(
        self,
        progress_callback: Optional[Callable[[str, str, int], None]] = None,
        selected_machines: Optional[list[str]] = None,
        start_date: Optional[tuple[int, int, int]] = None,
        end_date: Optional[tuple[int, int, int]] = None,
    ) -> list[MachineResult]:
        results = []

        # Filter configs berdasarkan pilihan user
        configs_to_fetch = []
        for config in self._configs:
            if not config.enabled:
                continue
            if selected_machines and config.name not in selected_machines:
                continue
            configs_to_fetch.append(config)

        if not configs_to_fetch:
            return results

        workers = min(len(configs_to_fetch), self._max_workers)

        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {}
            for i, config in enumerate(configs_to_fetch):
                # Stagger start: 1 detik jeda antar mesin agar tidak overload jaringan
                if i > 0:
                    import time
                    time.sleep(1)
                future = executor.submit(
                    self._fetch_single, config, progress_callback,
                    start_date, end_date
                )
                futures[future] = config

            for future in as_completed(futures):
                config = futures[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    error_result = MachineResult(
                        machine_name=config.name,
                        success=False,
                        message=f"Unexpected error: {e}",
                        records=[],
                        status=ConnectionStatus.ERROR,
                    )
                    results.append(error_result)
                    logger.error(
                        f"[{config.name}] Uncaught error: {e}", exc_info=True
                    )

        return results

    def _test_single(self, config: MachineConfig) -> MachineResult:
        """Test koneksi ke satu mesin."""
        machine = create_machine(config)
        success, message = machine.test_connection()

        return MachineResult(
            machine_name=config.name,
            success=success,
            message=message,
            records=[],
            status=ConnectionStatus.CONNECTED if success else ConnectionStatus.ERROR,
        )

    def _fetch_single(
        self,
        config: MachineConfig,
        progress_callback: Optional[Callable],
        start_date: Optional[tuple[int, int, int]] = None,
        end_date: Optional[tuple[int, int, int]] = None,
    ) -> MachineResult:
        max_fetch_attempts = 2

        for attempt in range(1, max_fetch_attempts + 1):
            machine = create_machine(config)

            if progress_callback:
                msg = "Connecting..." if attempt == 1 else f"Retry {attempt}..."
                progress_callback(config.name, msg, 0)

            # Connect
            success, connect_msg = machine.connect()
            if not success:
                if attempt < max_fetch_attempts:
                    import time
                    time.sleep(3)  # Tunggu sebentar sebelum retry
                    continue
                if progress_callback:
                    progress_callback(config.name, f"GAGAL connect", 0)
                return MachineResult(
                    machine_name=config.name,
                    success=False,
                    message=connect_msg,
                    records=[],
                    status=ConnectionStatus.ERROR,
                )

            if progress_callback:
                progress_callback(config.name, "Menarik data...", 0)

            # Fetch attendance — dengan filter tanggal jika tersedia
            if start_date and end_date and isinstance(machine, ChiyuMachine):
                records, data_msg = machine.get_attendance_by_date(
                    start_month=start_date[0],
                    start_day=start_date[1],
                    start_year=start_date[2],
                    end_month=end_date[0],
                    end_day=end_date[1],
                    end_year=end_date[2],
                )
            else:
                records, data_msg = machine.get_attendance_logs()

            # Jika berhasil (ada data), langsung return
            if records:
                if progress_callback:
                    progress_callback(config.name, "Selesai", len(records))
                return MachineResult(
                    machine_name=config.name,
                    success=True,
                    message=data_msg,
                    records=records,
                    status=ConnectionStatus.CONNECTED,
                )

            # Jika kosong dan masih ada attempt, retry
            if attempt < max_fetch_attempts:
                logger.warning(
                    f"[{config.name}] Fetch attempt {attempt} returned 0 records, retrying..."
                )
                import time
                time.sleep(2)
                continue

            # Attempt terakhir tetap kosong
            if progress_callback:
                progress_callback(config.name, "Selesai (kosong)", 0)
            return MachineResult(
                machine_name=config.name,
                success=False,
                message=data_msg,
                records=[],
                status=ConnectionStatus.ERROR,
            )

        # Seharusnya tidak sampai sini
        return MachineResult(
            machine_name=config.name,
            success=False,
            message="Unexpected: all attempts exhausted",
            records=[],
            status=ConnectionStatus.ERROR,
        )
