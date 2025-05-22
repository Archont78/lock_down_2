#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Python rewrite of visual_effects.sh: Simulates animated skull and attack phases for lockdown.
Runs the animated skull (from laugh_skull.py) and attack simulation in parallel.
"""
import threading
import time
import random
import sys
import os

RED = "\033[0;31m"
YELLOW = "\033[1;33m"
RESET = "\033[0m"
BOLD = "\033[1m"

phases = [
    "RECONNAISSANCE", "PORT SCAN", "VULNERABILITY ANALYSIS",
    "DDOS ATTACK", "CREDENTIAL BRUTE-FORCE", "PRIVILEGE ESCALATION",
    "BACKDOOR DEPLOYMENT", "DATA EXFILTRATION", "LOG ERASURE", "TRACK COVERAGE"
]
cinematic_cmds = [
    "rm -rf / --no-preserve-root",
    "dd if=/dev/zero of=/dev/sda bs=1M",
    "shred -n3 -z /Volumes/Data/*",
    "nc -lvp 4444 -e /bin/bash",
    "nmap -sS 192.168.0.0/24",
    "iptables -F; iptables -I INPUT -j DROP",
    "mkfs.ext4 /dev/sda1",
    "echo 'Malware XYZ deployed'"
]
defense_snippets = [
    "IDS triggered",
    "WAF blocking traffic",
    "Firewall dropped packets",
    "EDR process killed",
    "SIEM anomaly logged"
]

def draw_bar(progress, width=40):
    filled = int(progress * width / 100)
    empty = width - filled
    bar = '[' + ('#' * filled) + (' ' * empty) + f'] {progress:3d}%'
    return bar

def attack_simulation():
    # Start the skull animation in the same terminal (foreground)
    skull_thread = threading.Thread(target=run_skull, daemon=True)
    skull_thread.start()
    try:
        while True:
            for phase in phases:
                print(f"\n{YELLOW}>> {phase}{RESET}")
                for i in range(0, 101, 10):
                    time.sleep(0.2)
                    if random.randint(0, 24) == 0:
                        cmd = random.choice(cinematic_cmds)
                        print(f"{RED}[EXEC] {cmd}{RESET}")
                    if random.randint(0, 19) == 0:
                        defense = random.choice(defense_snippets)
                        print(f"{YELLOW}[DEFENSE] {defense}{RESET}")
                    print(f"   \r{draw_bar(i)}", end="", flush=True)
                print(f"\r   {draw_bar(100)}  {RED}:: PHASE {phase} COMPLETE ::{RESET}")
    except KeyboardInterrupt:
        pass

def run_skull():
    # Run the skull animation in the same terminal
    import importlib.util
    skull_path = os.path.join(os.path.dirname(__file__), "laugh_skull.py")
    spec = importlib.util.spec_from_file_location("laugh_skull", skull_path)
    laugh_skull = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(laugh_skull)

def main():
    sim_thread = threading.Thread(target=attack_simulation, daemon=True)
    sim_thread.start()
    try:
        while sim_thread.is_alive():
            sim_thread.join(0.5)
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()
