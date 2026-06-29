import customtkinter as ctk

from config import APP_NAME, APP_VERSION, WINDOW_WIDTH, WINDOW_HEIGHT, APP_MODE, IS_DEVELOPMENT
from ui.frames.connection_frame import ConnectionFrame
from ui.frames.data_frame import DataViewFrame
from ui.frames.export_frame import ExportFrame


class App(ctk.CTk):
    """Window utama aplikasi multi-device."""

    def __init__(self):
        super().__init__()

        # ─── Window Setup ─────────────────────────────────
        self.title(f"{APP_NAME} v{APP_VERSION}")
        self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.minsize(900, 600)

        # Theme
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # ─── Shared State ─────────────────────────────────
        self._records = []

        # ─── Layout ───────────────────────────────────────
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._create_header()

        # Tab View
        self.tabview = ctk.CTkTabview(self, anchor="nw")
        self.tabview.grid(row=1, column=0, padx=15, pady=(0, 15), sticky="nsew")

        # Tab 1: Multi-device Connection
        tab_conn = self.tabview.add("🔌 Koneksi (5 Mesin)")
        tab_conn.grid_columnconfigure(0, weight=1)
        tab_conn.grid_rowconfigure(0, weight=1)

        self.connection_frame = ConnectionFrame(
            tab_conn, on_data_received=self._on_data_received
        )
        self.connection_frame.grid(row=0, column=0, sticky="nsew")

        # Tab 2: Data View & Filter
        tab_data = self.tabview.add("📊 Data")
        tab_data.grid_columnconfigure(0, weight=1)
        tab_data.grid_rowconfigure(0, weight=1)

        self.data_frame = DataViewFrame(tab_data)
        self.data_frame.grid(row=0, column=0, sticky="nsew")

        # Tab 3: Export
        tab_export = self.tabview.add("💾 Export")
        tab_export.grid_columnconfigure(0, weight=1)
        tab_export.grid_rowconfigure(0, weight=1)

        self.export_frame = ExportFrame(
            tab_export, get_summaries=self._get_summaries
        )
        self.export_frame.grid(row=0, column=0, sticky="nsew")

        # Status Bar
        self._create_statusbar()

    def _create_header(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, padx=15, pady=(15, 5), sticky="ew")

        ctk.CTkLabel(
            header,
            text=f"🖐️ {APP_NAME}",
            font=ctk.CTkFont(size=22, weight="bold"),
        ).pack(side="left")

        ctk.CTkLabel(
            header,
            text=f"v{APP_VERSION} • Multi-Device (Biotronix + Chiyu)",
            font=ctk.CTkFont(size=11),
            text_color="gray",
        ).pack(side="left", padx=(10, 0), pady=(5, 0))

        # Mode badge
        if IS_DEVELOPMENT:
            ctk.CTkLabel(
                header,
                text="🛠️ DEV MODE",
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color="#F59E0B",
                fg_color="#292524",
                corner_radius=6,
                padx=8,
                pady=2,
            ).pack(side="left", padx=(12, 0), pady=(4, 0))

    def _create_statusbar(self):
        statusbar_frame = ctk.CTkFrame(self, fg_color="transparent")
        statusbar_frame.grid(row=2, column=0, padx=15, pady=(0, 10), sticky="ew")
        statusbar_frame.grid_columnconfigure(0, weight=1)

        self.statusbar = ctk.CTkLabel(
            statusbar_frame,
            text="Siap. Klik 'Ping Semua' untuk cek jaringan atau 'Tarik Data' untuk mulai.",
            font=ctk.CTkFont(size=11),
            text_color="gray",
            anchor="w",
        )
        self.statusbar.grid(row=0, column=0, sticky="ew")

        # Footer credit — centered
        ctk.CTkLabel(
            statusbar_frame,
            text="© 2026 · Crafted by Willy Pieter Julius Situmorang",
            font=ctk.CTkFont(size=10),
            text_color="#6B7280",
            anchor="center",
        ).grid(row=1, column=0, pady=(6, 0), sticky="ew")

    def _on_data_received(self, records: list):
        """Callback saat data diterima dari multi-device fetch."""
        self._records = records
        self.data_frame.load_data(records)

        machines = set(r.machine_name for r in records if r.machine_name)
        self.statusbar.configure(
            text=f"✅ {len(records)} record dari {len(machines)} mesin dimuat. Lihat tab Data."
        )
        self.tabview.set("📊 Data")

    def _get_summaries(self) -> list:
        """Getter untuk summaries (First IN / Last OUT) dari data frame."""
        return self.data_frame.get_summaries()

    def _get_current_records(self) -> list:
        filtered = self.data_frame.get_filtered_records()
        return filtered if filtered is not None else self._records
