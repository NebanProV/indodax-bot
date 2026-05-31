# ============================================================
#  indodax_api.py — Koneksi ke API INDODAX
#  Public API (harga): tidak butuh login
#  Private API (trading): butuh API Key + Secret Key
# ============================================================
import hashlib
import hmac
import time
import requests
from urllib.parse import urlencode
import config

PUBLIC_BASE  = "https://indodax.com/api"
PRIVATE_BASE = "https://indodax.com/tapi"
TIMEOUT      = 15


def get_semua_harga() -> dict:
    """
    Ambil harga terkini SEMUA koin sekaligus (1 API call efisien).
    Return dict: {"btc_idr": {"last":"...", "buy":"...", ...}, ...}
    """
    try:
        r = requests.get(f"{PUBLIC_BASE}/ticker_all", timeout=TIMEOUT)
        r.raise_for_status()
        data = r.json()
        return data.get("tickers", {})
    except Exception as e:
        print(f"[API ERROR] get_semua_harga: {e}")
        return {}


def get_harga_koin(pair: str) -> dict:
    """
    Ambil harga satu koin. pair contoh: 'hbaridr'
    Return: {"last":..., "buy":..., "sell":..., "high":..., "low":..., "vol_idr":...}
    """
    try:
        r = requests.get(f"{PUBLIC_BASE}/{pair}/ticker", timeout=TIMEOUT)
        r.raise_for_status()
        return r.json().get("ticker", {})
    except Exception as e:
        print(f"[API ERROR] get_harga_koin({pair}): {e}")
        return {}


def get_riwayat_harga(pair: str, jumlah: int = 200) -> list:
    """
    Ambil riwayat transaksi untuk menghitung indikator teknikal.
    Return: list of float (harga dari terlama → terbaru)
    """
    try:
        r = requests.get(f"{PUBLIC_BASE}/{pair}/trades", timeout=TIMEOUT)
        r.raise_for_status()
        trades = r.json()
        harga_list = [float(t["price"]) for t in trades if "price" in t]
        return harga_list[-jumlah:]
    except Exception as e:
        print(f"[API ERROR] get_riwayat_harga({pair}): {e}")
        return []


def get_orderbook(pair: str) -> dict:
    """
    Ambil order book (antrian beli/jual).
    Berguna untuk melihat tekanan beli vs jual.
    """
    try:
        r = requests.get(f"{PUBLIC_BASE}/{pair}/depth", timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"[API ERROR] get_orderbook({pair}): {e}")
        return {}


def _private_request(method: str, params: dict = {}) -> dict:
    """Kirim request ke Private API (butuh API Key & Secret)."""
    if config.MODE_SIMULASI:
        return {"success": 1, "simulasi": True, "method": method}

    nonce     = str(int(time.time() * 1000))
    post_data = {"method": method, "timestamp": nonce, **params}
    body      = urlencode(post_data)
    signature = hmac.new(
        config.INDODAX_SECRET_KEY.encode(),
        body.encode(),
        hashlib.sha512
    ).hexdigest()

    headers = {
        "Key":          config.INDODAX_API_KEY,
        "Sign":         signature,
        "Content-Type": "application/x-www-form-urlencoded",
    }
    try:
        r = requests.post(PRIVATE_BASE, data=post_data, headers=headers, timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"[API ERROR] private_request({method}): {e}")
        return {}


def get_saldo() -> dict:
    """Cek saldo akun INDODAX."""
    result = _private_request("getInfo")
    if result.get("success") == 1:
        return result.get("return", {}).get("balance", {})
    return {}


def eksekusi_beli(pair: str, modal_idr: float, harga: float) -> dict:
    """Eksekusi order beli limit."""
    koin        = pair.replace("idr", "")
    jumlah_koin = modal_idr / harga
    params = {
        "pair":  pair,
        "type":  "buy",
        "price": str(int(harga)),
        koin:    f"{jumlah_koin:.8f}",
    }
    return _private_request("trade", params)


def eksekusi_jual(pair: str, jumlah_koin: float, harga: float) -> dict:
    """Eksekusi order jual limit."""
    koin = pair.replace("idr", "")
    params = {
        "pair":  pair,
        "type":  "sell",
        "price": str(int(harga)),
        koin:    f"{jumlah_koin:.8f}",
    }
    return _private_request("trade", params)


def pair_ke_simbol(pair: str) -> str:
    """'hbaridr' → 'HBAR/IDR'"""
    koin = pair.replace("idr", "").upper()
    return f"{koin}/IDR"
