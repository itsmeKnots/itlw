import time
from smbus2 import SMBus

ADDR = 0x48
# Single-shot, +/-4.096 V range (matches ADS_GAIN = 1), 128 SPS
CONFIG_HI = {0: 0xC3, 1: 0xD3}  # A0, A1 versus GND

with SMBus(1) as bus:
    while True:
        out = []
        for ch in (0, 1):
            bus.write_i2c_block_data(ADDR, 0x01, [CONFIG_HI[ch], 0x83])
            time.sleep(0.01)
            hi, lo = bus.read_i2c_block_data(ADDR, 0x00, 2)
            raw = (hi << 8) | lo
            if raw & 0x8000:
                raw -= 65536
            out.append(f"A{ch}: {raw * 4.096 / 32768:5.3f} V")
        print("   ".join(out))
        time.sleep(0.2)