import sys
import os
import logging
from datetime import datetime

# Menambahkan root project ke path
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

    from config import APP_MODE, IS_DEVELOPMENT

    logger.info("=" * 50)
    logger.info("Aplikasi Absensi Reader - Multi Device Started")
    logger.info(f"Mode: {APP_MODE.upper()} {'(dummy data)' if IS_DEVELOPMENT else '(mesin asli)'}")
    logger.info("=" * 50)

    from ui.app import App

    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
