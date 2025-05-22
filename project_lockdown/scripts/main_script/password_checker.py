#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Python rewrite of password_checker.sh for lockdown authentication.
Features:
- 2 attempts
- Timeout (default 15s)
- Aggressive countdown timer
- Success/failure file signaling
- Shutdown or sleep on failure
"""
import sys
import time
import threading
import getpass
import os
import signal
import subprocess

CORRECT_PASSWORD = "Secret123"
TIMEOUT = int(sys.argv[1]) if len(sys.argv) > 1 else 15
SUCCESSFILE = os.path.join(os.path.dirname(__file__), ".lockdown_success")
SHUTDOWNFILE = os.path.join(os.path.dirname(__file__), ".lockdown_shutdown")

RED = "\033[0;31m"
GREEN = "\033[0;32m"
YELLOW = "\033[1;33m"
BOLD = "\033[1m"
RESET = "\033[0m"

# Aggressive countdown timer
def ticking_timer(stop_event):
    secs_left = TIMEOUT
    while secs_left > 0 and not stop_event.is_set():
        msg = f"{RED}{BOLD}                   >>> SYSTEM SHUTDOWN IN {secs_left} SECONDS <<< {RESET}"
        print(msg.ljust(80), end="\r", flush=True)
        time.sleep(1)
        secs_left -= 1
    if not stop_event.is_set():
        stop_event.set()

def do_shutdown():
    shutdown_screen()
    # Try to put MacBook to sleep instead of shutdown
    try:
        subprocess.run(["osascript", "-e", 'tell application "System Events" to sleep'], check=False)
    except Exception:
        pass
    sys.exit(1)

def shutdown_screen():
    os.system('clear')
    print(f"{RED}{BOLD}")
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║                     SYSTEM SHUTDOWN                          ║")
    print("╠══════════════════════════════════════════════════════════════╣")
    print("║                   Unauthorized access detected               ║")
    print("║                                                              ║")
    print("║             Initiating IMMEDIATE DEFENSE PROTOCOL            ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print(f"{RESET}")
    try:
        subprocess.run(["afplay", "/System/Library/Sounds/Basso.aiff"], check=False)
    except Exception:
        pass
    time.sleep(2)


def main():
    if os.path.exists(SUCCESSFILE):
        os.remove(SUCCESSFILE)
    stop_event = threading.Event()
    timer_thread = threading.Thread(target=ticking_timer, args=(stop_event,), daemon=True)
    timer_thread.start()

    # Print blinking warning text
    os.system('clear')
    BLINK = "\033[5m"
    print(f"{RED}{BLINK} {BOLD}                  WARNING: Unauthorized access detected!{RESET}")
    print(f"{RED}{BLINK} {BOLD}                  WARNING: IMMEDIATE DEFENSE PROTOCOL ACTIVATED!{RESET}")




    attempts = 0
    while attempts < 2 and not stop_event.is_set():
        try:
            print(f"{BOLD} Password: {RESET}", end="", flush=True)
            # getpass does not support timeout, so use input with timeout workaround
            def get_input(result):
                try:
                    result.append(getpass.getpass(""))
                except Exception:
                    result.append("")
            result = []
            input_thread = threading.Thread(target=get_input, args=(result,))
            input_thread.start()
            input_thread.join(timeout=TIMEOUT)
            if input_thread.is_alive():
                stop_event.set()
                break
            input_val = result[0] if result else ""
        except KeyboardInterrupt:
            stop_event.set()
            break
        print()
        if stop_event.is_set():
            break
        if input_val == CORRECT_PASSWORD:
            stop_event.set()
            print(f"{GREEN}{BOLD}✅ Access granted. Lockdown lifted.{RESET}")
            with open(SUCCESSFILE, "w"): pass
            # Restore Karabiner profile to Default profile
            try:
                subprocess.run(["/usr/local/bin/karabiner_cli", '--select-profile', 'Default profile'], check=False)
            except Exception:
                pass
            # Close all Terminal windows
            try:
                subprocess.run(['osascript', '-e', 'tell application "Terminal" to close every window'], check=False)
            except Exception:
                pass
            sys.exit(0)
        else:
            attempts += 1
            print(f"{RED}{BOLD}Access denied!{RESET}")
            if attempts >= 2:
                stop_event.set()
                with open(SHUTDOWNFILE, "w"): pass
                break
    # If we get here, either timeout or too many attempts
    do_shutdown()

if __name__ == "__main__":
    # If not already launched in a new Terminal, open one with 80x24 size
    if os.environ.get("LOCKDOWN_TERMINAL_LAUNCHED") != "1":
        import shlex
        script_path = os.path.abspath(__file__)
        # Centered bounds for 800x400 window on 1440x900 screen
        bounds = "320,250,1120,650"  # left,top,right,bottom
        launch_cmd = f'''
        tell application "Terminal"
            activate
            set newWin to do script "export LOCKDOWN_TERMINAL_LAUNCHED=1; cd '{os.path.dirname(script_path)}'; python3 '{script_path}' {TIMEOUT}"
            delay 0.2
            set bounds of front window to {{{bounds}}}
        end tell'''
        subprocess.Popen(["osascript", "-e", launch_cmd])
        sys.exit(0)
    # Launch visual_effects.py in a background thread or subprocess in the same terminal
    visual_effects_path = os.path.join(os.path.dirname(__file__), "visual_effects.py")
    visual_proc = None
    if not any("visual_effects.py" in p for p in subprocess.getoutput('ps aux').splitlines()):
        try:
            visual_proc = subprocess.Popen([sys.executable, visual_effects_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            print(f"[password_checker] Warning: Could not launch visual_effects.py: {e}")
    main()
    # Cleanup visual effects process if started
    if visual_proc:
        visual_proc.terminate()