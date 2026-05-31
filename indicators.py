# ============================================================
#  indicators.py — Indikator teknikal profesional
#  RSI · MACD · Bollinger Bands · Moving Average · Volume
# ============================================================
import statistics
import config


# ── RSI (Relative Strength Index) ───────────────────────────
def hitung_rsi(harga: list, period: int = 14) -> float:
    """
    RSI mengukur kekuatan momentum naik vs turun.
    < 35 = oversold (potensi beli) | > 65 = overbought (potensi jual)
    """
    if len(harga) < period + 1:
        return 50.0

    delta  = [harga[i] - harga[i-1] for i in range(1, len(harga))]
    gains  = [d if d > 0 else 0.0 for d in delta]
    losses = [-d if d < 0 else 0.0 for d in delta]

    avg_g = sum(gains[:period]) / period
    avg_l = sum(losses[:period]) / period

    for i in range(period, len(delta)):
        avg_g = (avg_g * (period - 1) + gains[i]) / period
        avg_l = (avg_l * (period - 1) + losses[i]) / period

    if avg_l == 0:
        return 100.0
    rs = avg_g / avg_l
    return round(100 - (100 / (1 + rs)), 2)


# ── EMA (Exponential Moving Average) ────────────────────────
def hitung_ema(harga: list, period: int) -> float:
    """EMA memberi bobot lebih pada harga terbaru."""
    if len(harga) < period:
        return 0.0
    k   = 2 / (period + 1)
    ema = sum(harga[:period]) / period
    for h in harga[period:]:
        ema = h * k + ema * (1 - k)
    return round(ema, 8)


def hitung_ema_series(harga: list, period: int) -> list:
    """Hitung seluruh series EMA (untuk MACD)."""
    if len(harga) < period:
        return []
    k      = 2 / (period + 1)
    result = [sum(harga[:period]) / period]
    for h in harga[period:]:
        result.append(h * k + result[-1] * (1 - k))
    return result


# ── MA (Simple Moving Average) ───────────────────────────────
def hitung_ma(harga: list, period: int) -> float:
    if len(harga) < period:
        return 0.0
    return round(sum(harga[-period:]) / period, 8)


# ── MACD ─────────────────────────────────────────────────────
def hitung_macd(harga: list) -> dict:
    """
    MACD = EMA(12) - EMA(26)
    Signal = EMA(9) dari MACD
    Histogram = MACD - Signal

    Return: {"macd": float, "signal": float, "histogram": float,
             "bullish_cross": bool, "bearish_cross": bool}
    """
    if len(harga) < 35:
        return {"macd": 0, "signal": 0, "histogram": 0,
                "bullish_cross": False, "bearish_cross": False}

    ema12 = hitung_ema_series(harga, 12)
    ema26 = hitung_ema_series(harga, 26)

    # Sejajarkan panjang
    min_len   = min(len(ema12), len(ema26))
    macd_line = [ema12[-(min_len - i)] - ema26[-(min_len - i)]
                 for i in range(min_len)]

    if len(macd_line) < 9:
        return {"macd": 0, "signal": 0, "histogram": 0,
                "bullish_cross": False, "bearish_cross": False}

    signal_line = hitung_ema_series(macd_line, 9)

    macd_now    = macd_line[-1]
    signal_now  = signal_line[-1]
    macd_prev   = macd_line[-2]   if len(macd_line) > 1   else macd_now
    signal_prev = signal_line[-2] if len(signal_line) > 1 else signal_now

    return {
        "macd":          round(macd_now, 8),
        "signal":        round(signal_now, 8),
        "histogram":     round(macd_now - signal_now, 8),
        # Bullish cross: MACD naik melewati Signal dari bawah
        "bullish_cross": macd_prev <= signal_prev and macd_now > signal_now,
        # Bearish cross: MACD turun melewati Signal dari atas
        "bearish_cross": macd_prev >= signal_prev and macd_now < signal_now,
    }


# ── BOLLINGER BANDS ──────────────────────────────────────────
def hitung_bollinger(harga: list, period: int = 20, std_mult: float = 2.0) -> dict:
    """
    Upper = MA + 2*StdDev  |  Lower = MA - 2*StdDev
    Harga < Lower = potensi beli  |  Harga > Upper = potensi jual
    """
    if len(harga) < period:
        return {"upper": 0, "middle": 0, "lower": 0, "lebar_pct": 0}

    data   = harga[-period:]
    middle = sum(data) / period
    std    = statistics.stdev(data) if len(data) > 1 else 0
    upper  = middle + std_mult * std
    lower  = middle - std_mult * std
    lebar  = (upper - lower) / middle * 100 if middle else 0

    return {
        "upper":     round(upper, 2),
        "middle":    round(middle, 2),
        "lower":     round(lower, 2),
        "lebar_pct": round(lebar, 2),
    }


# ── ANALISIS VOLUME ──────────────────────────────────────────
def analisis_volume(vol_sekarang: float, vol_history: list) -> dict:
    """
    Bandingkan volume sekarang dengan rata-rata.
    Spike volume = konfirmasi sinyal lebih kuat.
    """
    if not vol_history or vol_sekarang == 0:
        return {"rasio": 1.0, "spike": False, "label": "Normal"}

    avg_vol = sum(vol_history) / len(vol_history)
    rasio   = vol_sekarang / avg_vol if avg_vol > 0 else 1.0
    spike   = rasio >= 1.8

    if rasio >= 2.5:   label = "Sangat Tinggi"
    elif rasio >= 1.8: label = "Tinggi"
    elif rasio >= 1.2: label = "Normal Atas"
    elif rasio >= 0.8: label = "Normal"
    else:              label = "Rendah"

    return {"rasio": round(rasio, 2), "spike": spike, "label": label}


# ── TREN MA ──────────────────────────────────────────────────
def analisis_tren(harga: list) -> str:
    """Bandingkan MA7 vs MA25 untuk tren: 'naik', 'turun', 'sideways'"""
    ma7  = hitung_ma(harga, config.MA_PENDEK)
    ma25 = hitung_ma(harga, config.MA_PANJANG)
    if ma7 == 0 or ma25 == 0:
        return "sideways"
    selisih = (ma7 - ma25) / ma25 * 100
    if selisih > 1.0:    return "naik"
    elif selisih < -1.0: return "turun"
    return "sideways"


# ── SKOR SINYAL TERPADU (0–100) ──────────────────────────────
def hitung_skor_sinyal(harga: list, harga_sekarang: float,
                       vol_rasio: float) -> dict:
    """
    Gabungkan semua indikator menjadi satu skor sinyal.
    Skor Beli: tinggi = sinyal beli kuat
    Skor Jual: tinggi = sinyal jual kuat
    """
    skor_beli = 0
    skor_jual = 0
    alasan    = []

    rsi  = hitung_rsi(harga)
    macd = hitung_macd(harga)
    bb   = hitung_bollinger(harga)
    tren = analisis_tren(harga)
    ma7  = hitung_ma(harga, 7)
    ma25 = hitung_ma(harga, 25)

    # ── RSI scoring ──
    if rsi < 25:
        skor_beli += 35; alasan.append(f"RSI {rsi} (Oversold Ekstrem)")
    elif rsi < config.RSI_BELI:
        skor_beli += 22; alasan.append(f"RSI {rsi} (Oversold)")
    elif rsi < 50:
        skor_beli += 8
    elif rsi > 75:
        skor_jual += 35; alasan.append(f"RSI {rsi} (Overbought Ekstrem)")
    elif rsi > config.RSI_JUAL:
        skor_jual += 22; alasan.append(f"RSI {rsi} (Overbought)")

    # ── MACD scoring ──
    if macd["bullish_cross"]:
        skor_beli += 25; alasan.append("MACD Bullish Cross")
    elif macd["bearish_cross"]:
        skor_jual += 25; alasan.append("MACD Bearish Cross")
    elif macd["histogram"] > 0:
        skor_beli += 8
    elif macd["histogram"] < 0:
        skor_jual += 8

    # ── Bollinger Bands scoring ──
    if bb["lower"] > 0:
        if harga_sekarang < bb["lower"]:
            skor_beli += 20; alasan.append("Di bawah Bollinger Lower")
        elif harga_sekarang > bb["upper"]:
            skor_jual += 20; alasan.append("Di atas Bollinger Upper")

    # ── MA Trend scoring ──
    if tren == "naik":
        skor_beli += 12; alasan.append("Tren MA Naik")
    elif tren == "turun":
        skor_jual += 12; alasan.append("Tren MA Turun")

    # ── Volume scoring ──
    if vol_rasio >= 2.0:
        # Volume tinggi memperkuat sinyal yang sedang dominan
        if skor_beli > skor_jual:
            skor_beli += 8; alasan.append(f"Volume Tinggi ({vol_rasio:.1f}x)")
        else:
            skor_jual += 8; alasan.append(f"Volume Tinggi ({vol_rasio:.1f}x)")

    # Normalisasi ke 0-100
    skor_beli = min(100, skor_beli)
    skor_jual = min(100, skor_jual)

    return {
        "skor_beli":  skor_beli,
        "skor_jual":  skor_jual,
        "rsi":        rsi,
        "macd":       macd,
        "bb":         bb,
        "tren":       tren,
        "ma7":        ma7,
        "ma25":       ma25,
        "alasan":     alasan,
    }
