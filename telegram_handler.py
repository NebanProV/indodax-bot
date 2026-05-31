# ============================================================
#  telegram_handler.py — Bot Telegram: perintah & notifikasi
# ============================================================
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, ContextTypes
)
from datetime import datetime, time as dtime
import config
from scanner import CoinScanner
import indodax_api as api

scanner = CoinScanner()


# ── FORMAT PESAN ─────────────────────────────────────────────
def fmt_uang(angka: float) -> str:
    return f"Rp {angka:,.0f}"

def fmt_pct(pct: float) -> str:
    return f"{pct:+.2f}%" if pct != 0 else "0.00%"

def tren_emoji(tren: str) -> str:
    return {"naik": "📈", "turun": "📉", "sideways": "➡️"}.get(tren, "➡️")


def format_sinyal_telegram(s: dict) -> str:
    """Format sinyal trading menjadi pesan Telegram yang informatif."""
    aksi     = s["aksi"]
    simbol   = s["simbol"]
    harga    = s["harga"]
    skor     = s["skor"]
    rsi      = s["rsi"]
    tren     = s["tren"]
    alasan   = s["alasan"]
    mode_txt = " <i>[SIMULASI]</i>" if config.MODE_SIMULASI else ""

    # Header berdasarkan aksi
    if aksi == "BELI":
        header = f"🟢 <b>SINYAL BELI</b> — {simbol}{mode_txt}"
        skor_bar = "🟩" * (skor // 10) + "⬜" * (10 - skor // 10)
        body = (
            f"💰 Harga sekarang : <b>{fmt_uang(harga)}</b>\n"
            f"📊 Skor sinyal    : <b>{skor}/100</b>\n"
            f"   {skor_bar}\n\n"
            f"📉 RSI ({config.RSI_PERIOD})       : <b>{rsi}</b> (Oversold)\n"
            f"📈 Tren MA       : {tren_emoji(tren)} {tren.upper()}\n"
            f"🎯 Target profit  : <b>{fmt_uang(s['tp_harga'])}</b> (+{config.TAKE_PROFIT*100:.0f}%)\n"
            f"✂️ Stop loss      : <b>{fmt_uang(s['sl_harga'])}</b> (-{config.STOP_LOSS*100:.0f}%)\n\n"
            f"📝 Alasan sinyal:\n"
        )
        for a in alasan:
            body += f"   • {a}\n"
        body += f"\n⏰ {s['waktu']}"

    elif aksi in ("JUAL_REKOMENDASI",):
        header = f"🔴 <b>REKOMENDASI JUAL</b> — {simbol}{mode_txt}"
        body = (
            f"💰 Harga sekarang : <b>{fmt_uang(harga)}</b>\n"
            f"📊 Skor jual      : <b>{skor}/100</b>\n"
            f"📈 RSI ({config.RSI_PERIOD})       : <b>{rsi}</b> (Overbought)\n"
            f"📉 Tren MA       : {tren_emoji(tren)} {tren.upper()}\n\n"
            f"📝 Alasan:\n"
        )
        for a in alasan:
            body += f"   • {a}\n"
        body += f"\n⏰ {s['waktu']}"

    elif aksi == "TP":
        trade    = s.get("trade_info", {})
        profit   = trade.get("profit", 0)
        pct      = trade.get("pct", 0)
        header   = f"✅ <b>TAKE PROFIT</b> — {simbol}{mode_txt}"
        body = (
            f"💰 Harga jual  : <b>{fmt_uang(harga)}</b>\n"
            f"💵 Profit      : <b>+{fmt_uang(profit)}</b> (+{pct:.2f}%)\n"
            f"🏆 Target profit tercapai!\n\n"
            f"⏰ {s['waktu']}"
        )

    elif aksi == "CUT_LOSS":
        trade    = s.get("trade_info", {})
        profit   = trade.get("profit", 0)
        pct      = trade.get("pct", 0)
        header   = f"✂️ <b>CUT LOSS</b> — {simbol}{mode_txt}"
        body = (
            f"💰 Harga jual  : <b>{fmt_uang(harga)}</b>\n"
            f"📉 Loss        : <b>{fmt_uang(profit)}</b> ({pct:.2f}%)\n"
            f"🛡️ Stop loss dieksekusi — modal dilindungi!\n\n"
            f"⏰ {s['waktu']}"
        )

    else:
        header = f"ℹ️ INFO — {simbol}"
        body   = str(s)

    return f"{header}\n{'─' * 28}\n{body}"


# ── PERINTAH TELEGRAM ────────────────────────────────────────
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    mode = "🟡 SIMULASI" if config.MODE_SIMULASI else "🔴 LIVE TRADING"
    pairs = ", ".join([p.replace("idr", "").upper() for p in config.WATCHLIST])
    pesan = (
        f"🤖 <b>Bot Trading INDODAX aktif!</b>\n\n"
        f"Mode        : <b>{mode}</b>\n"
        f"Scan tiap   : {config.SCAN_INTERVAL_DETIK // 60} menit\n"
        f"Modal       : {fmt_uang(config.MODAL_IDR)}\n"
        f"Take Profit : +{config.TAKE_PROFIT*100:.0f}%\n"
        f"Stop Loss   : -{config.STOP_LOSS*100:.0f}%\n\n"
        f"Watchlist:\n<code>{pairs}</code>\n\n"
        f"Ketik /help untuk daftar perintah."
    )
    await update.message.reply_html(pesan)


async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_html(
        "📋 <b>Daftar Perintah Bot</b>\n\n"
        "/start    — Info bot\n"
        "/scan     — Pindai koin sekarang\n"
        "/status   — Status posisi terbuka\n"
        "/harga    — Harga semua koin watchlist\n"
        "/portfolio — Ringkasan profit/loss\n"
        "/help     — Tampilkan menu ini\n\n"
        "ℹ️ Bot otomatis scan dan kirim notifikasi setiap "
        f"{config.SCAN_INTERVAL_DETIK // 60} menit."
    )


async def cmd_scan(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_html("🔍 <i>Memindai koin... tunggu sebentar.</i>")
    sinyal_list = scanner.scan_semua()

    if not sinyal_list:
        await update.message.reply_html(
            "📊 Scan selesai.\n"
            "Tidak ada sinyal kuat saat ini.\n"
            "Semua koin dalam kondisi <b>TAHAN / NETRAL</b>."
        )
        return

    for s in sinyal_list:
        await update.message.reply_html(format_sinyal_telegram(s))


async def cmd_harga(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    semua = api.get_semua_harga()
    baris = []
    for pair in config.WATCHLIST:
        koin = pair.replace("idr", "").upper()
        key  = f"{pair.replace('idr', '')}_idr"
        t    = semua.get(key, {})
        if t:
            h   = float(t.get("last", 0))
            beli = float(t.get("buy", 0))
            naik = h >= beli
            arah = "🟢" if naik else "🔴"
            baris.append(f"{arah} <b>{koin:<6}</b> {fmt_uang(h)}")
        else:
            baris.append(f"⚪ <b>{koin:<6}</b> tidak tersedia")

    teks = "💹 <b>Harga Koin Watchlist</b>\n" + "─" * 28 + "\n"
    teks += "\n".join(baris)
    teks += f"\n\n⏰ {datetime.now().strftime('%H:%M:%S %d/%m/%Y')}"
    await update.message.reply_html(teks)


async def cmd_status(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    posisi_dict = scanner.posisi.state.get("posisi", {})
    if not posisi_dict:
        await update.message.reply_html(
            "📂 <b>Tidak ada posisi terbuka saat ini.</b>\n\n"
            "Bot sedang menunggu sinyal beli yang kuat."
        )
        return

    semua_harga = api.get_semua_harga()
    teks        = "📂 <b>Posisi Terbuka</b>\n" + "─" * 28 + "\n"

    for pair, pos in posisi_dict.items():
        koin    = pair.replace("idr", "").upper()
        key     = f"{pair.replace('idr', '')}_idr"
        t       = semua_harga.get(key, {})
        h_now   = float(t.get("last", pos["harga_beli"])) if t else pos["harga_beli"]
        pct     = (h_now - pos["harga_beli"]) / pos["harga_beli"] * 100
        profit  = (h_now - pos["harga_beli"]) * pos["jumlah"]
        emoji   = "✅" if profit >= 0 else "📉"

        teks += (
            f"\n{emoji} <b>{koin}</b>\n"
            f"   Beli  : {fmt_uang(pos['harga_beli'])}\n"
            f"   Skrng : {fmt_uang(h_now)}\n"
            f"   P/L   : <b>{fmt_pct(pct)}</b> ({fmt_uang(profit)})\n"
            f"   TP    : {fmt_uang(pos['harga_beli'] * (1+config.TAKE_PROFIT))}\n"
            f"   SL    : {fmt_uang(pos['harga_beli'] * (1-config.STOP_LOSS))}\n"
        )

    await update.message.reply_html(teks)


async def cmd_portfolio(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    r    = scanner.posisi.ringkasan()
    mode = "🟡 SIMULASI" if config.MODE_SIMULASI else "🔴 LIVE"
    pcolor = "+" if r["total_profit"] >= 0 else ""
    teks = (
        f"📊 <b>Ringkasan Portfolio</b> [{mode}]\n"
        f"{'─' * 28}\n"
        f"Total trade : <b>{r['total_trade']}</b>\n"
        f"Menang      : <b>{r['win']}</b>\n"
        f"Kalah       : <b>{r['loss']}</b>\n"
        f"Win Rate    : <b>{r['winrate']}%</b>\n"
        f"Posisi buka : <b>{r['open']}</b>\n"
        f"Total Profit: <b>{pcolor}{fmt_uang(r['total_profit'])}</b>\n"
        f"\n⏰ {datetime.now().strftime('%H:%M %d/%m/%Y')}"
    )
    await update.message.reply_html(teks)


# ── JOB QUEUE CALLBACKS ──────────────────────────────────────
async def job_scan_otomatis(ctx: ContextTypes.DEFAULT_TYPE):
    """Dipanggil otomatis setiap N menit — scan dan kirim alert."""
    try:
        sinyal_list = scanner.scan_semua()
        for s in sinyal_list:
            await ctx.bot.send_message(
                chat_id=config.TELEGRAM_CHAT_ID,
                text=format_sinyal_telegram(s),
                parse_mode="HTML"
            )
    except Exception as e:
        print(f"[JOB ERROR] scan_otomatis: {e}")


async def job_ringkasan_harian(ctx: ContextTypes.DEFAULT_TYPE):
    """Kirim ringkasan portfolio tiap pagi jam 8."""
    try:
        r    = scanner.posisi.ringkasan()
        mode = "🟡 SIMULASI" if config.MODE_SIMULASI else "🔴 LIVE"
        teks = (
            f"🌅 <b>Ringkasan Harian — {datetime.now().strftime('%d/%m/%Y')}</b>\n"
            f"Mode: {mode}\n{'─' * 28}\n"
            f"Total trade : {r['total_trade']}\n"
            f"Win Rate    : {r['winrate']}%\n"
            f"Total Profit: {fmt_uang(r['total_profit'])}\n"
            f"Posisi buka : {r['open']}\n\n"
            f"Bot berjalan normal. Selamat pagi! ☀️"
        )
        await ctx.bot.send_message(
            chat_id=config.TELEGRAM_CHAT_ID,
            text=teks,
            parse_mode="HTML"
        )
    except Exception as e:
        print(f"[JOB ERROR] ringkasan_harian: {e}")


# ── SETUP APPLICATION ────────────────────────────────────────
def setup_bot() -> Application:
    """Buat dan konfigurasi aplikasi Telegram bot."""
    app = Application.builder().token(config.TELEGRAM_TOKEN).build()

    # Daftarkan perintah
    app.add_handler(CommandHandler("start",     cmd_start))
    app.add_handler(CommandHandler("help",      cmd_help))
    app.add_handler(CommandHandler("scan",      cmd_scan))
    app.add_handler(CommandHandler("harga",     cmd_harga))
    app.add_handler(CommandHandler("status",    cmd_status))
    app.add_handler(CommandHandler("portfolio", cmd_portfolio))

    # Jadwalkan scan otomatis setiap N detik
    app.job_queue.run_repeating(
        job_scan_otomatis,
        interval=config.SCAN_INTERVAL_DETIK,
        first=30,   # mulai 30 detik setelah start
    )

    # Jadwalkan ringkasan harian jam 08:00
    app.job_queue.run_daily(
        job_ringkasan_harian,
        time=dtime(hour=8, minute=0, second=0),
    )

    return app
