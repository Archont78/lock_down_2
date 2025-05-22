#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Python rewrite of lockdown.sh: master controller for lockdown system.
Launches and monitors subprocesses, handles cleanup, and manages authentication loop.
"""
import os
import sys
import subprocess
import time
import signal
import atexit
from pathlib import Path

# === Config ===
DIR = Path(__file__).parent.resolve()
TIMEOUT = 15  # seconds, must match password_checker
PASSWORD_SCRIPT = DIR / "password_checker.py"
INPUT_BLOCKER = DIR / "input_blocker2.py"
KEYBOARD_INTERCEPTOR = DIR / "keyboard_interceptor.py" 
VISUAL_EFFECTS = DIR / "visual_effects.py"
SUCCESSFILE = DIR / ".lockdown_success"
LOCKFILE = DIR / ".lockdown_running"
SHUTDOWNFILE = DIR / ".lockdown_shutdown"

# === Colors ===
RED = "\033[0;31m"
YELLOW = "\033[1;33m"
RESET = "\033[0m"
BOLD = "\033[1m"

# === State ===
procs = {}

# === Cleanup ===
def cleanup():
    for name, proc in procs.items():
        if proc and proc.poll() is None:
            try:
                proc.terminate()
                proc.wait(timeout=2)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass
    # No longer using Karabiner
    if LOCKFILE.exists():
        LOCKFILE.unlink()
    # Remove success and shutdown files
    if SUCCESSFILE.exists():
        SUCCESSFILE.unlink()
    if SHUTDOWNFILE.exists():
        SHUTDOWNFILE.unlink()

# Register cleanup for normal exit
atexit.register(cleanup)

def emergency_shutdown(msg):
    print(f"{RED}EMERGENCY: {msg} Shutting down all processes and exiting.{RESET}")
    cleanup()
    sys.exit(1)

def signal_handler(signum, frame):
    emergency_shutdown(f"Signal {signum} received.")

# Add more signals for robust cleanup
for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP, signal.SIGQUIT):
    signal.signal(sig, signal_handler)

# Prevent multiple instances
if LOCKFILE.exists():
    print(f"{RED}Lockdown already running!{RESET}")
    sys.exit(1)
LOCKFILE.touch()

try:
    while True:
        if SUCCESSFILE.exists():
            SUCCESSFILE.unlink()
            
        # Step 1: Start keyboard interceptor to block system shortcuts
        if not any(KEYBOARD_INTERCEPTOR.name in p for p in subprocess.getoutput('ps aux').splitlines()):
            print("[lockdown] Launching keyboard_interceptor.py...")
            procs['keyboard'] = subprocess.Popen([sys.executable, str(KEYBOARD_INTERCEPTOR)], 
                                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            print("[lockdown] keyboard_interceptor.py already running.")

        # Step 2: Start visual effects in a new, maximized Terminal window
        osa_visual_cmd = f'''
        tell application "Terminal"
            activate
            set visWin to do script "cd '{DIR}'; {sys.executable} '{VISUAL_EFFECTS}'"
            delay 0.2
            set bounds of front window to {{0, 22, 1440, 900}} -- Adjust for your screen resolution
        end tell'''
        subprocess.Popen(["osascript", "-e", osa_visual_cmd])
        time.sleep(1)

        # Step 3: Start input blocker after 1 second
        if not any(INPUT_BLOCKER.name in p for p in subprocess.getoutput('ps aux').splitlines()):
            print("[lockdown] Launching input_blocker2.py...")
            procs['mouse'] = subprocess.Popen([sys.executable, str(INPUT_BLOCKER)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            print("[lockdown] input_blocker2.py already running.")

        # Step 4: Start password checker in a new Terminal window sized 80x24
        osa_pass_cmd = f'''
        tell application "Terminal"
            activate
            set passWin to do script "cd '{DIR}'; {sys.executable} '{PASSWORD_SCRIPT}' {TIMEOUT}"
            delay 0.2
            set bounds of front window to {{100, 100, 900, 500}} -- Approx 80x24 chars
        end tell'''
        subprocess.Popen(["osascript", "-e", osa_pass_cmd])

        # Wait for password_checker.py to finish
        while any('password_checker.py' in p for p in subprocess.getoutput('ps aux').splitlines()):
            time.sleep(1)

        # Check for success
        if SUCCESSFILE.exists():
            SUCCESSFILE.unlink()
            cleanup()
            print(f"{YELLOW}Lockdown lifted. Welcome back.{RESET}")
            sys.exit(0)
        # Else: failed, restart loop
        cleanup()
        print(f"{RED}Authentication failed. Start up lockdown...{RESET}")
        time.sleep(1)
finally:
    cleanup()
