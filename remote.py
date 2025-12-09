import asyncio, logging, argparse, sys
from greeclimate.device import Device, DeviceInfo, Mode, FanSpeed

# BEÁLLÍTÁSOK
IP, MAC = "192.168.100.19", "58:0d:0d:90:05:a8"

# Néma üzemmód a könyvtárnak
logging.getLogger("greeclimate").setLevel(logging.CRITICAL)

# --- ARGUMENTUMOK FELDOLGOZÁSA (CLI) ---
parser = argparse.ArgumentParser(description="Gree Comfort Pro Vezérlő")
parser.add_argument("-p", "--power", choices=["on", "off", "toggle"], help="Klíma be/kikapcsolása")
parser.add_argument("-t", "--temp", type=int, help="Hőmérséklet beállítása (16-30)")
parser.add_argument("-m", "--mode", choices=["auto", "cool", "heat", "dry", "fan"], help="Üzemmód (auto, cool, heat, dry, fan)")
parser.add_argument("-f", "--fan", choices=["auto", "low", "medium", "high"], help="Ventilátor sebesség")
parser.add_argument("-q", "--quiet", choices=["on", "off"], help="Csendes mód")
parser.add_argument("-u", "--turbo", choices=["on", "off"], help="Turbó mód")
parser.add_argument("-l", "--light", choices=["on", "off"], help="Kijelző fény")

args = parser.parse_args()
# Megnézzük, hogy kaptunk-e bármilyen parancssori argumentumot
CLI_MODE = any([args.power, args.temp, args.mode, args.fan, args.quiet, args.turbo, args.light])

async def main():
    if CLI_MODE:
        print(f"📡 Gyors parancs küldése: {IP}...")
    else:
        print(f"📡 Csatlakozás: {IP}...")

    dev = Device(DeviceInfo(ip=IP, port=7000, mac=MAC.replace(":", ""), name="Gree"))
    
    try:
        await dev.bind()
        # Ha menüben vagyunk, vagy ha hőfokot akarunk állítani, meg kell várni az adatokat
        if not CLI_MODE or args.temp: 
             # Indulási várakozás
            if not CLI_MODE: print("⏳ Adatokra várunk...", end="", flush=True)
            while dev.target_temperature is None:
                await dev.update_state()
                await asyncio.sleep(1)
                if not CLI_MODE: print(".", end="", flush=True)
    except Exception as e: return print(f"\n❌ Hiba: {e}")

    # ==========================================
    # 1. PARANCS SOR (CLI) MÓD
    # ==========================================
    if CLI_MODE:
        print("\n⚙️ Beállítások alkalmazása...")
        
        # Power
        if args.power == "on": dev.power = True
        elif args.power == "off": dev.power = False
        elif args.power == "toggle": dev.power = not dev.power

        # Hőfok
        if args.temp:
            if 16 <= args.temp <= 30: dev.target_temperature = args.temp
            else: print("⚠️ Hiba: Hőfok csak 16-30 lehet!")

        # Mód
        if args.mode:
            if args.mode == "auto": dev.mode = Mode.Auto
            elif args.mode == "cool": dev.mode = Mode.Cool
            elif args.mode == "heat": dev.mode = Mode.Heat
            elif args.mode == "dry": dev.mode = Mode.Dry
            elif args.mode == "fan": dev.mode = Mode.Fan

        # Ventilátor
        if args.fan:
            # Venti állításnál reseteljük a quiet/turbot
            dev.quiet = False
            dev.turbo = False
            if args.fan == "auto": dev.fan_speed = FanSpeed.Auto
            elif args.fan == "low": dev.fan_speed = FanSpeed.Low
            elif args.fan == "medium": dev.fan_speed = FanSpeed.Medium
            elif args.fan == "high": dev.fan_speed = FanSpeed.High

        # Extrák
        if args.quiet:
            dev.quiet = True if args.quiet == "on" else False
            if dev.quiet: dev.turbo = False

        if args.turbo:
            dev.turbo = True if args.turbo == "on" else False
            if dev.turbo: dev.quiet = False
            
        if args.light:
            dev.light = True if args.light == "on" else False

        # Küldés
        await dev.push_state_update()
        print("✅ Parancs elküldve! Kilépés.")
        sys.exit(0) # Itt kilépünk, nem megyünk tovább a menübe

    # ==========================================
    # 2. INTERAKTÍV MENÜ MÓD (HA NINCS ARGUMENTUM)
    # ==========================================
    
    # Segédtáblák
    modes = {
        "Auto": "Automata",  "0": "Automata",
        "Cool": "Hűtés ❄️",   "1": "Hűtés ❄️",
        "Dry":  "Szárít 💧",  "2": "Szárít 💧",
        "Fan":  "Vent 🌀",    "3": "Vent 🌀",
        "Heat": "Fűtés ☀️",   "4": "Fűtés ☀️"
    }
    
    fans = {
        "Auto": "Auto",      "0": "Auto",
        "Low":  "Min",       "1": "Min",
        "MediumLow": "Köz-Min", "2": "Köz-Min",
        "Medium": "Közepes", "3": "Közepes",
        "MediumHigh": "Köz-Max", "4": "Köz-Max",
        "High": "Max",       "5": "Max"
    }

    while True:
        try: await dev.update_state()
        except: pass

        # --- MEGJELENÍTÉS ---
        pwr = "🟢 BE" if dev.power else "🔴 KI"
        cur_t = f"{dev.current_temperature}°C" if dev.current_temperature else "?"
        raw_mode = str(dev.mode).replace("Mode.", "")
        mod = modes.get(raw_mode, raw_mode) 
        
        if dev.quiet: fan = "🤫 CSENDES"
        else:
            raw_fan = str(dev.fan_speed).replace("FanSpeed.", "")
            fan = fans.get(raw_fan, raw_fan)

        sw = "ON ↕️" if getattr(dev, 'swing_vertical', False) else "OFF"
        xfan = "ON 🌬️" if getattr(dev, 'xfan', False) else "OFF"
        turbo = "ON 🚀" if dev.turbo else "OFF"
        light = "ON 💡" if dev.light else "OFF"

        print("\n" + "="*40)
        print(f"❄️  GREE COMFORT PRO ({dev.target_temperature}°C)  ❄️")
        print("="*40)
        print(f" [1] Állapot:    {pwr}")
        print(f" [2] Hőfok:      {dev.target_temperature}°C (Szoba: {cur_t})")
        print(f" [3] Mód:        {mod}")
        print(f" [4] Ventilátor: {fan}")
        print("-" * 40)
        print(f" [5] Turbo:   {turbo:<10} [6] Csendes: {('ON 🤫' if dev.quiet else 'OFF')}")
        print(f" [7] Kijelző: {light:<10} [8] Swing:   {sw}")
        print(f" [9] X-Fan:   {xfan}")
        print("=" * 40)

        c = input(" > Mit állítasz? (0=Kilépés): ")
        
        try:
            valtozas_tortent = False 
            if c == "0": break
            elif c == "1": dev.power = not dev.power; valtozas_tortent = True
            elif c == "2": 
                t = int(input(" >> Hőfok (16-30): "))
                if 16<=t<=30: dev.target_temperature = t; valtozas_tortent = True
            elif c == "3":
                m = input(" >> (a)uto (c)ool (h)eat (d)ry (f)an: ").lower()
                if m in ['a','c','h','d','f']:
                    if m=='a': dev.mode = Mode.Auto
                    elif m=='c': dev.mode = Mode.Cool
                    elif m=='h': dev.mode = Mode.Heat
                    elif m=='d': dev.mode = Mode.Dry
                    elif m=='f': dev.mode = Mode.Fan
                    valtozas_tortent = True
            elif c == "4":
                f = input(" >> (a)uto (1)min..(5)max: ").lower()
                if f in ['a','1','2','3','4','5']:
                    dev.quiet = dev.turbo = False 
                    if f=='a': dev.fan_speed = FanSpeed.Auto
                    elif f=='1': dev.fan_speed = FanSpeed.Low
                    elif f=='2': dev.fan_speed = FanSpeed.MediumLow
                    elif f=='3': dev.fan_speed = FanSpeed.Medium
                    elif f=='4': dev.fan_speed = FanSpeed.MediumHigh
                    elif f=='5': dev.fan_speed = FanSpeed.High
                    valtozas_tortent = True
            elif c == "5": dev.turbo = not dev.turbo; valtozas_tortent = True; 
            elif c == "6": dev.quiet = not dev.quiet; valtozas_tortent = True; 
            elif c == "7": dev.light = not dev.light; valtozas_tortent = True
            elif c == "8": dev.swing_vertical = not getattr(dev, 'swing_vertical', False); valtozas_tortent = True
            elif c == "9": dev.xfan = not getattr(dev, 'xfan', False); valtozas_tortent = True

            # Logikai tisztázás gomboknál
            if valtozas_tortent:
                if dev.turbo: dev.quiet = False
                if dev.quiet: dev.turbo = False

                print("⏳ Végrehajtás", end="", flush=True)
                await dev.push_state_update()
                for _ in range(3):
                    await asyncio.sleep(1)
                    await dev.update_state() 
                    print(".", end="", flush=True)
                print(" Kész!")
            
        except Exception as e: print(f"⚠️ Hiba: {e}")

if __name__ == "__main__":
    try: asyncio.run(main())
    except: pass
    
