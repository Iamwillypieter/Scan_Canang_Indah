import threading
from datetime import date, datetime
from typing import Callable

import customtkinter as ctk

from config import MACHINES, MachineType
from core.machine import ConnectionStatus, MachineResult
from core.multi_device import MultiDeviceManager


class MachineStatusCard(ctk.CTkFrame):
    def __init__(self, parent, name: str, ip: str, port: int, machine_type: MachineType):
        super().__init__(parent, border_width=1, border_color="gray40")
        self.grid_columnconfigure(2, weight=1)

        # Checkbox untuk pilih mesin
        self.selected = ctk.BooleanVar(value=True)
        self.checkbox = ctk.CTkCheckBox(
            self, text="", variable=self.selected, width=20
        )
        self.checkbox.grid(row=0, column=0, rowspan=2, padx=(8, 2), pady=8)

        # Status indicator (colored dot)
        self.status_dot = ctk.CTkLabel(
            self, text="⚪", font=ctk.CTkFont(size=14), width=20
        )
        self.status_dot.grid(row=0, column=1, rowspan=2, padx=(2, 5), pady=8)

        # Machine name
        ctk.CTkLabel(
            self,
            text=name,
            font=ctk.CTkFont(size=11, weight="bold"),
            anchor="w",
        ).grid(row=0, column=2, sticky="w", padx=3, pady=(8, 0))

        # IP info
        type_label = "ZKTeco" if machine_type == MachineType.BIOTRONIX else "HTTP"
        ctk.CTkLabel(
            self,
            text=f"{ip}:{port} ({type_label})",
            font=ctk.CTkFont(size=9),
            text_color="gray",
            anchor="w",
        ).grid(row=1, column=2, sticky="w", padx=3, pady=(0, 8))

        # Status text
        self.status_label = ctk.CTkLabel(
            self,
            text="Menunggu...",
            font=ctk.CTkFont(size=9),
            text_color="gray",
            anchor="e",
            wraplength=160,
        )
        self.status_label.grid(row=0, column=3, rowspan=2, padx=8, pady=8, sticky="e")

    def set_status(self, status: ConnectionStatus, message: str = ""):
        status_config = {
            ConnectionStatus.DISCONNECTED: ("⚪", "gray", "Idle"),
            ConnectionStatus.CONNECTING: ("🟡", "#F59E0B", "Connecting..."),
            ConnectionStatus.CONNECTED: ("🟢", "#10B981", "OK"),
            ConnectionStatus.ERROR: ("🔴", "#EF4444", "Error"),
            ConnectionStatus.FETCHING: ("🔵", "#3B82F6", "Fetching..."),
        }
        dot, color, default_msg = status_config.get(status, ("⚪", "gray", "?"))
        self.status_dot.configure(text=dot)
        self.status_label.configure(text=message or default_msg, text_color=color)


class ConnectionFrame(ctk.CTkFrame):

    def __init__(self, parent, on_data_received: Callable):
        super().__init__(parent, fg_color="transparent")
        self._on_data_received = on_data_received
        self._manager = MultiDeviceManager()
        self._machine_cards: dict[str, MachineStatusCard] = {}

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)
        self._build_ui()

    def _build_ui(self):
        # ─── Machine Status Cards ───────
        status_frame = ctk.CTkFrame(self)
        status_frame.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        status_frame.grid_columnconfigure(0, weight=1)
        status_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            status_frame,
            text="Pilih Mesin & Status",
            font=ctk.CTkFont(size=13, weight="bold"),
        ).grid(row=0, column=0, columnspan=2, pady=(12, 8), padx=15, sticky="w")

        for i, config in enumerate(MACHINES):
            card = MachineStatusCard(
                status_frame,
                name=config.name,
                ip=config.ip,
                port=config.port,
                machine_type=config.machine_type,
            )
            card.grid(row=1 + i // 2, column=i % 2, padx=8, pady=4, sticky="ew")
            self._machine_cards[config.name] = card

        # ─── Date Range Filter ────────────────────────────
        filter_frame = ctk.CTkFrame(self)
        filter_frame.grid(row=1, column=0, sticky="ew", pady=(0, 8))

        ctk.CTkLabel(
            filter_frame,
            text="Rentang Tanggal (Wajib untuk Tarik Data)",
            font=ctk.CTkFont(size=13, weight="bold"),
        ).grid(row=0, column=0, columnspan=6, pady=(12, 8), padx=15, sticky="w")

        # Start Date
        ctk.CTkLabel(filter_frame, text="Start Date:").grid(
            row=1, column=0, padx=(15, 5), pady=10, sticky="w"
        )
        self.start_date_entry = ctk.CTkEntry(
            filter_frame, placeholder_text="DD Month YYYY", width=145
        )
        self.start_date_entry.grid(row=1, column=1, padx=5, pady=10)

        # Set default: awal bulan ini
        today = date.today()
        first_day = today.replace(day=1)
        self.start_date_entry.insert(0, first_day.strftime("%d %B %Y"))

        # End Date
        ctk.CTkLabel(filter_frame, text="End Date:").grid(
            row=1, column=2, padx=(15, 5), pady=10, sticky="w"
        )
        self.end_date_entry = ctk.CTkEntry(
            filter_frame, placeholder_text="DD Month YYYY", width=145
        )
        self.end_date_entry.grid(row=1, column=3, padx=5, pady=10)

        # Set default: hari ini
        self.end_date_entry.insert(0, today.strftime("%d %B %Y"))

        # Quick date buttons
        ctk.CTkButton(
            filter_frame, text="Hari Ini", width=70, height=28,
            fg_color="#6B7280", hover_color="#4B5563",
            command=self._set_today,
        ).grid(row=1, column=4, padx=5, pady=10)

        ctk.CTkButton(
            filter_frame, text="Bulan Ini", width=75, height=28,
            fg_color="#6B7280", hover_color="#4B5563",
            command=self._set_this_month,
        ).grid(row=1, column=5, padx=(0, 15), pady=10)

        # ─── Action Buttons ───────────────────────────────
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=2, column=0, sticky="ew", pady=8)

        self.btn_ping = ctk.CTkButton(
            btn_frame,
            text="📡 Ping",
            command=self._ping_all,
            width=100,
            height=38,
            fg_color="#6366F1",
            hover_color="#4F46E5",
        )
        self.btn_ping.pack(side="left", padx=(0, 6))

        self.btn_test = ctk.CTkButton(
            btn_frame,
            text="🔌 Test Koneksi",
            command=self._test_all,
            width=130,
            height=38,
            fg_color="#2563EB",
            hover_color="#1D4ED8",
        )
        self.btn_test.pack(side="left", padx=(0, 6))

        self.btn_fetch = ctk.CTkButton(
            btn_frame,
            text="📥 Tarik Data Absensi",
            command=self._fetch_data,
            width=200,
            height=38,
            fg_color="#059669",
            hover_color="#047857",
            font=ctk.CTkFont(size=13, weight="bold"),
        )
        self.btn_fetch.pack(side="left", padx=(0, 6))

        # Select all / deselect all
        ctk.CTkButton(
            btn_frame, text="✅ Semua", width=75, height=28,
            fg_color="#374151", hover_color="#1F2937",
            command=self._select_all,
        ).pack(side="right", padx=(6, 0))

        ctk.CTkButton(
            btn_frame, text="☐ Kosongkan", width=90, height=28,
            fg_color="#374151", hover_color="#1F2937",
            command=self._deselect_all,
        ).pack(side="right", padx=(6, 0))

        # ─── Log Output ──────────────────────────────────
        self.log_textbox = ctk.CTkTextbox(self, height=160, state="disabled")
        self.log_textbox.grid(row=3, column=0, sticky="nsew", pady=(5, 0))

    # ─── Quick Date Setters ──────────────────────────────

    def _set_today(self):
        today = date.today().strftime("%d %B %Y")
        self.start_date_entry.delete(0, "end")
        self.start_date_entry.insert(0, today)
        self.end_date_entry.delete(0, "end")
        self.end_date_entry.insert(0, today)

    def _set_this_month(self):
        today = date.today()
        first = today.replace(day=1).strftime("%d %B %Y")
        self.start_date_entry.delete(0, "end")
        self.start_date_entry.insert(0, first)
        self.end_date_entry.delete(0, "end")
        self.end_date_entry.insert(0, today.strftime("%d %B %Y"))

    # ─── Machine Selection ───────────────────────────────

    def _select_all(self):
        for card in self._machine_cards.values():
            card.selected.set(True)

    def _deselect_all(self):
        for card in self._machine_cards.values():
            card.selected.set(False)

    def _get_selected_machines(self) -> list[str]:
        """Get nama mesin yang di-check."""
        return [
            name for name, card in self._machine_cards.items()
            if card.selected.get()
        ]

    # ─── Date Parsing ────────────────────────────────────

    def _parse_dates(self) -> tuple:
        start_str = self.start_date_entry.get().strip()
        end_str = self.end_date_entry.get().strip()

        if not start_str or not end_str:
            return None, None, "Tanggal Start dan End harus diisi."

        start_dt = self._flexible_parse_date(start_str)
        end_dt = self._flexible_parse_date(end_str)

        if not start_dt:
            return None, None, f"Format Start Date salah: '{start_str}'. Gunakan YYYY-MM-DD."
        if not end_dt:
            return None, None, f"Format End Date salah: '{end_str}'. Gunakan YYYY-MM-DD."

        if start_dt > end_dt:
            return None, None, "Start Date tidak boleh lebih besar dari End Date."

        # Chiyu CGI menggunakan year 2-digit, day dan month tanpa leading zero
        start_tuple = (start_dt.month, start_dt.day, start_dt.year % 100)
        end_tuple = (end_dt.month, end_dt.day, end_dt.year % 100)

        return start_tuple, end_tuple, ""

    @staticmethod
    def _flexible_parse_date(s: str):
        from datetime import datetime as dt
        formats = [
            "%d %B %Y",    # 27 June 2026  ← format utama
            "%d %b %Y",    # 27 Jun 2026
            "%Y-%m-%d",    # 2026-06-27
            "%d/%m/%Y",    # 27/06/2026
            "%m/%d/%Y",    # 06/27/2026
        ]
        s = s.strip()
        for fmt in formats:
            try:
                return dt.strptime(s, fmt)
            except ValueError:
                continue
        return None

    # ─── Logging ─────────────────────────────────────────

    def _log(self, message: str):
        def _update():
            self.log_textbox.configure(state="normal")
            self.log_textbox.insert("end", f"{message}\n")
            self.log_textbox.see("end")
            self.log_textbox.configure(state="disabled")
        self.after(0, _update)

    def _set_buttons_loading(self, loading: bool):
        state = "disabled" if loading else "normal"
        self.btn_ping.configure(state=state)
        self.btn_test.configure(state=state)
        self.btn_fetch.configure(state=state)

    # ─── Ping All ────────────────────────────────────────

    def _ping_all(self):
        selected = self._get_selected_machines()
        if not selected:
            self._log("⚠️ Tidak ada mesin yang dipilih.")
            return

        self._set_buttons_loading(True)
        self._log("─" * 45)
        self._log(f"📡 Ping {len(selected)} mesin...")

        for name in selected:
            self._machine_cards[name].set_status(ConnectionStatus.CONNECTING, "Pinging...")

        def _worker():
            def on_ping(name, reachable, msg):
                if name not in selected:
                    return
                status = ConnectionStatus.CONNECTED if reachable else ConnectionStatus.ERROR
                self.after(0, lambda n=name, s=status, m=msg: (
                    self._machine_cards[n].set_status(s, m)
                ))
                icon = "✅" if reachable else "❌"
                self._log(f"  {icon} {name}: {msg}")

            self._manager.ping_all(progress_callback=on_ping)
            self.after(0, lambda: self._set_buttons_loading(False))
            self._log("📡 Ping selesai.\n")

        threading.Thread(target=_worker, daemon=True).start()

    # ─── Test All ────────────────────────────────────────

    def _test_all(self):
        selected = self._get_selected_machines()
        if not selected:
            self._log("⚠️ Tidak ada mesin yang dipilih.")
            return

        self._set_buttons_loading(True)
        self._log("─" * 45)
        self._log(f"🔌 Test koneksi {len(selected)} mesin...")

        for name in selected:
            self._machine_cards[name].set_status(ConnectionStatus.CONNECTING, "Testing...")

        def _worker():
            def on_test(name, success, msg):
                if name not in selected:
                    return
                status = ConnectionStatus.CONNECTED if success else ConnectionStatus.ERROR
                short = "OK" if success else msg.split("\n")[0][:40]
                self.after(0, lambda n=name, s=status, m=short: (
                    self._machine_cards[n].set_status(s, m)
                ))
                icon = "✅" if success else "❌"
                self._log(f"  {icon} {name}: {short}")

            self._manager.test_all_connections(progress_callback=on_test)
            self.after(0, lambda: self._set_buttons_loading(False))
            self._log("🔌 Test selesai.\n")

        threading.Thread(target=_worker, daemon=True).start()

    # ─── Fetch Data (with date range + machine selection) ─

    def _fetch_data(self):
        selected = self._get_selected_machines()
        if not selected:
            self._log("⚠️ Tidak ada mesin yang dipilih. Centang minimal 1 mesin.")
            return

        # Validasi tanggal
        start_tuple, end_tuple, err = self._parse_dates()
        if err:
            self._log(f"⚠️ {err}")
            return

        start_str = self.start_date_entry.get().strip()
        end_str = self.end_date_entry.get().strip()

        self._set_buttons_loading(True)
        self._log("─" * 45)
        self._log(
            f"📥 Tarik data: {start_str} s/d {end_str} "
            f"dari {len(selected)} mesin..."
        )

        for name in selected:
            self._machine_cards[name].set_status(ConnectionStatus.FETCHING, "Menarik data...")

        def _worker():
            def on_progress(name, status_msg, count):
                self.after(0, lambda n=name, m=status_msg: (
                    self._machine_cards[n].set_status(ConnectionStatus.FETCHING, m)
                ))
                self._log(f"  [{name}] {status_msg} ({count} records)")

            results = self._manager.fetch_all_attendance(
                progress_callback=on_progress,
                selected_machines=selected,
                start_date=start_tuple,
                end_date=end_tuple,
            )

            # Proses hasil
            all_records = []
            success_count = 0
            fail_count = 0

            for result in results:
                if result.success:
                    success_count += 1
                    all_records.extend(result.records)
                    self.after(0, lambda n=result.machine_name, c=len(result.records): (
                        self._machine_cards[n].set_status(
                            ConnectionStatus.CONNECTED, f"✅ {c} records"
                        )
                    ))
                else:
                    fail_count += 1
                    short_err = result.message.split("\n")[0][:50]
                    self.after(0, lambda n=result.machine_name, m=short_err: (
                        self._machine_cards[n].set_status(ConnectionStatus.ERROR, m)
                    ))

            # Summary
            self._log(f"\n{'═' * 45}")
            self._log(
                f"📊 HASIL: {success_count} berhasil, {fail_count} gagal | "
                f"Total: {len(all_records)} records"
            )
            self._log(f"{'═' * 45}\n")

            if all_records:
                self.after(0, lambda: self._on_data_received(all_records))

            self.after(0, lambda: self._set_buttons_loading(False))

        threading.Thread(target=_worker, daemon=True).start()
