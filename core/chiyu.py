"""
Handler koneksi mesin Chiyu (BF-660C dan sejenisnya).
Mesin Chiyu menggunakan Web CGI interface di port 80.
Data diambil via HTTP GET ke endpoint if.cgi dengan parsing HTML table.

Referensi endpoint:
- Homepage: http://<IP>/
- Access Log: http://<IP>/if.cgi?redirect=AccLog.htm&failure=fail.htm&type=go_log_page&page=0
- Search Log: http://<IP>/if.cgi?redirect=UserLog.htm&failure=fail.htm&type=search_user_log&...
"""
import logging
import time
import re
from datetime import datetime
from typing import Optional

import requests
from bs4 import BeautifulSoup

from config import MachineConfig, CONNECTION_TIMEOUT, READ_TIMEOUT, MAX_RETRIES, RETRY_DELAY
from core.machine import BaseMachine, AttendanceRecord, ConnectionStatus

logger = logging.getLogger(__name__)


class ChiyuMachine(BaseMachine):
    """
    Koneksi ke mesin Chiyu via HTTP CGI web interface.
    Mesin Chiyu meng-expose data access log via halaman web (port 80).
    """

    def __init__(self, config: MachineConfig):
        super().__init__(config)
        self._session: Optional[requests.Session] = None
        self._base_url = f"http://{config.ip}:{config.port}"

    def _create_session(self) -> requests.Session:
        """Buat HTTP session dengan header yang sesuai."""
        session = requests.Session()
        session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Connection": "keep-alive",
        })
        return session

    def connect(self) -> tuple[bool, str]:
        """
        Connect ke mesin Chiyu (buka session HTTP dan verifikasi aksesibilitas).
        Jika mesin memerlukan login, gunakan username/password dari config.
        """
        self.status = ConnectionStatus.CONNECTING

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                logger.info(
                    f"[{self.name}] Attempt {attempt}/{MAX_RETRIES} "
                    f"connecting to {self._base_url}..."
                )

                self._session = self._create_session()

                # Test akses homepage
                response = self._session.get(
                    self._base_url,
                    timeout=CONNECTION_TIMEOUT,
                )
                response.raise_for_status()

                if len(response.text) < 100:
                    raise ConnectionError("Response terlalu pendek, mesin mungkin tidak aktif")

                # Cek apakah ada form login
                if self._needs_login(response.text):
                    login_ok = self._do_login()
                    if not login_ok:
                        raise ConnectionError("Login gagal (username/password salah?)")

                # Cek apakah ini halaman Chiyu yang valid
                content = response.text.lower()
                if "chiyu" in content or "bf-" in content or "access log" in content or "terminal" in content:
                    self.status = ConnectionStatus.CONNECTED
                    msg = (
                        f"Terhubung ke {self.name}\n"
                        f"  URL: {self._base_url}\n"
                        f"  Status: HTTP {response.status_code}\n"
                        f"  Content: {len(response.text)} bytes"
                    )
                    logger.info(f"[{self.name}] ✅ Connected via HTTP")
                    return True, msg
                else:
                    # Tetap dianggap berhasil jika HTTP 200
                    self.status = ConnectionStatus.CONNECTED
                    msg = (
                        f"Terhubung ke {self.name}\n"
                        f"  URL: {self._base_url}\n"
                        f"  Note: Halaman valid tapi signature Chiyu tidak ditemukan"
                    )
                    return True, msg

            except requests.exceptions.ConnectTimeout:
                self._last_error = f"Connection timeout ({CONNECTION_TIMEOUT}s)"
                logger.warning(f"[{self.name}] Attempt {attempt}: timeout")

            except requests.exceptions.ConnectionError as e:
                self._last_error = f"Connection refused: {e}"
                logger.warning(f"[{self.name}] Attempt {attempt}: connection error")

            except Exception as e:
                self._last_error = str(e)
                logger.warning(f"[{self.name}] Attempt {attempt}: {e}")

            # Cleanup sebelum retry
            self._session = None
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY)

        # Semua attempt gagal
        self.status = ConnectionStatus.ERROR
        error_msg = (
            f"Gagal terhubung ke {self.name} ({self._base_url})\n"
            f"  Percobaan: {MAX_RETRIES}x\n"
            f"  Error terakhir: {self._last_error}\n"
            f"\n"
            f"  Checklist:\n"
            f"  • Pastikan mesin Chiyu menyala\n"
            f"  • Buka {self._base_url} di browser untuk verifikasi\n"
            f"  • Pastikan port 80 tidak diblokir firewall\n"
            f"  • Cek kabel LAN ke mesin"
        )
        return False, error_msg

    def disconnect(self):
        """Tutup HTTP session."""
        if self._session:
            try:
                self._session.close()
            except Exception:
                pass
            self._session = None
        self.status = ConnectionStatus.DISCONNECTED
        logger.info(f"[{self.name}] Session closed")

    def _needs_login(self, html: str) -> bool:
        """Cek apakah halaman mengandung form login."""
        lower = html.lower()
        return (
            'type="password"' in lower
            or 'name="password"' in lower
            or 'name="pass"' in lower
        )

    def _do_login(self) -> bool:
        """
        Login ke mesin Chiyu menggunakan username/password dari config.
        Chiyu biasanya menggunakan HTTP Basic Auth atau form POST.
        """
        username = self.config.username or "admin"
        password = self.config.web_password or "admin"

        try:
            # Metode 1: HTTP Basic Auth
            self._session.auth = (username, password)
            response = self._session.get(self._base_url, timeout=CONNECTION_TIMEOUT)

            if response.status_code == 200 and len(response.text) > 200:
                logger.info(f"[{self.name}] Login via Basic Auth berhasil")
                return True

            # Metode 2: Form POST login
            self._session.auth = None
            login_data = {
                "username": username,
                "password": password,
                "user": username,
                "pass": password,
                "submit": "Login",
            }

            # Coba beberapa endpoint login umum Chiyu
            login_urls = [
                f"{self._base_url}/login.cgi",
                f"{self._base_url}/if.cgi",
                f"{self._base_url}/",
            ]

            for login_url in login_urls:
                try:
                    resp = self._session.post(
                        login_url, data=login_data, timeout=CONNECTION_TIMEOUT
                    )
                    if resp.status_code == 200:
                        logger.info(f"[{self.name}] Login via POST ke {login_url}")
                        return True
                except Exception:
                    continue

            logger.warning(f"[{self.name}] Login gagal dengan semua metode")
            return False

        except Exception as e:
            logger.error(f"[{self.name}] Login error: {e}")
            return False

    def test_connection(self) -> tuple[bool, str]:
        """Test koneksi HTTP ke mesin Chiyu."""
        success, msg = self.connect()
        if success:
            self.disconnect()
        return success, msg

    def get_attendance_logs(self) -> tuple[list[AttendanceRecord], str]:
        """
        Tarik semua data attendance dari mesin Chiyu via HTTP.
        Endpoint: if.cgi?redirect=AccLog.htm&type=go_log_page&page=N
        Data di-parse dari HTML table per halaman (20 records/page).
        """
        if not self._session:
            success, msg = self.connect()
            if not success:
                return [], msg

        self.status = ConnectionStatus.FETCHING
        all_records = []
        page = 0
        max_pages = 5000  # Safety limit (20 rec/page * 5000 = 100k max)

        try:
            while page <= max_pages:
                # Request halaman
                url = f"{self._base_url}/if.cgi"
                params = {
                    "redirect": "AccLog.htm",
                    "failure": "fail.htm",
                    "type": "go_log_page",
                    "page": str(page),
                }

                response = self._session.get(url, params=params, timeout=READ_TIMEOUT)
                response.raise_for_status()

                # Parse halaman
                page_records, total_str, has_next = self._parse_access_log_page(
                    response.text
                )

                if not page_records:
                    if page == 0:
                        logger.warning(f"[{self.name}] Tidak ada data di halaman pertama")
                    break

                all_records.extend(page_records)

                logger.info(
                    f"[{self.name}] Page {page}: {len(page_records)} records "
                    f"(total so far: {len(all_records)})"
                )

                if not has_next:
                    break

                page += 1
                # Kecilkan beban ke mesin
                time.sleep(0.3)

            self.status = ConnectionStatus.CONNECTED
            msg = f"[{self.name}] Berhasil: {len(all_records)} record dari {page + 1} halaman"
            logger.info(msg)
            return all_records, msg

        except requests.exceptions.Timeout:
            self.status = ConnectionStatus.ERROR
            self._last_error = "Read timeout saat mengambil data"
            return all_records, f"[{self.name}] Timeout setelah {len(all_records)} record"

        except Exception as e:
            self.status = ConnectionStatus.ERROR
            self._last_error = str(e)
            error_msg = f"[{self.name}] Error: {str(e)}"
            logger.error(error_msg, exc_info=True)
            # Kembalikan data yang sudah berhasil diambil
            if all_records:
                return all_records, f"{error_msg} (partial: {len(all_records)} records)"
            return [], error_msg

        finally:
            self.disconnect()

    def get_attendance_by_date(
        self, start_month: int, start_day: int, start_year: int,
        end_month: int, end_day: int, end_year: int
    ) -> tuple[list[AttendanceRecord], str]:
        """
        Tarik data attendance dengan filter tanggal menggunakan form search.
        Endpoint: if.cgi?redirect=UserLog.htm&type=search_user_log&...
        
        PENTING: Endpoint search Chiyu mengembalikan SEMUA records yang cocok
        dalam 1 response (tidak ada pagination). Jadi cukup 1 request.

        Args:
            start_month, start_day, start_year: Tanggal mulai
            end_month, end_day, end_year: Tanggal akhir
            (year format: 2 digit, misal 26 untuk 2026)
        """
        if not self._session:
            success, msg = self.connect()
            if not success:
                return [], msg

        self.status = ConnectionStatus.FETCHING

        try:
            url = f"{self._base_url}/if.cgi"
            params = {
                "redirect": "UserLog.htm",
                "failure": "fail.htm",
                "type": "search_user_log",
                "UID": "",       # Kosong = semua user
                "TID": "",       # Kosong = semua terminal
                "dep": "0",      # All departments
                "Fkey": "255",   # All function keys
                "num": "0",      # No number filter
                "start_month": str(start_month),
                "start_date": str(start_day),
                "start_year": str(start_year),
                "end_month": str(end_month),
                "end_date": str(end_day),
                "end_year": str(end_year),
                "search.x": "0",
                "search.y": "0",
            }

            logger.info(
                f"[{self.name}] Search: {start_month}/{start_day}/20{start_year} "
                f"- {end_month}/{end_day}/20{end_year}"
            )

            # Timeout lebih panjang karena mesin memproses query besar
            response = self._session.get(url, params=params, timeout=READ_TIMEOUT * 3)
            response.raise_for_status()

            logger.info(
                f"[{self.name}] Search response: {len(response.text)} bytes"
            )

            # Parse semua records dari response
            records, total_str, _ = self._parse_access_log_page(response.text)

            self.status = ConnectionStatus.CONNECTED
            msg = (
                f"[{self.name}] Search berhasil: {len(records)} record "
                f"({total_str})"
            )
            logger.info(msg)
            return records, msg

        except requests.exceptions.Timeout:
            self.status = ConnectionStatus.ERROR
            self._last_error = "Search timeout (mesin terlalu lama memproses)"
            return [], f"[{self.name}] Search timeout - coba perkecil rentang tanggal"

        except Exception as e:
            self.status = ConnectionStatus.ERROR
            self._last_error = str(e)
            return [], f"[{self.name}] Search error: {str(e)}"

        finally:
            self.disconnect()

    def _parse_access_log_page(
        self, html: str
    ) -> tuple[list[AttendanceRecord], str, bool]:
        """
        Parse halaman HTML Access Log mesin Chiyu.
        Robust parser yang tidak kehilangan data.

        Returns:
            (records, total_info_string, has_next_page)
        """
        records = []
        total_str = ""
        has_next = False

        try:
            soup = BeautifulSoup(html, "html.parser")

            # Cari total records info
            total_match = re.search(r"Total\s+(\d+)\s+Record", html, re.IGNORECASE)
            if total_match:
                total_str = total_match.group(0)

            # Cek apakah ada halaman berikutnya
            if "Next" in html and "go_log_page" in html:
                has_next = True

            # Cek apakah ini "End of List" (tidak ada halaman lagi)
            if "End of List" in html:
                has_next = False

            # ─── Parse data rows ──────────────────────────────
            # Chiyu menggunakan TR dengan bgcolor untuk data rows.
            # Pattern: <tr bgcolor='#999F9F'> atau <tr bgcolor='#99CFCF'>
            # Ini cara paling reliable untuk mendapatkan SEMUA data row
            # tanpa kehilangan satupun.
            data_rows = soup.find_all("tr", bgcolor=True)

            for row in data_rows:
                cols = row.find_all("td")
                if len(cols) < 5:
                    continue

                col_texts = [col.get_text(strip=True) for col in cols]

                # Skip jika row ini adalah navigation/pagination row
                joined = " ".join(col_texts).lower()
                if "total" in joined and "record" in joined:
                    continue
                if "first" in joined and "end" in joined and "prev" in joined:
                    continue

                try:
                    # Mapping kolom Chiyu:
                    # [0] No, [1] Card ID, [2] Employee ID, [3] Name,
                    # [4] Date, [5] Time, [6] Terminal, [7] IN/OUT, [8] Door

                    # No. column — bisa "1 ." atau "1." atau "1"
                    # Skip jika kolom 0 bukan angka (cleanup spasi & titik)
                    no_clean = col_texts[0].replace(".", "").strip()
                    if not no_clean.isdigit():
                        continue

                    # Card ID (mungkin di dalam <a> tag)
                    card_id_elem = cols[1].find("a")
                    card_id = card_id_elem.get_text(strip=True) if card_id_elem else col_texts[1]
                    card_id = card_id.strip()

                    employee_id = col_texts[2].strip() if len(col_texts) > 2 else ""
                    name_raw = col_texts[3].strip() if len(col_texts) > 3 else ""
                    date_str = col_texts[4].strip() if len(col_texts) > 4 else ""
                    time_str = col_texts[5].strip() if len(col_texts) > 5 else ""
                    terminal = col_texts[6].strip() if len(col_texts) > 6 else ""
                    in_out = col_texts[7].strip() if len(col_texts) > 7 else ""
                    door = col_texts[8].strip() if len(col_texts) > 8 else ""

                    # Validasi minimal: harus ada identitas dan tanggal
                    if not card_id and not employee_id:
                        continue
                    if not date_str or "/" not in date_str:
                        continue

                    # Parse datetime (format: MM/DD/YYYY HH:MM:SS)
                    timestamp = None
                    if time_str:
                        try:
                            timestamp = datetime.strptime(
                                f"{date_str} {time_str}", "%m/%d/%Y %H:%M:%S"
                            )
                        except ValueError:
                            pass

                    if not timestamp:
                        try:
                            timestamp = datetime.strptime(date_str, "%m/%d/%Y")
                        except ValueError:
                            continue

                    # Parse status IN/OUT
                    status = self._parse_in_out_status(in_out)

                    # User ID: prefer employee_id, fallback card_id
                    user_id = employee_id if employee_id and employee_id != "----" else card_id

                    # Name: gunakan raw jika valid
                    name = name_raw if name_raw and name_raw != "----, ----" else f"ID-{user_id}"

                    record = AttendanceRecord(
                        user_id=user_id,
                        name=name,
                        timestamp=timestamp,
                        status=status,
                        punch=2,  # Chiyu: card-based
                        machine_name=self.name,
                        card_id=card_id,
                        department="",
                        door=door,
                    )
                    records.append(record)

                except (IndexError, ValueError) as e:
                    logger.debug(f"[{self.name}] Skip row: {e}")
                    continue

        except Exception as e:
            logger.error(f"[{self.name}] HTML parse error: {e}", exc_info=True)

        return records, total_str, has_next

    @staticmethod
    def _parse_in_out_status(in_out_str: str) -> int:
        """
        Parse string IN/OUT dari Chiyu ke status code.
        Chiyu format: "IN/IN", "OUT/OUT", "UNAUTHORIZED/IN", dll.
        """
        if not in_out_str:
            return 0

        upper = in_out_str.upper()

        if "OUT" in upper and "IN" not in upper.replace("UNAUTHORIZED", ""):
            return 1  # Check-Out
        else:
            return 0  # Check-In (default)
