#!/usr/bin/env python3
"""xauusd_levels.py — prints current XAU/USD price + our key levels (read-only)."""
import json, urllib.request
# user's known setup levels (from session): Entry 3992-3996, SL 3970, TP1 4015, TP2 4040, TP3 4080
LEVELS = {"entry_zone": [3992, 3996], "sl": 3970, "tp1": 4015, "tp2": 4040, "tp3": 4080}
try:
    d = json.load(urllib.request.urlopen(urllib.request.Request("https://api.binance.com/api/v3/ticker/price?symbol=PAXGUSDT"), timeout=10))
    paxg = float(d['price'])  # PAXG tracks gold oz closely
    out = {"proxy_price_PAXG": paxg, "levels": LEVELS}
    # position check
    e1,e2 = LEVELS["entry_zone"]
    out["in_entry_zone"] = e1 <= paxg <= e2
    out["above_tp1"] = paxg >= LEVELS["tp1"]
    out["below_sl"] = paxg <= LEVELS["sl"]
except Exception as e:
    out = {"error": str(e)}
print(json.dumps(out, indent=1))
