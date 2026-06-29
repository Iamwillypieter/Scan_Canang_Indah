import logging
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, date
from typing import Optional

from core.machine import AttendanceRecord

logger = logging.getLogger(__name__)


# ─── Processed Record (First IN / Last OUT) ──────────────────

@dataclass
class DailySummaryRecord:
    no: int
    card_id: str
    employee_id: str
    name: str
    department: str
    date: date
    first_in: Optional[datetime]
    last_out: Optional[datetime]
    terminal_first: str     # Nama mesin First IN
    terminal_last: str      # Nama mesin Last OUT
    door_first: str         # Door First IN
    door_last: str          # Door Last OUT

    @property
    def first_in_str(self) -> str:
        return self.first_in.strftime("%H:%M:%S") if self.first_in else "-"

    @property
    def last_out_str(self) -> str:
        return self.last_out.strftime("%H:%M:%S") if self.last_out else "-"

    @property
    def date_str(self) -> str:
        return self.date.strftime("%Y-%m-%d")


# ─── Data Processor ──────────────────────────────────────────

class DataProcessor:
    def __init__(self, records: list[AttendanceRecord]):
        self._records = records

    @property
    def total_records(self) -> int:
        return len(self._records)

    # ─── Filtering ────────────────────────────────────────

    def filter_by_date(
        self,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
    ) -> list[AttendanceRecord]:
        filtered = self._records

        if from_date:
            filtered = [r for r in filtered if r.timestamp.date() >= from_date]

        if to_date:
            filtered = [r for r in filtered if r.timestamp.date() <= to_date]

        logger.info(
            f"Filter date: {len(filtered)}/{self.total_records} records "
            f"({from_date} s/d {to_date})"
        )
        return filtered

    def filter_by_card_id(
        self, card_id: str, records: Optional[list[AttendanceRecord]] = None
    ) -> list[AttendanceRecord]:
        source = records if records is not None else self._records
        card_id_lower = card_id.strip().lower()
        return [r for r in source if card_id_lower in r.card_id.lower()]

    def filter_by_employee_id(
        self, employee_id: str, records: Optional[list[AttendanceRecord]] = None
    ) -> list[AttendanceRecord]:
        source = records if records is not None else self._records
        emp_lower = employee_id.strip().lower()
        return [r for r in source if emp_lower in r.user_id.lower()]

    # ─── Grouping: First IN / Last OUT ────────────────────

    @staticmethod
    def group_first_in_last_out(
        records: list[AttendanceRecord],
    ) -> list[DailySummaryRecord]:
        # Group by (user_id, date)
        groups: dict[tuple[str, date], list[AttendanceRecord]] = defaultdict(list)

        for r in records:
            key = (r.user_id, r.timestamp.date())
            groups[key].append(r)

        # Build summary records
        summaries = []
        counter = 0

        # Sort keys by date then user_id
        sorted_keys = sorted(groups.keys(), key=lambda k: (k[1], k[0]))

        for user_id, record_date in sorted_keys:
            group_records = groups[(user_id, record_date)]

            # Sort by timestamp ascending
            group_records.sort(key=lambda r: r.timestamp)

            first_record = group_records[0]   # Earliest
            last_record = group_records[-1]   # Latest

            counter += 1

            summary = DailySummaryRecord(
                no=counter,
                card_id=first_record.card_id or "",
                employee_id=user_id,
                name=first_record.name,
                department=first_record.department or "",
                date=record_date,
                first_in=first_record.timestamp,
                last_out=last_record.timestamp if len(group_records) > 1 else None,
                terminal_first=first_record.machine_name or "",
                terminal_last=last_record.machine_name or "" if len(group_records) > 1 else "",
                door_first=first_record.door or "",
                door_last=last_record.door or "" if len(group_records) > 1 else "",
            )
            summaries.append(summary)

        logger.info(
            f"Grouped: {len(records)} raw records → {len(summaries)} daily summaries"
        )
        return summaries

    # ─── Statistics ───────────────────────────────────────

    def get_statistics(
        self, records: Optional[list[AttendanceRecord]] = None
    ) -> dict:
        source = records if records is not None else self._records

        if not source:
            return {
                "total_records": 0,
                "unique_users": 0,
                "check_in": 0,
                "check_out": 0,
                "date_range": "N/A",
            }

        unique_users = set(r.user_id for r in source)
        check_in = sum(1 for r in source if r.status == 0)
        check_out = sum(1 for r in source if r.status == 1)
        dates = [r.timestamp.date() for r in source]

        return {
            "total_records": len(source),
            "unique_users": len(unique_users),
            "check_in": check_in,
            "check_out": check_out,
            "date_range": f"{min(dates)} s/d {max(dates)}",
        }

    # ─── Sorting ──────────────────────────────────────────

    @staticmethod
    def sort_by_timestamp(
        records: list[AttendanceRecord], ascending: bool = True
    ) -> list[AttendanceRecord]:
        return sorted(records, key=lambda r: r.timestamp, reverse=not ascending)
