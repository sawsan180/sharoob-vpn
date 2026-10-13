#!/data/data/com.termux/files/usr/bin/python3
import sys, os, time, random, select, termios, tty, subprocess, signal

STATUS_FILE = os.path.expanduser("~/.sharoob/status")
SETTINGS_FILE = os.path.expanduser("~/.sharoob/settings.conf")
SHAROOB_BIN = "/data/data/com.termux/files/usr/bin/sharoob.bin"
LOG_FILE = os.path.expanduser("~/.sharoob/logs/vpn_%s.log" % time.strftime("%Y-%m-%d"))

RESET="\033[0m"; CLEAR="\033[2J\033[H"; ERASE="\033[J"
HIDE="\033[?25l"; SHOW="\033[?25h"; NOWRAP="\033[?7l"; WRAP="\033[?7h"

GH="\033[1;92m"; GB="\033[1;32m"; GT="\033[2;32m"
RH="\033[1;91m"; RB="\033[1;31m"; RT="\033[2;31m"
W="\033[1;97m"; Y="\033[1;33m"; C="\033[1;36m"
MENU_MARK = "\x01"
G_BG = "\033[48;5;22m"; R_BG = "\033[48;5;52m"

LOGO = [
    "████ █  █ ████ ████ ████ ████ ████",
    "█    █  █ █  █ █  █ █  █ █  █ █  █",
    "████ ████ ████ ████ █  █ █  █ ████",
    "   █ █  █ █  █ █  █ █  █ █  █ █  █",
    "████ █  █ █  █ █  █ ████ ████ ████",
]
PW = 44
CHARS = "01ﺍﺏﺕﺙﺝﺡﺥﺩﺫﺭﺯﺱﺵﺹﺽﻁﻅﻉﻍﻑﻕﻙﻝﻡﻥﻩﻭﻱ"

WINCH = False
def _on_winch(s, f):
    global WINCH
    WINCH = True
try: signal.signal(signal.SIGWINCH, _on_winch)
except Exception: pass

COLS = 60; ROWS = 30
PANEL_L = 5; PANEL_T = 5; PANEL_R = 49; PANEL_B = 23
drops = []; speeds = []

def get_size():
    try:
        s = os.get_terminal_size(); return s.columns, s.lines
    except: return 60, 30

def lock_size():
    global COLS, ROWS, PANEL_L, PANEL_T, PANEL_R, PANEL_B, drops, speeds
    COLS, ROWS = get_size()
    PANEL_L = max(1, (COLS - PW)//2)
    PANEL_T = max(0, (ROWS - 20)//2)
    PANEL_R = PANEL_L + PW
    PANEL_B = PANEL_T + 18
    drops = [random.randint(-ROWS, 0) for _ in range(COLS+2)]
    speeds = [random.randint(1,2) for _ in range(COLS+2)]

def read_status():
    try:
        with open(STATUS_FILE) as f: return f.read().strip()
    except: return "disconnected"

def get_lang():
    try:
        with open(SETTINGS_FILE) as f:
            for ln in f:
                if ln.startswith("LANG="):
                    return ln.split("=",1)[1].strip()
    except: pass
    return "en"

def set_lang(v):
    try:
        lines = []
        found = False
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE) as f:
                for ln in f:
                    if ln.startswith("LANG="):
                        lines.append(f"LANG={v}\n"); found = True
                    else:
                        lines.append(ln)
        if not found:
            lines.append(f"LANG={v}\n")
        with open(SETTINGS_FILE, "w") as f:
            f.writelines(lines)
    except Exception as e:
        pass

def read_version():
    try:
        with open("/data/data/com.termux/files/usr/bin/.sharoob_version") as f:
            return f.read().strip()
    except: pass
    return "?"

def center(text, width):
    text = text[:width]
    p = width - len(text)
    l = p//2
    return " "*l + text + " "*(p-l)

def update_rain():
    for i in range(len(drops)):
        drops[i] += speeds[i]
        if drops[i] > ROWS + 3:
            drops[i] = random.randint(-25, -5)
            speeds[i] = random.randint(1,2)

def rain_char(col, row, head, body, tail):
    if col >= len(drops): return " "
    d = drops[col] - row
    if d == 0: return head + random.choice(CHARS) + RESET
    if 0 < d < 3: return body + random.choice(CHARS) + RESET
    if 3 <= d < 8: return tail + random.choice(CHARS) + RESET
    return " "

def menu_items(lang, connected):
    if lang == "ar":
        return [
            ("1)  " + ("ﻞﺼﺘﻣ" if connected else "ﻞﺼﺘﻣ ﺮﻴﻏ")),
            "2)  ﺔﻟﺎﺤﻟﺍ",
            "3)  ﺕﺎﻤﻠﻌﻟﺍ",
            "4)  ﺕﺍﺩﺍﺪﻋﻹﺍ",
            "5)  ﺓﺪﻋﺎﺴﻣ",
            "6)  [ For English ]",
            "7)  ﺝﻭﺮﺧ",
        ]
    else:
        return [
            ("1)  " + ("Disconnect" if connected else "Connect")),
            "2)  Status",
            "3)  View Logs",
            "4)  Settings",
            "5)  Help",
            "6)  [ ﺔﻴﺑﺮﻌﻟﺍ ]",
            "7)  Exit",
        ]

def build_panel(version, connected, state, lang, overlay=None):
    lines = [""]
    for lg in LOGO: lines.append(center(lg, PW))
    lines.append("")
    lines.append(center(f"V P N  ·  v{version}", PW))
    lines.append("")
    if overlay:
        # Show overlay content centered
        ov = overlay.split("\n")
        # max 8 lines
        ov = ov[:8]
        for _ in range(7 - len(ov)): lines.append("")
        for ol in ov:
            lines.append(MENU_MARK + center(ol, PW-2))
        while len(lines) < 16: lines.append("")
    elif state == "connecting":
        lines.append("")
        msg = "ﺔﻴﻟﺎﺘﻟﺍ ﺔﻈﺘﻧﺍ..." if lang == "ar" else "CONNECTING..."
        lines.append(MENU_MARK + center(msg, PW-2))
        msg2 = "..." if lang == "ar" else "please wait"
        lines.append(MENU_MARK + center(msg2, PW-2))
        for _ in range(5): lines.append("")
    else:
        items = menu_items(lang, connected)
        for it in items: lines.append(MENU_MARK + it)
    lines.append("")
    return lines

def maybe_relock():
    global WINCH
    if not WINCH: return False
    WINCH = False
    time.sleep(0.35)
    if WINCH: WINCH = False
    lock_size()
    sys.stdout.write(CLEAR)
    return True

def render(version, state="menu", overlay=None):
    maybe_relock()
    connected = (read_status() == "connected")
    lang = get_lang()
    head, body, tail = (GH, GB, GT) if connected else (RH, RB, RT)
    menu_bg = G_BG if connected else R_BG
    panel = build_panel(version, connected, state, lang, overlay)

    buf = []
    for row in range(ROWS):
        buf.append(f"\033[{row+1};1H")
        parts = []
        for col in range(COLS):
            if PANEL_L <= col < PANEL_R and PANEL_T <= row < PANEL_B:
                pr = row - PANEL_T; pc = col - PANEL_L
                if pr < len(panel) and pc < len(panel[pr]):
                    pline = panel[pr]
                    if pline.startswith(MENU_MARK):
                        content = pline[1:].ljust(PW-2)
                        ch = content[pc] if pc < len(content) else " "
                        parts.append(menu_bg + W + ch + RESET)
                    else:
                        ch = pline[pc]
                        if ch == " ": parts.append(" ")
                        elif pr < 6: parts.append(head + ch + RESET)
                        elif overlay: parts.append(C + ch + RESET)
                        elif "CONNECT" in pline or "ﺔﻈﺘﻧﺍ" in pline:
                            parts.append(Y + ch + RESET)
                        else: parts.append(W + ch + RESET)
                else:
                    parts.append(" ")
            else:
                parts.append(rain_char(col, row, head, body, tail))
        buf.append("".join(parts))

    if overlay:
        hint_en = "Press any key to return"
        hint_ar = "ﺓﺩﻮﻌﻠﻟ ﺏﺎﺴﺣﺃ ﺢﻔﺗﺍ"
        hint = hint_ar if lang == "ar" else hint_en
    else:
        hint_en = "Choice (1-7): "
        hint_ar = " :(7-1) ﺭﺎﻴﺘﺧﻹﺍ"
        hint = hint_ar if lang == "ar" else hint_en
    buf.append(f"\033[{ROWS};1H")
    buf.append(" "*max(0,(COLS-len(hint))//2) + W + hint + RESET)
    buf.append(ERASE)
    sys.stdout.write("".join(buf)); sys.stdout.flush()

def get_key(t=0.08):
    if select.select([sys.stdin], [], [], t)[0]: return sys.stdin.read(1)
    return None

def show_overlay(version, content):
    """Display content for a few seconds, wait for keypress."""
    old = termios.tcgetattr(sys.stdin)
    try:
        tty.setcbreak(sys.stdin.fileno())
        # Flush any pending keys
        while select.select([sys.stdin], [], [], 0.05)[0]:
            sys.stdin.read(1)
        start = time.time()
        while time.time() - start < 5:
            update_rain()
            render(version, "overlay", overlay=content)
            k = get_key(0.08)
            if k is not None: return
            maybe_relock()
    finally:
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old)

def run_menu(version):
    old = termios.tcgetattr(sys.stdin)
    try:
        tty.setcbreak(sys.stdin.fileno())
        lock_size()
        sys.stdout.write(HIDE + NOWRAP + CLEAR)
        while True:
            update_rain()
            render(version, "menu")
            k = get_key(0.08)
            if k is not None and k in "1234567": return k
    finally:
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old)
        sys.stdout.write(WRAP + SHOW + RESET)

def run_action(action, version):
    proc = subprocess.Popen([SHAROOB_BIN, action],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL)
    old = termios.tcgetattr(sys.stdin)
    try:
        tty.setcbreak(sys.stdin.fileno())
        lock_size()
        sys.stdout.write(HIDE + NOWRAP + CLEAR)
        while proc.poll() is None:
            update_rain()
            render(version, "connecting")
            time.sleep(0.08)
    finally:
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old)
        sys.stdout.write(WRAP + SHOW + RESET)

def do_status(version):
    st = read_status()
    ip = "?"
    try:
        r = subprocess.check_output(
            ["curl", "-s", "--max-time", "5", "https://api.ipify.org"],
            stderr=subprocess.DEVNULL, timeout=6)
        ip = r.decode(errors="ignore").strip() or "?"
    except: pass
    if st == "connected":
        return f"VPN: CONNECTED\nIP: {ip}"
    return "VPN: DISCONNECTED"

def do_logs(version):
    try:
        with open(LOG_FILE) as f:
            lines = f.readlines()[-6:]
        return "".join(lines).strip()[:120]
    except:
        return "No logs"

def do_settings(version):
    try:
        with open(SETTINGS_FILE) as f:
            return f.read().strip()[:150]
    except:
        return "No settings"

def do_help(version):
    return "Sharoob VPN\nConnect: tap 1\nToggle lang: tap 6\nExit: tap 7"

def do_stop():
    """Stop VPN directly from Python (avoids shc self-kill issue)."""
    for name in ["aether", "busybox"]:
        subprocess.run(["pkill", "-9", "-x", name],
                       stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
    subprocess.run(["am", "force-stop", "com.github.kr328.clash"],
                   stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
    try:
        with open(STATUS_FILE, "w") as f:
            f.write("disconnected\n")
    except: pass

def main():
    version = read_version()
    try:
        while True:
            k = run_menu(version)
            if k == "7":
                sys.stdout.write(CLEAR + SHOW); print("Goodbye!"); break
            elif k == "1":
                conn = (read_status() == "connected")
                if conn:
                    do_stop()
                else:
                    run_action("--start", version)
            elif k == "2":
                show_overlay(version, do_status(version))
            elif k == "3":
                show_overlay(version, do_logs(version))
            elif k == "4":
                show_overlay(version, do_settings(version))
            elif k == "5":
                show_overlay(version, do_help(version))
            elif k == "6":
                cur = get_lang()
                set_lang("ar" if cur == "en" else "en")
                # Menu will refresh automatically
    except KeyboardInterrupt:
        sys.stdout.write(SHOW + RESET + "\n")

if __name__ == "__main__":
    main()

