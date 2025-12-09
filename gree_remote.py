import asyncio, logging, argparse, sys
from greeclimate.device import Device, DeviceInfo, Mode, FanSpeed

# ==========================================
# ❄️ GREE COMFORT PRO CONTROLLER
# 🛠️ Author: Bence Reményi
# ==========================================

# --- Configuration ---
IP, MAC = "192.168.100.19", "58:0d:0d:90:05:a8"

# Mute gree library noise
logging.getLogger("greeclimate").setLevel(logging.CRITICAL)

# --- CLI Argument Parsing ---
parser = argparse.ArgumentParser(description="Gree Comfort Pro CLI Controller by Bence Reményi")
parser.add_argument("-p", "--power", choices=["on", "off", "toggle"], help="Turn AC Power On/Off/Toggle")
parser.add_argument("-t", "--temp", type=int, help="Set Temperature (16-30)")
parser.add_argument("-m", "--mode", choices=["auto", "cool", "heat", "dry", "fan"], help="Set Operation Mode")
parser.add_argument("-f", "--fan", choices=["auto", "low", "medium", "high"], help="Set Fan Speed")
parser.add_argument("-q", "--quiet", choices=["on", "off"], help="Quiet Mode (Silent)")
parser.add_argument("-u", "--turbo", choices=["on", "off"], help="Turbo Mode")
parser.add_argument("-l", "--light", choices=["on", "off"], help="Display Light")

args = parser.parse_args()
CLI_MODE = any([args.power, args.temp, args.mode, args.fan, args.quiet, args.turbo, args.light])

async def main():
    if CLI_MODE:
        print(f"📡 Sending command to: {IP}...")
    else:
        print(f"📡 Connecting to: {IP}...")

    dev = Device(DeviceInfo(ip=IP, port=7000, mac=MAC.replace(":", ""), name="GreeAC"))
    
    try:
        await dev.bind()
        # Wait for valid data on startup
        if not CLI_MODE or args.temp: 
            if not CLI_MODE: print("⏳ Fetching data...", end="", flush=True)
            while dev.target_temperature is None:
                await dev.update_state()
                await asyncio.sleep(1)
                if not CLI_MODE: print(".", end="", flush=True)
    except Exception as e: return print(f"\n❌ Error: {e}")

    # ==========================================
    # 1. CLI MODE (One-shot command)
    # ==========================================
    if CLI_MODE:
        print("\n⚙️ Applying settings...")
        
        if args.power == "on": dev.power = True
        elif args.power == "off": dev.power = False
        elif args.power == "toggle": dev.power = not dev.power

        if args.temp:
            if 16 <= args.temp <= 30: dev.target_temperature = args.temp
            else: print("⚠️ Error: Temp must be between 16-30!")

        if args.mode:
            modes = {"auto": Mode.Auto, "cool": Mode.Cool, "heat": Mode.Heat, "dry": Mode.Dry, "fan": Mode.Fan}
            if args.mode in modes: dev.mode = modes[args.mode]

        if args.fan:
            # Reset specific modes when changing fan speed
            dev.quiet = False
            dev.turbo = False
            fans = {"auto": FanSpeed.Auto, "low": FanSpeed.Low, "medium": FanSpeed.Medium, "high": FanSpeed.High}
            if args.fan in fans: dev.fan_speed = fans[args.fan]

        if args.quiet:
            dev.quiet = (args.quiet == "on")
            if dev.quiet: dev.turbo = False

        if args.turbo:
            dev.turbo = (args.turbo == "on")
            if dev.turbo: dev.quiet = False
            
        if args.light:
            dev.light = (args.light == "on")

        await dev.push_state_update()
        print("✅ Done.")
        sys.exit(0)

    # ==========================================
    # 2. INTERACTIVE MENU MODE
    # ==========================================
    
    # Display Mappings (supports numeric codes from device)
    modes = {
        "Auto": "Auto",     "0": "Auto",
        "Cool": "Cool ❄️",   "1": "Cool ❄️",
        "Dry":  "Dry 💧",    "2": "Dry 💧",
        "Fan":  "Fan 🌀",    "3": "Fan 🌀",
        "Heat": "Heat ☀️",   "4": "Heat ☀️"
    }
    
    fans = {
        "Auto": "Auto",      "0": "Auto", 
        "Low": "Min",        "1": "Min",
        "MediumLow": "Low-Mid", "2": "Low-Mid", 
        "Medium": "Mid",     "3": "Mid",
        "MediumHigh": "Mid-High", "4": "Mid-High", 
        "High": "Max",       "5": "Max"
    }

    while True:
        try: await dev.update_state()
        except: pass

        # Prepare Display Data
        pwr = "🟢 ON" if dev.power else "🔴 OFF"
        cur_t = f"{dev.current_temperature}°C" if dev.current_temperature else "?"
        
        raw_mode = str(dev.mode).replace("Mode.", "")
        mod = modes.get(raw_mode, raw_mode) 
        
        if dev.quiet: fan = "🤫 QUIET"
        else:
            raw_fan = str(dev.fan_speed).replace("FanSpeed.", "")
            fan = fans.get(raw_fan, raw_fan)

        sw = "ON ↕️" if getattr(dev, 'swing_vertical', False) else "OFF"
        xfan = "ON 🌬️" if getattr(dev, 'xfan', False) else "OFF"
        turbo = "ON 🚀" if dev.turbo else "OFF"
        light = "ON 💡" if dev.light else "OFF"

        # Dashboard UI
        print("\n" + "="*40)
        print(f"❄️  GREE COMFORT PRO ({dev.target_temperature}°C)  ❄️")
        print("="*40)
        print(f" [1] Power:      {pwr}")
        print(f" [2] Target:     {dev.target_temperature}°C (Room: {cur_t})")
        print(f" [3] Mode:       {mod}")
        print(f" [4] Fan Speed:  {fan}")
        print("-" * 40)
        print(f" [5] Turbo:   {turbo:<10} [6] Quiet:   {('ON 🤫' if dev.quiet else 'OFF')}")
        print(f" [7] Light:   {light:<10} [8] Swing:   {sw}")
        print(f" [9] X-Fan:   {xfan}")
        print("=" * 40)

        c = input(" > Select option (0=Exit): ")
        
        try:
            changed = False 
            if c == "0": break
            elif c == "1": dev.power = not dev.power; changed = True
            elif c == "2": 
                t = int(input(" >> Set Temp (16-30): "))
                if 16<=t<=30: dev.target_temperature = t; changed = True
            elif c == "3":
                m = input(" >> (a)uto (c)ool (h)eat (d)ry (f)an: ").lower()
                if m in ['a','c','h','d','f']:
                    mode_map = {'a': Mode.Auto, 'c': Mode.Cool, 'h': Mode.Heat, 'd': Mode.Dry, 'f': Mode.Fan}
                    dev.mode = mode_map[m]
                    changed = True
            elif c == "4":
                f = input(" >> (a)uto (1)min..(5)max: ").lower()
                if f in ['a','1','2','3','4','5']:
                    dev.quiet = dev.turbo = False # Prevent conflict
                    fan_map = {'a': FanSpeed.Auto, '1': FanSpeed.Low, '2': FanSpeed.MediumLow, '3': FanSpeed.Medium, '4': FanSpeed.MediumHigh, '5': FanSpeed.High}
                    dev.fan_speed = fan_map[f]
                    changed = True
            elif c == "5": dev.turbo = not dev.turbo; changed = True
            elif c == "6": dev.quiet = not dev.quiet; changed = True
            elif c == "7": dev.light = not dev.light; changed = True
            elif c == "8": dev.swing_vertical = not getattr(dev, 'swing_vertical', False); changed = True
            elif c == "9": dev.xfan = not getattr(dev, 'xfan', False); changed = True

            # Execution logic
            if changed:
                if dev.turbo: dev.quiet = False
                if dev.quiet: dev.turbo = False

                print("⏳ Executing", end="", flush=True)
                await dev.push_state_update()
                
                # Wait for AC confirmation (3 sec)
                for _ in range(3):
                    await asyncio.sleep(1)
                    await dev.update_state() 
                    print(".", end="", flush=True)
                print(" Done!")
            
        except Exception as e: print(f"⚠️ Error: {e}")

if __name__ == "__main__":
    try: asyncio.run(main())
    except: pass
