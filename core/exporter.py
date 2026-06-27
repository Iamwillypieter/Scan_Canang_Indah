"""
Module export data ke berbagai format (Excel, CSV).
Output format: First IN / Last OUT per karyawan per hari.
"""
import os
import logging
from datetime import datetime

import pandas as pd

from core.data_processor import DailySummaryRecord
from config import EXPORT_FOLDER

logger = logging.getLogger(__name__)


class DataExporter:
    """Export data attendance (First IN / Last OUT) ke file Excel atau CSV."""

    def __init__(self, summaries: list[DailySummaryRecord]):
        self._summaries = summaries

    def _to_dataframe(self) -> pd.DataFrame:
        """Konversi list DailySummaryRecord ke pandas DataFrame."""
        data = []
        for s in self._summaries:
            data.append({
                "No.": s.no,
                "Card ID": s.card_id,
                "Employee ID": s.employee_id,
                "Name": s.name,
                "Depart.": s.department,
                "Date": s.date_str,
                "First IN": s.first_in_str,
                "Last OUT": s.last_out_str,
                "Terminal(First)": s.terminal_first,
                "Terminal(Last)": s.terminal_last,
                "Door(First)": s.door_first,
                "Door(Last)": s.door_last,
            })
        return pd.DataFrame(data)

    def to_excel(self, filepath: str = "") -> str:
        """Export ke file Excel (.xlsx). Returns: filepath."""
        if not filepath:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = os.path.join(EXPORT_FOLDER, f"absensi_{timestamp}.xlsx")

        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        df = self._to_dataframe()

        with pd.ExcelWriter(filepath, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="Absensi", index=False)

            # Auto-adjust column width
            worksheet = writer.sheets["Absensi"]
            for column in worksheet.columns:
                max_length = 0
                col_letter = column[0].column_letter
                for cell in column:
                    try:
                        cell_len = len(str(cell.value))
                        if cell_len > max_length:
                            max_length = cell_len
                    except (TypeError, AttributeError):
                        pass
                worksheet.column_dimensions[col_letter].width = min(max_length + 3, 40)

        logger.info(f"Excel exported: {filepath} ({len(self._summaries)} rows)")
        return filepath

    def to_csv(self, filepath: str = "") -> str:
        """Export ke file CSV. Returns: filepath."""
        if not filepath:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filepath = os.path.join(EXPORT_FOLDER, f"absensi_{timestamp}.csv")

        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        df = self._to_dataframe()
        df.to_csv(filepath, index=False, encoding="utf-8-sig")

        logger.info(f"CSV exported: {filepath} ({len(self._summaries)} rows)")
        return filepath
