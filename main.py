#!/usr/bin/env python3
# ============================================================
#  main.py — Entry point. Jalankan file ini untuk start bot.
#
#  Cara jalankan lokal  : python main.py
#  Cara deploy Railway  : Procfile sudah mengurus ini otomatis
# ============================================================
import logging
import config
from telegram_handler import setup_bot

# Setup logging (tampilkan info di terminal)
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
    datefmt="%H:%M:%S %d/%m/%Y",
)
logging.getLogger("httpx").setLevel(logging.WARNING)
log = logging.getLogger("BOT")


def main():
    # Validasi konfigurasi wajib
    if not config.TELEGRAM_TOKEN:
        log.error("TELEGRAM_BOT_TOKEN kosong! Isi di file .env")
        return
    if not config.TELEGRAM_CHAT_ID:
        log.error("TELEGRAM_CHAT_ID kosong! Isi di file .env")
        return

    mode_label = "SIMULASI" if config.MODE_SIMULASI else "LIVE TRADING"
    log.info(f"Bot dimulai — Mode: {mode_label}")
    log.info(f"Watchlist: {', '.join(config.WATCHLIST)}")
    log.info(f"Scan interval: {config.SCAN_INTERVAL_DETIK // 60} menit")

    if config.MODE_SIMULASI:
        log.info("MODE SIMULASI aktif — tidak ada order nyata yang dieksekusi")

    # Bangun dan jalankan bot
    app = setup_bot()
    log.info("Telegram bot siap. Ketik /start di chat Telegram kamu!")
    app.run_polling(allowed_updates=["message"])


if __name__ == "__main__":
    main()
