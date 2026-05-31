# ============================================================
#  scanner.py — Pemindai multi-koin & manajer posisi
# ============================================================
import json
import os
import time
from datetime import datetime
import config
import indodax_api as api
import indicators as ind


# ── Posisi Manager ───────────────────────────────────────────
class PosisiManager:
    """Menyimpan dan mengelola posisi terbuka."""

    def __init__(self):
        self.state = self._load()

    def _load(self) -> dict:
        if os.path.exists(config.STATE_FILE):
            try:
                with open(config.STATE_FILE) as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "posisi":       {},   # pair → {harga_beli, jumlah, modal, waktu}
            "riwayat":      [],   # list of closed trades
            "total_profit": 0.0,
            "win":          0,
            "loss":         0,
        }

    def simpan(self):
        with open(config.STATE_FILE, "w") as f:
            json.dump(self.state, f, indent=2, default=str)

    def ada_posisi(self, pair: str) -> bool:
        return pair in self.state["posisi"]

    def buka_posisi(self, pair: str, harga: float, modal: float):
        fee         = modal * 0.003
        modal_bersih = modal - fee
        jumlah      = modal_bersih / harga
        self.state["posisi"][pair] = {
            "harga_beli": harga,
            "jumlah":     jumlah,
            "modal":      modal,
            "waktu":      datetime.now().isoformat(),
        }
        self.simpan()

    def tutup_posisi(self, pair: str, harga_jual: float) -> dict:
        if pair not in self.state["posisi"]:
            return {}
        pos        = self.state["posisi"][pair]
        hasil      = pos["jumlah"] * harga_jual
        fee        = hasil * 0.003
        hasil_bersih = hasil - fee
        profit     = hasil_bersih - pos["modal"]
        pct        = profit / pos["modal"] * 100

        trade = {
            "pair":       pair,
            "beli":       pos["harga_beli"],
            "jual":       harga_jual,
            "modal":      pos["modal"],
            "profit":     round(profit, 0),
            "pct":        round(pct, 2),
            "durasi":     str(datetime.now()),
        }
        self.state["riwayat"].append(trade)
        self.state["total_profit"] += profit
        if profit > 0:
            self.state["win"] += 1
        else:
            self.state["loss"] += 1

        del self.state["posisi"][pair]
        self.simpan()
        return trade

    def cek_tp_sl(self, pair: str, harga: float) -> str | None:
        """Return 'TP', 'SL', atau None."""
        if pair not in self.state["posisi"]:
            return None
        pos = self.state["posisi"][pair]
        pct = (harga - pos["harga_beli"]) / pos["harga_beli"]
        if pct >= config.TAKE_PROFIT: return "TP"
        if pct <= -config.STOP_LOSS:  return "SL"
        return None

    def info_posisi(self, pair: str, harga: float) -> dict | None:
        if pair not in self.state["posisi"]:
            return None
        pos    = self.state["posisi"][pair]
        profit = (harga - pos["harga_beli"]) / pos["harga_beli"] * 100
        return {**pos, "profit_pct": round(profit, 2),
                "harga_sekarang": harga}

    def ringkasan(self) -> dict:
        total = self.state["win"] + self.state["loss"]
        wr    = self.state["win"] / total * 100 if total > 0 else 0
        return {
            "total_trade":  total,
            "win":          self.state["win"],
            "loss":         self.state["loss"],
            "winrate":      round(wr, 1),
            "total_profit": round(self.state["total_profit"], 0),
            "open":         len(self.state["posisi"]),
        }


# ── Coin Scanner ─────────────────────────────────────────────
class CoinScanner:
    """Memindai semua koin di watchlist dan menghasilkan sinyal."""

    def __init__(self):
        self.posisi  = PosisiManager()
        self.cache   = {}   # cache harga historis agar tidak spam API
        self.last_scan = 0

    def _pair_to_ticker_key(self, pair: str) -> str:
        """'hbaridr' → 'hbar_idr' (format ticker_all API)"""
        koin = pair.replace("idr", "")
        return f"{koin}_idr"

    def scan_semua(self) -> list:
        """
        Pindai semua koin di watchlist.
        Return: list of signal dict, hanya yang memenuhi threshold.
        """
        sinyal_list = []
        semua_harga = api.get_semua_harga()

        for pair in config.WATCHLIST:
            try:
                sinyal = self._analisis_satu_koin(pair, semua_harga)
                if sinyal:
                    sinyal_list.append(sinyal)
                time.sleep(0.5)  # hindari rate limit
            except Exception as e:
                print(f"[SCANNER] Error {pair}: {e}")

        self.last_scan = time.time()
        return sinyal_list

    def _analisis_satu_koin(self, pair: str, semua_harga: dict) -> dict | None:
        """Analisis satu koin, return sinyal jika ada."""
        ticker_key = self._pair_to_ticker_key(pair)
        ticker     = semua_harga.get(ticker_key, {})

        if not ticker:
            ticker = api.get_harga_koin(pair)
        if not ticker:
            return None

        harga_now = float(ticker.get("last", 0))
        vol_idr   = float(ticker.get("vol_idr", 0))
        if harga_now == 0:
            return None

        # Ambil riwayat harga (cached)
        now = time.time()
        if pair not in self.cache or now - self.cache[pair]["ts"] > 300:
            hist = api.get_riwayat_harga(pair, 300)
            self.cache[pair] = {"data": hist, "ts": now}
        hist = self.cache[pair]["data"]

        if len(hist) < 30:
            return None

        # Hitung volume rasio (sederhana: vol sekarang vs median 7 nilai terakhir)
        vol_rasio = 1.0
        if vol_idr > 0 and len(hist) > 10:
            avg_trade_price = sum(hist[-10:]) / 10
            vol_rasio = min(harga_now / avg_trade_price, 3.0) if avg_trade_price else 1.0

        # Hitung semua indikator
        hasil = ind.hitung_skor_sinyal(hist, harga_now, vol_rasio)
        skor_b = hasil["skor_beli"]
        skor_j = hasil["skor_jual"]

        simbol = api.pair_ke_simbol(pair)

        # ── Cek TP / SL posisi terbuka ──
        tp_sl = self.posisi.cek_tp_sl(pair, harga_now)
        if tp_sl == "TP":
            trade = self.posisi.tutup_posisi(pair, harga_now)
            return self._buat_sinyal(pair, simbol, harga_now, "TP",
                                     skor_j, hasil, trade)
        if tp_sl == "SL":
            trade = self.posisi.tutup_posisi(pair, harga_now)
            return self._buat_sinyal(pair, simbol, harga_now, "CUT_LOSS",
                                     skor_j, hasil, trade)

        # ── Sinyal beli baru ──
        if skor_b >= config.MIN_SKOR_BELI and not self.posisi.ada_posisi(pair):
            if config.MODE_SIMULASI:
                self.posisi.buka_posisi(pair, harga_now, config.MODAL_IDR)
            else:
                result = api.eksekusi_beli(pair, config.MODAL_IDR, harga_now)
                if result.get("success") == 1:
                    self.posisi.buka_posisi(pair, harga_now, config.MODAL_IDR)
            return self._buat_sinyal(pair, simbol, harga_now, "BELI",
                                     skor_b, hasil)

        # ── Sinyal jual manual (RSI tinggi, belum TP/SL) ──
        if skor_j >= config.MIN_SKOR_JUAL and self.posisi.ada_posisi(pair):
            return self._buat_sinyal(pair, simbol, harga_now, "JUAL_REKOMENDASI",
                                     skor_j, hasil)

        return None

    def _buat_sinyal(self, pair, simbol, harga, aksi, skor, ind_data,
                     trade_info=None) -> dict:
        return {
            "pair":        pair,
            "simbol":      simbol,
            "harga":       harga,
            "aksi":        aksi,
            "skor":        skor,
            "rsi":         ind_data["rsi"],
            "tren":        ind_data["tren"],
            "macd":        ind_data["macd"],
            "bb":          ind_data["bb"],
            "ma7":         ind_data["ma7"],
            "ma25":        ind_data["ma25"],
            "alasan":      ind_data["alasan"],
            "tp_harga":    round(harga * (1 + config.TAKE_PROFIT), 0),
            "sl_harga":    round(harga * (1 - config.STOP_LOSS), 0),
            "trade_info":  trade_info,
            "waktu":       datetime.now().strftime("%H:%M %d/%m/%Y"),
        }
