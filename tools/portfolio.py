#!/usr/bin/env python3
"""portfolio.py — full portfolio snapshot (read-only)."""
import json, subprocess, urllib.request

RPC = "https://bsc-dataseed.binance.org/"
ME = "0xf47dD174879d17b8bC0cDCa6B1D487EC7DCaB195"
SHEN = "0x34ec38a5eDaB4477b80A137169Ee46Ea56613E8c"
P0   = "0xB493D1165c153b8551C724692EBCb0Ff440ec2E9"
DOUBAO = "0x51e5c3b0a87ae9dfe147986bcde4e34bcdf1ffff"
NAKA = "0x2D7097E0f28Ea0fEB0b3b44c7d0ee0227d513103"

def rpc(m,p):
    payload = json.dumps({"jsonrpc":"2.0","id":1,"method":m,"params":p})
    r = subprocess.run(["curl","-s","-m","10","-X","POST",RPC,"-H","Content-Type: application/json","-d",payload], capture_output=True, text=True)
    try: return json.loads(r.stdout)
    except: return {}

def call(to, data):
    r = rpc("eth_call",[{"to":to,"data":data},"latest"])
    return r.get('result')

def erc20_bal(to):
    v = call(to, "0x70a08231" + ME.lower().replace("0x","").rjust(64,"0"))
    return int(v,16)/1e18 if v else 0

def erc721_bal(to):
    v = call(to, "0x70a08231" + ME.lower().replace("0x","").rjust(64,"0"))
    return int(v,16) if v else 0

px = json.load(urllib.request.urlopen(urllib.request.Request("https://api.binance.com/api/v3/ticker/price?symbol=BNBUSDT")))['price']
out = {
  "bnb": round(int(rpc("eth_getBalance",[ME,"latest"]).get('result','0x0'),16)/1e18, 6),
  "bnb_usd": None,
  "P0": erc20_bal(P0),
  "doubao_ai": erc20_bal(DOUBAO),
  "shenlong_nft": erc721_bal(SHEN),
  "nakamigos_nft": erc721_bal(NAKA),
}
out["bnb_usd"] = round(out["bnb"] * float(px), 2)
out["shenlong_cards"] = ["#6981 3*","#7055 6*","#7083 7*","#7124 6*"] if out["shenlong_nft"]>=4 else f'{out["shenlong_nft"]} NFT'
print(json.dumps(out, indent=1))
