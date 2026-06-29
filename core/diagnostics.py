import logging
import socket
import subprocess
import platform
from dataclasses import dataclass

from config import MachineConfig, MachineType, PING_TIMEOUT, CONNECTION_TIMEOUT

logger = logging.getLogger(__name__)


@dataclass
class DiagnosticResult:
    step: str
    passed: bool
    message: str
    suggestion: str = ""


def run_diagnostics(config: MachineConfig) -> list[DiagnosticResult]:
    results = []

    # ─── Step 1: Ping ─────────────────────────────────────
    results.append(_check_ping(config.ip))

    # ─── Step 2: Port Open ────────────────────────────────
    results.append(_check_port(config.ip, config.port))

    # ─── Step 3: Protocol Response ────────────────────────
    if config.machine_type == MachineType.CHIYU:
        results.append(_check_http_response(config.ip, config.port))
    else:
        results.append(_check_tcp_response(config.ip, config.port))

    # ─── Step 4: ARP Check (IP Conflict) ──────────────────
    results.append(_check_arp(config.ip))

    return results


def _check_ping(ip: str) -> DiagnosticResult:
    """Step 1: Ping host."""
    try:
        param = "-n" if platform.system().lower() == "windows" else "-c"
        timeout_param = "-w" if platform.system().lower() == "windows" else "-W"
        timeout_val = str(PING_TIMEOUT * 1000) if platform.system().lower() == "windows" else str(PING_TIMEOUT)

        result = subprocess.run(
            ["ping", param, "1", timeout_param, timeout_val, ip],
            capture_output=True,
            text=True,
            timeout=PING_TIMEOUT + 2,
        )

        if result.returncode == 0:
            return DiagnosticResult(
                step="Ping Host",
                passed=True,
                message=f"Host {ip} merespons ping",
            )
        else:
            return DiagnosticResult(
                step="Ping Host",
                passed=False,
                message=f"Host {ip} TIDAK merespons ping",
                suggestion=(
                    "• Pastikan mesin menyala dan kabel LAN terpasang\n"
                    "• Cek apakah mesin dan PC ada di subnet yang sama\n"
                    "• Beberapa mesin disable ICMP — lanjut ke step berikutnya"
                ),
            )
    except Exception as e:
        return DiagnosticResult(
            step="Ping Host",
            passed=False,
            message=f"Error ping: {e}",
            suggestion="• Pastikan command 'ping' tersedia di sistem",
        )


def _check_port(ip: str, port: int) -> DiagnosticResult:
    """Step 2: TCP port reachability."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(CONNECTION_TIMEOUT)
        result = sock.connect_ex((ip, port))
        sock.close()

        if result == 0:
            return DiagnosticResult(
                step=f"Port {port} Open",
                passed=True,
                message=f"Port {port} di {ip} OPEN (accepting connections)",
            )
        else:
            return DiagnosticResult(
                step=f"Port {port} Open",
                passed=False,
                message=f"Port {port} di {ip} CLOSED/FILTERED (error code: {result})",
                suggestion=(
                    f"• Port {port} tidak bisa diakses\n"
                    f"• Cek firewall Windows: matikan sementara untuk test\n"
                    f"• Pastikan port benar (Biotronix: 4370, Chiyu: 80)\n"
                    f"• Coba dari browser: http://{ip}:{port}/ (untuk Chiyu)"
                ),
            )
    except socket.timeout:
        return DiagnosticResult(
            step=f"Port {port} Open",
            passed=False,
            message=f"Timeout saat cek port {port} ({CONNECTION_TIMEOUT}s)",
            suggestion=(
                "• Koneksi sangat lambat atau port diblokir\n"
                "• Cek switch/router antara PC dan mesin"
            ),
        )
    except Exception as e:
        return DiagnosticResult(
            step=f"Port {port} Open",
            passed=False,
            message=f"Error cek port: {e}",
        )


def _check_http_response(ip: str, port: int) -> DiagnosticResult:
    """Step 3 (Chiyu): Cek HTTP response."""
    try:
        import requests

        url = f"http://{ip}:{port}/"
        response = requests.get(url, timeout=CONNECTION_TIMEOUT)

        if response.status_code == 200:
            content_preview = response.text[:200].strip()
            return DiagnosticResult(
                step="HTTP Response",
                passed=True,
                message=(
                    f"HTTP 200 OK ({len(response.text)} bytes)\n"
                    f"Preview: {content_preview[:100]}..."
                ),
            )
        else:
            return DiagnosticResult(
                step="HTTP Response",
                passed=False,
                message=f"HTTP {response.status_code}",
                suggestion="• Mesin merespons tapi bukan status 200",
            )
    except Exception as e:
        return DiagnosticResult(
            step="HTTP Response",
            passed=False,
            message=f"HTTP request gagal: {e}",
            suggestion=(
                f"• Buka http://{ip}:{port}/ di browser untuk verifikasi\n"
                "• Jika browser juga gagal, masalah di jaringan/mesin"
            ),
        )


def _check_tcp_response(ip: str, port: int) -> DiagnosticResult:
    """Step 3 (Biotronix): Cek TCP handshake ZKTeco."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(CONNECTION_TIMEOUT)
        sock.connect((ip, port))
        sock.close()

        return DiagnosticResult(
            step="TCP Handshake",
            passed=True,
            message=f"TCP connection ke {ip}:{port} berhasil (socket established)",
        )
    except socket.timeout:
        return DiagnosticResult(
            step="TCP Handshake",
            passed=False,
            message="TCP handshake timeout",
            suggestion=(
                "• Mesin mungkin sibuk atau port salah\n"
                "• Restart mesin fingerprint\n"
                "• Pastikan tidak ada software lain yang konek ke mesin"
            ),
        )
    except ConnectionRefusedError:
        return DiagnosticResult(
            step="TCP Handshake",
            passed=False,
            message="Connection refused — port tertutup aktif",
            suggestion=(
                f"• Port {port} aktif menolak koneksi\n"
                "• Kemungkinan port salah atau mesin dalam mode maintenance\n"
                "• Cek setting Communication di panel mesin"
            ),
        )
    except Exception as e:
        return DiagnosticResult(
            step="TCP Handshake",
            passed=False,
            message=f"TCP error: {e}",
        )


def _check_arp(ip: str) -> DiagnosticResult:
    """Step 4: Cek ARP table untuk detect IP conflict."""
    try:
        if platform.system().lower() != "windows":
            return DiagnosticResult(
                step="ARP Check",
                passed=True,
                message="Skip (non-Windows)",
            )

        result = subprocess.run(
            ["arp", "-a", ip],
            capture_output=True,
            text=True,
            timeout=5,
        )

        output = result.stdout.strip()

        if ip in output:
            # Parse MAC address
            lines = output.split("\n")
            for line in lines:
                if ip in line:
                    return DiagnosticResult(
                        step="ARP Check",
                        passed=True,
                        message=f"ARP entry ditemukan:\n  {line.strip()}",
                    )

        return DiagnosticResult(
            step="ARP Check",
            passed=False,
            message=f"Tidak ada ARP entry untuk {ip}",
            suggestion=(
                "• IP belum pernah berkomunikasi dengan PC ini\n"
                "• Ping terlebih dahulu lalu cek ulang\n"
                "• Jika ada duplicate MAC, kemungkinan IP conflict"
            ),
        )
    except Exception as e:
        return DiagnosticResult(
            step="ARP Check",
            passed=False,
            message=f"ARP check error: {e}",
        )
