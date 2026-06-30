import os
import subprocess
from typing import Callable

import customtkinter as ctk

from core.exporter import DataExporter
from config import EXPORT_FOLDER


class ExportFrame(ctk.CTkFrame):
    """Frame export data ke Excel dan CSV."""

    def __init__(self, parent, get_summaries: Callable):
        super().__init__(parent, fg_color="transparent")
        self._get_summaries = get_summaries

        self.grid_columnconfigure(0, weight=1)
        self._build_ui()

    def _build_ui(self):
        # ─── Export Options ───────────────────────────────
        export_frame = ctk.CTkFrame(self)
        export_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))

        ctk.CTkLabel(
            export_frame,
            text="Export Data Absensi (First IN / Last OUT)",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).grid(row=0, column=0, columnspan=3, pady=(15, 10), padx=15, sticky="w")

        ctk.CTkLabel(
            export_frame,
            text=(
                "Data yang diekspor adalah hasil grouping (First IN / Last OUT)\n"
                "sesuai filter yang diterapkan di tab Data."
            ),
            font=ctk.CTkFont(size=12),
            text_color="gray",
        ).grid(row=1, column=0, columnspan=3, padx=15, pady=(0, 15), sticky="w")

        # Kolom output info
        ctk.CTkLabel(
            export_frame,
            text=(
                "Kolom output: No. | Card ID | Employee ID | Name | Depart. | Date | "
                "First IN | Last OUT | Terminal(First) | Terminal(Last) | Door(First) | Door(Last)"
            ),
            font=ctk.CTkFont(family="Consolas", size=10),
            text_color="#6B7280",
        ).grid(row=2, column=0, columnspan=3, padx=15, pady=(0, 15), sticky="w")

        # Export Buttons
        self.btn_excel = ctk.CTkButton(
            export_frame,
            text="📗 Export ke Excel (.xlsx)",
            command=self._export_excel,
            width=220,
            height=45,
            fg_color="#059669",
            hover_color="#047857",
            font=ctk.CTkFont(size=13, weight="bold"),
        )
        self.btn_excel.grid(row=3, column=0, padx=15, pady=(0, 15), sticky="w")

        self.btn_csv = ctk.CTkButton(
            export_frame,
            text="📄 Export ke CSV",
            command=self._export_csv,
            width=180,
            height=45,
            fg_color="#2563EB",
            hover_color="#1D4ED8",
            font=ctk.CTkFont(size=13, weight="bold"),
        )
        self.btn_csv.grid(row=3, column=1, padx=5, pady=(0, 15), sticky="w")

        self.btn_open_folder = ctk.CTkButton(
            export_frame,
            text="📂 Buka Folder Export",
            command=self._open_folder,
            width=180,
            height=45,
            fg_color="#6B7280",
            hover_color="#4B5563",
            font=ctk.CTkFont(size=13),
        )
        self.btn_open_folder.grid(row=3, column=2, padx=5, pady=(0, 15), sticky="w")

        # ─── Result Log ──────────────────────────────────
        self.result_label = ctk.CTkLabel(
            self,
            text="",
            font=ctk.CTkFont(size=12),
            text_color="gray",
            wraplength=900,
            justify="left",
        )
        self.result_label.grid(row=1, column=0, sticky="w", padx=5, pady=10)

    def _export_excel(self):
        """Export data ke Excel."""
        summaries = self._get_summaries()
        if not summaries:
            self.result_label.configure(
                text="⚠️ Tidak ada data. Tarik data dari tab Koneksi, lalu proses di tab Data.",
                text_color="#EF4444",
            )
            return

        try:
            exporter = DataExporter(summaries)
            filepath = exporter.to_excel()
            self.result_label.configure(
                text=f"✅ Berhasil export {len(summaries)} baris ke:\n{filepath}",
                text_color="#10B981",
            )
        except Exception as e:
            self.result_label.configure(
                text=f"❌ Error export: {str(e)}",
                text_color="#EF4444",
            )

    def _export_csv(self):
        """Export data ke CSV."""
        summaries = self._get_summaries()
        if not summaries:
            self.result_label.configure(
                text="⚠️ Tidak ada data. Tarik data dari tab Koneksi, lalu proses di tab Data.",
                text_color="#EF4444",
            )
            return

        try:
            exporter = DataExporter(summaries)
            filepath = exporter.to_csv()
            self.result_label.configure(
                text=f"✅ Berhasil export {len(summaries)} baris ke:\n{filepath}",
                text_color="#10B981",
            )
        except Exception as e:
            self.result_label.configure(
                text=f"❌ Error export: {str(e)}",
                text_color="#EF4444",
            )

    def _open_folder(self):
        """Buka folder export di Windows Explorer."""
        os.makedirs(EXPORT_FOLDER, exist_ok=True)
        subprocess.Popen(f'explorer "{EXPORT_FOLDER}"')
