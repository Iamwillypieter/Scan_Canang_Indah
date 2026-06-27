# 🖐️ Absensi Reader — Multi-Device

Aplikasi desktop Windows untuk menarik data absensi dari **4 mesin fingerprint** secara paralel:
- 2× Biotronix (protokol ZKTeco TCP, port 4370)  
- 2× Chiyu BF-660C (HTTP/CGI web interface, port 80)

## ✨ Fitur

- **Multi-Device Parallel** — tarik data dari 4 mesin sekaligus tanpa blocking
- **Ping All** — cek reachability semua mesin di jaringan
- **Test Koneksi** — verifikasi koneksi protocol (TCP/HTTP) ke setiap mesin
- **Status Real-time** — dashboard visual hijau/merah per mesin
- **Filter Data** — saring berdasarkan tanggal dan sumber mesin
- **Export Excel/CSV** — simpan hasil lengkap dengan kolom sumber mesin
- **Retry Mechanism** — 3x percobaan otomatis jika gagal connect
- **Diagnostics** — tool troubleshooting jaringan built-in

## 🏗️ Arsitektur

```
┌───────────────────────────────────────────┐
│              UI Layer (CustomTkinter)       │
│  ┌─────────┐ ┌────────┐ ┌──────────┐     │
│  │Koneksi  │ │ Data   │ │  Export  │     │
│  │(4 Mesin)│ │(Filter)│ │(XLS/CSV) │     │
│  └────┬────┘ └───┬────┘ └────┬─────┘     │
└───────┼──────────┼───────────┼────────────┘
        │          │           │
┌───────┼──────────┼───────────┼────────────┐
│       ▼          ▼           ▼             │
│          Core Business Logic               │
│  ┌──────────────────────────────────┐      │
│  │      MultiDeviceManager          │      │
│  │   (ThreadPoolExecutor-based)     │      │
│  └──────┬────────────────┬──────────┘      │
│         │                │                 │
│  ┌──────▼──────┐  ┌─────▼───────┐         │
│  │ Biotronix   │  │   Chiyu     │         │
│  │ (pyzk TCP)  │  │ (HTTP/CGI)  │         │
│  └─────────────┘  └─────────────┘         │
│                                            │
│  ┌─────────────┐  ┌─────────────┐         │
│  │DataProcessor│  │  Exporter   │         │
│  │(filter/sort)│  │(Excel/CSV)  │         │
│  └─────────────┘  └─────────────┘         │
└────────────────────────────────────────────┘
```

## 📂 Struktur Project

```
Project Scan/
├── main.py                     ← Entry point + logging setup
├── config.py                   ← Konfigurasi 4 mesin + settings
├── requirements.txt
├── start.bat
│
├── core/                       ← Business Logic
│   ├── machine.py              ← Base class + AttendanceRecord
│   ├── biotronix.py            ← Handler Biotronix (ZKTeco TCP)
│   ├── chiyu.py                ← Handler Chiyu (HTTP/CGI parsing)
│   ├── multi_device.py         ← Parallel fetch manager
│   ├── data_processor.py       ← Filter, sort, statistik
│   ├── exporter.py             ← Export Excel/CSV
│   └── diagnostics.py          ← Network troubleshooting tool
│
├── ui/                         ← Presentation Layer
│   ├── app.py                  ← Window utama + tabs
│   └── frames/
│       ├── connection_frame.py ← Dashboard 4 mesin + buttons
│       ├── data_frame.py       ← Tabel + filter (tanggal/mesin)
│       └── export_frame.py     ← Export interface
│
├── data/exports/               ← Output file
└── logs/                       ← Runtime logs
```

## 🚀 Instalasi & Menjalankan

```bash
# Install dependencies
pip install -r requirements.txt

# Jalankan
python main.py
```

## ⚙️ Konfigurasi Mesin

Edit `config.py` bagian `MACHINES`:

```python
MACHINES = [
    MachineConfig(
        name="Biotronix - Gerbang Utama",
        ip="192.168.3.83",
        port=4370,
        machine_type=MachineType.BIOTRONIX,
    ),
    MachineConfig(
        name="Chiyu - Lantai 1",
        ip="192.168.3.85",
        port=80,
        machine_type=MachineType.CHIYU,
    ),
    # ...tambah mesin lain
]
```

## 🐛 Troubleshooting: "Gagal Terhubung ke Mesin"

### Checklist Diagnostik

| # | Check | Cara Verifikasi |
|---|-------|-----------------|
| 1 | Mesin menyala? | Lihat LED power di mesin |
| 2 | Kabel LAN terpasang? | Cek LED link di port RJ45 |
| 3 | IP benar? | Lihat setting di panel mesin |
| 4 | Ping berhasil? | `ping 192.168.x.x` dari CMD |
| 5 | Port terbuka? | Klik "Ping Semua" di app |
| 6 | Firewall? | Matikan Windows Firewall sementara |
| 7 | IP conflict? | `arp -a 192.168.x.x` dari CMD |
| 8 | Subnet sama? | PC dan mesin harus di subnet yang sama |

### Penyebab Umum per Tipe Mesin

**Biotronix (Port 4370):**
- Port 4370 harus dibuka di kedua sisi (mesin & PC)
- Pastikan "Communication Mode" di mesin = TCP/IP
- Hanya 1 koneksi aktif per waktu (jangan buka software lain yang akses mesin)
- Coba restart mesin jika stuck

**Chiyu (Port 80):**
- Buka `http://IP_MESIN/` di browser terlebih dahulu
- Jika browser bisa buka tapi app tidak → firewall per-aplikasi
- Mesin Chiyu BF-660C menggunakan CGI endpoint `if.cgi`
- Jangan lupa: beberapa mesin perlu akses frame (cmdbar.htm → AccLog.htm)

## 📦 Build Executable

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name "Absensi Reader" main.py
```
