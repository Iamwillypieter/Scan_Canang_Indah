"""
Frame untuk menampilkan data attendance dalam format First IN / Last OUT.
Dengan filter: Date Range, Card ID, Employee ID.
"""
from datetime import date
from typing import Optional

import customtkinter as ctk

from core.machine import AttendanceRecord
from core.data_processor import DataProcessor, DailySummaryRecord


class DataViewFrame(ctk.CTkFrame):
    """Frame tabel data dengan grouping First IN / Last OUT."""

    def __init__(self, parent):
        super().__init__(parent, fg_color="transparent")
        self._records: list[AttendanceRecord] = []
        self._summaries: list[DailySummaryRecord] = []

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        self._build_ui()

    def _build_ui(self):
        # ─── Filter Section ───────────────────────────────
        filter_frame = ctk.CTkFrame(self)
        filter_frame.grid(row=0, column=0, sticky="ew", pady=(0, 8))

        ctk.CTkLabel(
            filter_frame,
            text="Filter & Proses Data",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).grid(row=0, column=0, columnspan=10, pady=(12, 8), padx=15, sticky="w")

        # Row 1: Date Range
        ctk.CTkLabel(filter_frame, text="Start Date:").grid(
            row=1, column=0, padx=(15, 5), pady=6, sticky="w"
        )
        self.from_date_entry = ctk.CTkEntry(
            filter_frame, placeholder_text="YYYY-MM-DD", width=115
        )
        self.from_date_entry.grid(row=1, column=1, padx=3, pady=6)

        ctk.CTkLabel(filter_frame, text="End Date:").grid(
            row=1, column=2, padx=(10, 5), pady=6, sticky="w"
        )
        self.to_date_entry = ctk.CTkEntry(
            filter_frame, placeholder_text="YYYY-MM-DD", width=115
        )
        self.to_date_entry.grid(row=1, column=3, padx=3, pady=6)

        # Card ID filter
        ctk.CTkLabel(filter_frame, text="Card ID:").grid(
            row=1, column=4, padx=(10, 5), pady=6, sticky="w"
        )
        self.card_id_entry = ctk.CTkEntry(
            filter_frame, placeholder_text="(opsional)", width=120
        )
        self.card_id_entry.grid(row=1, column=5, padx=3, pady=6)

        # Employee ID filter
        ctk.CTkLabel(filter_frame, text="Employee ID:").grid(
            row=1, column=6, padx=(10, 5), pady=6, sticky="w"
        )
        self.emp_id_entry = ctk.CTkEntry(
            filter_frame, placeholder_text="(opsional)", width=120
        )
        self.emp_id_entry.grid(row=1, column=7, padx=3, pady=6)

        # Buttons
        self.btn_filter = ctk.CTkButton(
            filter_frame,
            text="🔍 Proses",
            command=self._apply_filter,
            width=90,
            height=32,
            fg_color="#059669",
            hover_color="#047857",
        )
        self.btn_filter.grid(row=1, column=8, padx=8, pady=6)

        self.btn_reset = ctk.CTkButton(
            filter_frame,
            text="↩️ Reset",
            command=self._reset_filter,
            width=75,
            height=32,
            fg_color="#6B7280",
            hover_color="#4B5563",
        )
        self.btn_reset.grid(row=1, column=9, padx=(0, 15), pady=6)

        # ─── Statistics ───────────────────────────────────
        self.stats_label = ctk.CTkLabel(
            self,
            text="Belum ada data. Tarik data dari tab Koneksi, lalu klik 'Proses'.",
            font=ctk.CTkFont(size=11),
            text_color="gray",
        )
        self.stats_label.grid(row=1, column=0, sticky="w", pady=(4, 4))

        # ─── Data Table ──────────────────────────────────
        self.table_textbox = ctk.CTkTextbox(
            self,
            font=ctk.CTkFont(family="Consolas", size=10),
            state="disabled",
            wrap="none",
        )
        self.table_textbox.grid(row=2, column=0, sticky="nsew")

    def load_data(self, records: list[AttendanceRecord]):
        """Load raw data dari mesin. Auto-proses First IN / Last OUT."""
        self._records = records
        self._apply_filter()

    def get_summaries(self) -> list[DailySummaryRecord]:
        """Get current processed summaries (untuk export)."""
        return self._summaries

    def get_filtered_records(self) -> Optional[list[AttendanceRecord]]:
        """Backward compat: return raw filtered records."""
        return self._records

    def _apply_filter(self):
        """Terapkan filter lalu proses First IN / Last OUT."""
        if not self._records:
            return

        # 1. Filter berdasarkan tanggal
        from_date = self._parse_date(self.from_date_entry.get().strip())
        to_date = self._parse_date(self.to_date_entry.get().strip())

        processor = DataProcessor(self._records)
        filtered = processor.filter_by_date(from_date, to_date)

        # 2. Filter berdasarkan Card ID
        card_id = self.card_id_entry.get().strip()
        if card_id:
            filtered = processor.filter_by_card_id(card_id, filtered)

        # 3. Filter berdasarkan Employee ID
        emp_id = self.emp_id_entry.get().strip()
        if emp_id:
            filtered = processor.filter_by_employee_id(emp_id, filtered)

        # 4. Group First IN / Last OUT
        self._summaries = DataProcessor.group_first_in_last_out(filtered)

        # 5. Display
        self._display_summaries(self._summaries, len(filtered))

    def _reset_filter(self):
        """Reset semua filter dan proses ulang."""
        self.from_date_entry.delete(0, "end")
        self.to_date_entry.delete(0, "end")
        self.card_id_entry.delete(0, "end")
        self.emp_id_entry.delete(0, "end")
        self._apply_filter()

    def _parse_date(self, date_str: str) -> Optional[date]:
        """Parse tanggal flexibel: YYYY-MM-DD atau YYYY-M-D."""
        if not date_str:
            return None
        try:
            # Split by dash and parse integers (handles both 2026-06-01 and 2026-6-1)
            parts = date_str.strip().split("-")
            if len(parts) == 3:
                return date(int(parts[0]), int(parts[1]), int(parts[2]))
        except (ValueError, IndexError):
            pass
        return None

    def _display_summaries(self, summaries: list[DailySummaryRecord], raw_count: int):
        """Render tabel First IN / Last OUT."""
        # Stats
        unique_users = len(set(s.employee_id for s in summaries))
        unique_dates = len(set(s.date for s in summaries))

        self.stats_label.configure(
            text=(
                f"📊 Raw: {raw_count} log | "
                f"Grouped: {len(summaries)} baris | "
                f"👤 {unique_users} karyawan | "
                f"📅 {unique_dates} hari"
            ),
            text_color=("gray10", "gray90"),
        )

        # Build table header sesuai spesifikasi
        header = (
            f"{'No.':<5}"
            f"{'Card ID':<14}"
            f"{'Emp.ID':<8}"
            f"{'Name':<20}"
            f"{'Dept.':<8}"
            f"{'Date':<12}"
            f"{'First IN':<10}"
            f"{'Last OUT':<10}"
            f"{'Terminal(First)':<22}"
            f"{'Terminal(Last)':<22}"
            f"{'Door(First)':<13}"
            f"{'Door(Last)':<13}"
        )
        separator = "─" * 157

        lines = [header, separator]

        for s in summaries:
            line = (
                f"{s.no:<5}"
                f"{s.card_id[:12]:<14}"
                f"{s.employee_id[:6]:<8}"
                f"{s.name[:18]:<20}"
                f"{s.department[:6]:<8}"
                f"{s.date_str:<12}"
                f"{s.first_in_str:<10}"
                f"{s.last_out_str:<10}"
                f"{s.terminal_first[:20]:<22}"
                f"{s.terminal_last[:20]:<22}"
                f"{s.door_first[:11]:<13}"
                f"{s.door_last[:11]:<13}"
            )
            lines.append(line)

        self.table_textbox.configure(state="normal")
        self.table_textbox.delete("1.0", "end")
        self.table_textbox.insert("1.0", "\n".join(lines))
        self.table_textbox.configure(state="disabled")
