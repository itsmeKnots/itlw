import subprocess, time, sys

PINS = [int(x) for x in sys.argv[1:]] or [7, 8, 9, 18]

def run(*a):
    return subprocess.run(a, capture_output=True, text=True).stdout

def level(g):
    out = run("pinctrl", "get", str(g))
    return "hi" if "| hi" in out else "lo" if "| lo" in out else "?"

fails = {g: 0 for g in PINS}
runs = 0
try:
    while True:
        runs += 1
        for g in PINS:
            run("pinctrl", "set", str(g), "ip", "pu"); time.sleep(0.05)
            u = level(g)
            run("pinctrl", "set", str(g), "ip", "pd"); time.sleep(0.05)
            d = level(g)
            if not (u == "hi" and d == "lo"):
                fails[g] += 1
        line = "  ".join(f"GPIO{g}: {fails[g]} fail" for g in PINS)
        print(f"\rrun {runs}  {line}   ", end="", flush=True)
        time.sleep(0.4)
except KeyboardInterrupt:
    print("\n\nSummary after", runs, "runs:")
    for g in PINS:
        v = "RELIABLE" if fails[g] == 0 else f"UNRELIABLE ({fails[g]}/{runs})"
        print(f"  GPIO{g}: {v}")
