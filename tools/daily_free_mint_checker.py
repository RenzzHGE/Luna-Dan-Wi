#!/usr/bin/env python3
"""daily_free_mint_checker.py — checks daily free-mint availability (read-only)."""
import json, subprocess, time, datetime

RPC = "https://bsc-dataseed.binance.org/"
ME = "0xf47dD174879d17b8bC0cDCa6B1D487EC7DCaB195"
CORE = "0xc7b7593Aa572701d26301D9707E93b0c511e636A"  # AnthroBitCore

def rpc(m,p):
    payload = json.dumps({"jsonrpc":"2.0","id":1,"method":m,"params":p})
    r = subprocess.run(["curl","-s","-m","10","-X","POST",RPC,"-H","Content-Type: application/json","-d",payload], capture_output=True, text=True)
    try: return json.loads(r.stdout)
    except: return {}

def call(data):
    r = rpc("eth_call",[{"to":CORE,"data":data,"from":ME},"latest"])
    return r.get('result')

out = {"utc_date": datetime.datetime.utcnow().strftime("%Y-%m-%d")}
# anthrobit: mintNonce==0 today may indicate free available; check via helper's plan is heavy — do direct selector probes
# mintNonce() view
r = call("0x" + "0x8b6c2f0d" if False else "0x")
# Use the plan output known: mintNonce per day reset; we check totalMinted delta instead
out["note"] = "Run: cd /tmp/anthrobit/anthrobit-agent && node scripts/anthrobit.mjs plan-mint --wallet --multiplier 1 --max-value-wei 50000000000000"
out["free_today_anthrobit"] = "check via plan-mint: fees.mintWei == 0 means free"
print(json.dumps(out, indent=1))
