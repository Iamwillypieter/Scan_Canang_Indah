"""
Aplikasi Desktop Tarik Data Absensi - Multi Device
Entry point aplikasi.

Mendukung:
- 2x Mesin Biotronix (ZKTeco TCP protocol, port 4370)
- 2x Mesin Chiyu (HTTP/CGI web interface, port 80)
"""
import sys
import os
import logging
from datetime import datetime

# Tambahkan root project ke path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import LOG_FOLDER


def setup_logging():
    """Setup logging ke file dan console."""
    log_file = os.path.join(
        LOG_FOLDER, f"app_{datetime.now().strftime('%Y%m%d')}.log"
    )

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )


def main():
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("=" * 50)
    logger.info("Aplikasi Absensi Reader - Multi Device Started")
    logger.info("=" * 50)

    from ui.app import App

    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
