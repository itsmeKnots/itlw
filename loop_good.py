from gpiozero import OutputDevice, InputDevice
from time import sleep

out = OutputDevice("BOARD11")
inp = InputDevice("BOARD13", pull_up=None, active_state=True)
for v in (1, 0, 1, 0):
    out.value = v
    sleep(0.1)
    print("set", v, "read", int(inp.value))
