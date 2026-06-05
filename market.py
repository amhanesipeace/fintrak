"""Real-time crypto prices via the public CoinGecko REST API (no key needed)."""
import json
import time
import urllib.parse
import urllib.request

CG = "https://api.coingecko.com/api/v3"

# Curated set of popular coins offered in the "add holding" dropdown.
COINS = [
    {"id": "bitcoin", "symbol": "BTC", "name": "Bitcoin"},
    {"id": "ethereum", "symbol": "ETH", "name": "Ethereum"},
    {"id": "binancecoin", "symbol": "BNB", "name": "BNB"},
    {"id": "solana", "symbol": "SOL", "name": "Solana"},
    {"id": "ripple", "symbol": "XRP", "name": "XRP"},
    {"id": "cardano", "symbol": "ADA", "name": "Cardano"},
    {"id": "dogecoin", "symbol": "DOGE", "name": "Dogecoin"},
    {"id": "polkadot", "symbol": "DOT", "name": "Polkadot"},
    {"id": "litecoin", "symbol": "LTC", "name": "Litecoin"},
    {"id": "chainlink", "symbol": "LINK", "name": "Chainlink"},
]
COIN_BY_ID = {c["id"]: c for c in COINS}

_cache = {}
_TTL = 60  # seconds — keep within CoinGecko's free rate limits


def get_prices(coin_ids, vs="usd"):
    """Return {coin_id: price} for the given CoinGecko ids."""
    coin_ids = sorted({c for c in coin_ids if c})
    if not coin_ids:
        return {}

    key = (",".join(coin_ids), vs)
    now = time.time()
    hit = _cache.get(key)
    if hit and now - hit[0] < _TTL:
        return hit[1]

    qs = urllib.parse.urlencode({"ids": ",".join(coin_ids), "vs_currencies": vs})
    url = f"{CG}/simple/price?{qs}"
    req = urllib.request.Request(url, headers={"User-Agent": "finance-tracker/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception:
        # On API/network failure, fall back to any cached value or zeros.
        return hit[1] if hit else {cid: None for cid in coin_ids}

    prices = {cid: (data.get(cid) or {}).get(vs) for cid in coin_ids}
    _cache[key] = (now, prices)
    return prices
