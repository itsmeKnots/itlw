from gpiozero import OutputDevice, InputDevice
from time import sleep

out = OutputDevice("BOARD15")
inp = InputDevice("BOARD19", pull_up=None, active_state=True)
for v in (1, 0, 1, 0):
    out.value = v
    sleep(0.1)
    print("set", v, "read", int(inp.value))
