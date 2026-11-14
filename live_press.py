import time, threading
from gpiozero import Button

PINS = {"np_plus_1": 18, "np_minus_1": 9, "np_plus_10": 8, "np_minus_10": 7}
edges = {n: [] for n in PINS}
lock = threading.Lock()

def make(name, pin):
    b = Button(pin, pull_up=True, bounce_time=None)
    def hit():
        with lock:
            edges[name].append(time.time())
    b.when_pressed = hit
    b.when_released = hit
    return b

btns = [make(n, p) for n, p in PINS.items()]
print("Press buttons one at a time. Ctrl+C to stop.")
try:
    while True:
        time.sleep(0.4)
        now = time.time()
        with lock:
            for n, ts in edges.items():
                if ts and now - ts[-1] > 0.4:
                    c = len(ts)
                    verdict = "clean" if c == 2 else "BOUNCY" if c > 2 else "odd (1 edge)"
                    print(f"{n:12s} edges={c:3d}  {verdict}")
                    ts.clear()
except KeyboardInterrupt:
    pass
