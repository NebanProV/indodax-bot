# ============================================================
#  config.py — Semua pengaturan bot (dibaca dari file .env)
# ============================================================
import os
from dotenv import load_dotenv

load_dotenv()

# ── INDODAX API ──────────────────────────────────────────────
INDODAX_API_KEY    = os.getenv("INDODAX_API_KEY", "")
INDODAX_SECRET_KEY = os.getenv("INDODAX_SECRET_KEY", "")

# ── TELEGRAM ─────────────────────────────────────────────────
TELEGRAM_TOKEN   = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# ── DAFTAR KOIN YANG DIPANTAU ────────────────────────────────
# Format: nama_koin + idr (semua huruf kecil)
WATCHLIST = [
    "hbaridr",   # Hedera HBAR
    "dogeidr",   # Dogecoin DOGE
    "trxidr",    # TRON TRX
    "xlmidr",    # Stellar XLM
    "nearidr",   # NEAR Protocol
    "adaidr",    # Cardano ADA
    "btcidr",    # Bitcoin BTC
    "ethidr",    # Ethereum ETH
    "solidr",    # Solana SOL
    "linkidr",   # Chainlink LINK
]

# ── PARAMETER INDIKATOR ──────────────────────────────────────
RSI_PERIOD  = 14
RSI_BELI    = 35   # RSI di bawah ini = sinyal beli
RSI_JUAL    = 65   # RSI di atas ini  = sinyal jual
MA_PENDEK   = 7
MA_PANJANG  = 25
BB_PERIOD   = 20   # Bollinger Bands period
BB_STD      = 2.0  # Bollinger Bands std dev

# ── MANAJEMEN RISIKO ─────────────────────────────────────────
TAKE_PROFIT = 0.08   # Jual otomatis saat untung 8%
STOP_LOSS   = 0.05   # Jual otomatis saat rugi 5%
MODAL_IDR   = int(os.getenv("MODAL_IDR", 90000))

# ── PENGATURAN BOT ───────────────────────────────────────────
SCAN_INTERVAL_DETIK = 5 * 60      # Scan tiap 5 menit
DAILY_SUMMARY_JAM   = 8           # Kirim ringkasan tiap jam 8 pagi
MIN_SKOR_BELI       = 60          # Minimum skor untuk alert beli (0-100)
MIN_SKOR_JUAL       = 55          # Minimum skor untuk alert jual

# Mode simulasi: True = tidak ada order nyata
MODE_SIMULASI = os.getenv("MODE_SIMULASI", "True").strip().lower() == "true"

# File penyimpanan state posisi
STATE_FILE = "posisi.json"
