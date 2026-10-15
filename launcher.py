"""
Alborz Launcher - Enhanced
اجرای سرور وب، باز کردن خودکار مرورگر، نمایش در System Tray
"""
import sys
import os
import time
import socket
import threading
import webbrowser
import logging
from pathlib import Path

# مسیر پروژه
if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys._MEIPASS)
    APP_DIR = Path(sys.executable).parent
else:
    BASE_DIR = Path(__file__).parent
    APP_DIR = BASE_DIR

sys.path.insert(0, str(BASE_DIR))

# لاگ
LOG_FILE = APP_DIR / "Alborz.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("Alborz")


def find_free_port(start=8000, end=8100):
    for port in range(start, end):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise RuntimeError("هیچ پورت آزادی پیدا نشد")


def open_browser_later(url, delay=2.0):
    def _open():
        time.sleep(delay)
        webbrowser.open(url)
    threading.Thread(target=_open, daemon=True).start()


def banner(url):
    print()
    print("=" * 62)
    print("  🛠️  Alborz  —  Metadata Extractor & Manager")
    print("=" * 62)
    print(f"  ✅ سرور در حال اجرا روی: {url}")
    print("  🌐 مرورگر به‌طور خودکار باز می‌شود...")
    print()
    print("  📋 قابلیت‌ها:")
    print("     • استخراج کامل EXIF/GPS/IPTC")
    print("     • امتیاز حریم خصوصی")
    print("     • حذف متادیتا (کامل یا انتخابی)")
    print("     • پردازش دسته‌ای + ZIP")
    print("     • نقشه GPS تعاملی")
    print("     • گزارش PDF")
    print("     • ویرایش تگ‌ها")
    print("     • مقایسه دو فایل")
    print()
    print(f"  📄 لاگ: {LOG_FILE}")
    print("  ⛔ برای بستن، این پنجره را ببندید یا Ctrl+C بزنید.")
    print("=" * 62)
    print()


def main():
    try:
        import uvicorn
        from Alborz.api.server import app
        from Alborz import __version__

        log.info(f"Starting Alborz v{__version__}")

        port = find_free_port()
        url = f"http://127.0.0.1:{port}"

        banner(url)
        open_browser_later(url)

        uvicorn.run(
            app,
            host="127.0.0.1",
            port=port,
            log_level="warning",
            access_log=False,
        )
    except Exception as e:
        log.exception("Fatal error")
        print(f"\n❌ خطا: {e}")
        input("\nEnter بزنید برای بستن...")
        sys.exit(1)


if __name__ == "__main__":
    main()