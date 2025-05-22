#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт визуально эмулирует взлом системы (стилистика Watch Dogs 2).
Запуск: в терминале MacOS запустить этот файл (python3 scriptname.py).
Остановка: нажмите Ctrl+C (KeyboardInterrupt) для выхода.
"""
import time
import random
import sys
import subprocess

# === Maximize Terminal window (macOS only) ===
def maximize_terminal():
    try:
        subprocess.run([
            'osascript', '-e',
            'tell application "Terminal" to set bounds of front window to {0, 0, 2000, 1200}'
        ], check=True)
    except Exception:
        pass  # Ignore if not on macOS or fails

maximize_terminal()

# ASCII-арт смеющегося черепа с косой (в стиле Watch Dogs 2).
# Каждый элемент списка - строка ASCII-рисунка.
# Исходный кадр (neutral)
skull_frame_0 = [
     "                 _,.-------.,_",
    "             ,;~'             '~;,",
    "           ,;                     ;,",
    "          ;                         ;",
    "         ,'                         ',",
    "        ,;                           ;,",
    "        ; ;      .           .      ; ;",
    "        | ;   ______       ______   ; |",
    "        |  `/~\"     ~\" . \"~     \"~\\'  |",
    "        |  ~  ,-~~~^~, | ,~^~~~-,  ~  |",
    "         |   |        }:{        |   |",
    "         |   l       / | \\       !   |",
    "         .~  (__,.--\" .^. \"--.,__)  ~.",
    "         |     ---;' / | \\ `;---     |",
    "          \\__.       \\/^\\/       .__/",
    "           V| \\                 / |V",
    "            | |T~\\___!___!___/~T| |",
    "            | |`IIII_I_I_I_IIII'| |",
    "            |  \\,III I I I III,/  |",
    "             \\   `~~~~~~~~~~'    /",
    "               \\   .       .   /",
    "                 \\.    ^    ./",
    "                   ^~~~^~~~^"
]

# Кадр 1: чуть более широкий рот (улыбка)
skull_frame_1 = [
    "                 _,.-------.,_",
    "             ,;~'             '~;,",
    "           ,;        _          ;,",
    "          ;        (   )          ;",
    "         ,'        (_ )           ',",
    "        ,;           `             ;,",
    "        ; ;      .           .      ; ;",
    "        | ;   ______       ______   ; |",
    "        |  `/~\"    ~\" . \"~    \"~\\'  |",
    "        |  ~ ,-~~~^~, | ,~^~~~-, ~  |",
    "         |  /|       }:{       |\\  |",
    "         |   l      / | \\      !   |",
    "         .~ (__,.--\" .^. \"--.,__) ~.",
    "         |    ---;' / | \\ `;---    |",
    "          \\__.      \\/o\\/      .__/",
    "           V| \\                 / |V",
    "            | |T~\\___!___!___/~T| |",
    "            | |`IIII_I_I_I_IIII'| |",
    "            |  \\,III I I I III,/  |",
    "             \\   `~~~~~~~~~~'    /",
    "               \\   .  .  .    /",
    "                 \\.   -   ./",
    "                   -~~~-~~~-"
]


# Кадр 2: открытая челюсть (глубокий смех)
skull_frame_2 = [
    "                 _,.-------.,_",
    "             ,;~'             '~;,",
    "           ,;     \\     /       ;,",
    "          ;       (x)   (x)      ;",
    "         ,'       \\  ___  /       ',",
    "        ,;         \\|   |/         ;,",
    "        ; ;      .   \\ /   .      ; ;",
    "        | ;   ______\\_/_______   ; |",
    "        |  `/~\"     ~\" . \"~     \"~\\'  |",
    "        |  ~  ,-~~~^~, | ,~^~~~-,  ~  |",
    "         |   |        }:{        |   |",
    "         |   l       / | \\       !   |",
    "         .~  (__,.--\" .^. \"--.,__)  ~.",
    "         |     ---;' / | \\ `;---     |",
    "          \\__.       \\/^\\/       .__/",
    "           V| \\                 / |V",
    "            | |T~\\___!___!___/~T| |",
    "            | |`IIII_I_I_I_IIII'| |",
    "            |  \\,III I I I III,/  |",
    "             \\   `~~~~~~~~~~'    /",
    "               \\   .       .   /",
    "                 \\.    ^    ./",
    "                   ^~~~^~~~^"
]

# Кадр 3: усиленная “глитч”-деформация
skull_frame_3 = [
    "                 _,.-------.,_",
    "             ,;~'   .-.   .-. '~;,",
    "           ,;      (   ) (   )    ;,",
    "          ;         `-'   `-'       ;",
    "         ,'                         ',",
    "        ,;         .-\"\"\"\"-.          ;,",
    "        ; ;      .           .      ; ;",
    "        | ;   ______  ___  ______   ; |",
    "        |  `/~\"    ~\"     \"~    \"~\\' |",
    "        |  ~  ,-~~~^~, | ,~^~~~-, ~  |",
    "         |   |  (◕)  }:{  (◕)  |   |",
    "         |   l       / | \\       !  |",
    "         .~  (__,.--\" .^. \"--.,__) ~.",
    "         |     ---;' / | \\ `;---     |",
    "          \\__.       \\/^\\/       .__/",
    "           V| \\   *           * / |V",
    "            | |T~\\___!___!___/~T| |",
    "            | |`IIII_I_I_I_IIII'| |",
    "            |  \\,III I I I III,/  |",
    "             \\   `~~~~~~~~~~'    /",
    "               \\    \\___/     /",
    "                 \\.  \\_/  ./",
    "                   \\~~ ~~/"
]


# Собираем все кадры в один список для анимации:
skull_frames = [
    skull_frame_0,
    skull_frame_1,
    skull_frame_2,
    skull_frame_3,
]
# 

# Настройка ANSI-кодов для цвета/эффектов
RESET = "\033[0m"
BOLD = "\033[1m"
BLINK = "\033[5m"
# Цвета текста
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
MAGENTA = "\033[95m"
CYAN = "\033[96m"
WHITE = "\033[97m"

# Списки данных для генерации фейковых сообщений
users = ["admin", "root", "user", "guest"]  # имена пользователей для перебора паролей
passwords = ["123456", "password", "admin", "qwerty", "letmein", "welcome", "trustno1"]
ips = [f"{random.randint(10,255)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}" for _ in range(10)]
modules = ["EXPloit-0x1", "BruteForce-X", "MemDump", "SQLi-Ripper", "ZeroDayX", "PacketStorm", "Overflow-Gen"]

# Шаблоны сообщений атакующих действий (визуальные хаотичные команды)
attack_messages = [
    "Brute-forcing password for user {user}...",
    "Trying password: \"{pwd}\"",
    "Connecting to {ip}:{port} ...",
    "Connection established to {ip}:{port}",
    "Loading module: {module}",
    "Module {module} loaded successfully",
    "Launching exploit {module} against {ip}",
    "Exploit {module} execution complete",
    "Transferring data from {ip} ...",
    "Data exfiltration completed ({bytes} bytes)",
    "Attempting privilege escalation...",
    "Privilege escalation successful, admin rights gained",
    "Scanning network... Found vulnerable host at {ip}",
    "Accessing {ip} ...",
    "Access granted to {ip}",
    "Deleting system logs...",
    "Encryption bypass successful",
    "Uploading backdoor to {ip}",
    "Backdoor installed on {ip}"
]

# Шаблоны сообщений системы/защиты (реакции системы)
system_messages = [
    "Firewall: Intrusion detected from {attacker_ip}. Initiating countermeasures.",
    "Firewall: Blocking traffic from {attacker_ip}",
    "IDS Alert: Multiple failed login attempts",
    "System: Suspicious activity recorded in logs",
    "System: Port {port} closed due to security policy",
    "System: Account {user} locked due to brute-force attempt",
    "Warning: Unusual network activity on port {port}",
    "Error: Unauthorized access attempt on {ip}",
    "Security: Blacklisting source {attacker_ip}",
    "System: Connection to {ip} reset by peer",
    "Alert: Malware upload detected, aborting transfer",
    "Intrusion Prevention: Session terminated",
    "AntiVirus: Threat quarantined",
    "Alert: Remote code execution attempt blocked",
    "System: Kernel panic averted",
    "Firewall: DDoS mitigation engaged on port {port}"
]

# Функция печати ASCII-арта черепа построчно (с небольшой задержкой для эффекта построения)
def print_skull_art():
    sys.stdout.write(GREEN)  # устанавливаем цвет (белый)
    sys.stdout.flush()
    for line in skull_frames:
        print(line, flush=True)
        time.sleep(0.03)  # пауза между строками
    sys.stdout.write(RESET)  # сброс цвета к стандартному
    sys.stdout.flush()

# Функция мигания/инверсии черепа (создает эффект глитча или "смеха")
def flash_skull():
    # Перемещаем курсор вверх на высоту рисунка
    sys.stdout.write(f"\033[{len(skull_frames)}A")
    sys.stdout.flush()
    # Включаем инверсию цвета (reverse video) и печатаем череп заново
    sys.stdout.write("\033[7m")
    sys.stdout.flush()
    for line in skull_frames:
        print(line, flush=True)
    time.sleep(0.1)
    # Снова перемещаем курсор вверх и печатаем череп в нормальном режиме
    sys.stdout.write(f"\033[{len(skull_frames)}A")
    sys.stdout.write(RESET)
    sys.stdout.flush()
    for line in skull_frames:
        print(line, flush=True)
    time.sleep(0.1)

# Функция для форматированной печати одной строки с нужным цветом/эффектом
def print_line(category, text):
    if category == "attack":
        # Сообщения атакующего (зеленый текст)
        sys.stdout.write(GREEN + text + RESET + "\n")
    elif category == "system":
        # Обычные системные сообщения (желтый текст)
        sys.stdout.write(YELLOW + text + RESET + "\n")
    elif category == "alert":
        # Критические оповещения системы (красный мигающий текст)
        sys.stdout.write(RED + BLINK + text + RESET + "\n")
    else:
        # По умолчанию без спеццвета
        sys.stdout.write(text + "\n")
    sys.stdout.flush()

# Функция анимации черепа (прокручивает кадры, очищает экран, добавляет цвет)
def animate_skull(frames, cycles=10, delay=0.1):
    import os
    for i in range(cycles):
        os.system('clear')
        frame = frames[i % len(frames)]
        print(WHITE + "\n".join(frame) + RESET)
        sys.stdout.flush()
        time.sleep(delay)

# Скрываем курсор на время "атаки" для чистоты эффекта
sys.stdout.write("\033[?25l")
sys.stdout.flush()

try:
    # 1. Анимация черепа (глитч-анимация) и эффект глитча, затем сообщения, затем снова анимация
    while True:
        # Анимация черепа для тревожного эффекта
        animate_skull(skull_frames, cycles=random.randint(8, 16), delay=random.uniform(0.07, 0.15))
        # Очищаем экран перед выводом хаотичных команд
        sys.stdout.write("\033[2J\033[H")
        sys.stdout.flush()
        # 2. Основной цикл вывода псевдореалистичных сообщений взлома и защиты
        attacker_ip = f"{random.randint(1,255)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}"
        t_end = time.time() + random.uniform(2, 10)
        while time.time() < t_end:
            if random.random() < 0.7:
                template = random.choice(attack_messages)
                message = template.format(
                    user=random.choice(users),
                    pwd=random.choice(passwords),
                    ip=random.choice(ips),
                    port=random.randint(1, 65535),
                    module=random.choice(modules),
                    bytes=random.randint(1000, 50000)
                )
                print_line("attack", message)
            else:
                template = random.choice(system_messages)
                message = template.format(
                    attacker_ip=attacker_ip,
                    ip=random.choice(ips),
                    port=random.randint(1, 65535),
                    user=random.choice(users)
                )
                if random.random() < 0.3 or "Alert" in template or "Intrusion" in template:
                    print_line("alert", message)
                else:
                    print_line("system", message)
            time.sleep(random.uniform(0.05, 0.15))
            if random.random() < 0.1:
                user = random.choice(users)
                sys.stdout.write(GREEN + f"Bruteforcing {user}: attempt 1" + RESET)
                sys.stdout.flush()
                attempts = random.randint(5, 15)
                for attempt in range(2, attempts + 1):
                    time.sleep(0.1)
                    sys.stdout.write("\r" + GREEN + f"Bruteforcing {user}: attempt {attempt}" + RESET)
                    sys.stdout.flush()
                if random.random() < 0.3:
                    sys.stdout.write("\r" + GREEN + f"Bruteforcing {user}: SUCCESS on attempt {attempts}" + RESET + "\n")
                else:
                    sys.stdout.write("\r" + GREEN + f"Bruteforcing {user}: FAILED after {attempts} attempts" + RESET + "\n")
                sys.stdout.flush()
                time.sleep(0.2)
except KeyboardInterrupt:
    # Остановка скрипта пользователем (Ctrl+C)
    pass
finally:
    # Восстанавливаем настройки терминала: показываем курсор и сбрасываем цвета
    sys.stdout.write("\n" + RESET + "\033[?25h")
    sys.stdout.flush()