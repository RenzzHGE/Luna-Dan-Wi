#!/usr/bin/env python3
"""php2shell_check — CVE-2026-109618/109619 (PHP2Shell) version checker.
Usage: php2shell_check.sh [version]   (default: `php -r 'echo PHP_VERSION;'`)
Vulnerable: 8.0-8.1 EOL, 8.2.x < 8.2.35, 8.3.x < 8.3.36, 8.4.x < 8.4.27, 8.5.x < 8.5.12
Also scan a host: php2shell_check.sh --host example.com  (reads X-Powered-By)"""
import sys, re, subprocess
FIXED = {(8,2):(8,2,35),(8,3):(8,3,36),(8,4):(8,4,27),(8,5):(8,5,12)}
def verdict(v):
    t = tuple(int(x) for x in re.findall(r"\d+", v)[:3])
    if len(t)<3: return "UNKNOWN"
    f = FIXED.get(t[:2])
    if f: return "PATCHED" if t>=f else "VULNERABLE"
    return "PATCHED" if t>=(8,6,0) else "UNKNOWN"
if len(sys.argv)>2 and sys.argv[1]=="--host":
    host=sys.argv[2]
    out=subprocess.run(["curl","-sI","-m","8",f"https://{host}/"],capture_output=True,text=True).stdout.lower()
    m=re.search(r"x-powered-by:.*php/([\d.]+)",out)
    print(f"{host}: " + (f"PHP {m.group(1)} -> {verdict(m.group(1))}" if m else "no PHP banner (cannot fingerprint; may still run PHP)"))
else:
    v=sys.argv[1] if len(sys.argv)>1 else subprocess.run(["php","-r","echo PHP_VERSION;"],capture_output=True,text=True).stdout
    print(f"PHP {v}: {verdict(v)}")
