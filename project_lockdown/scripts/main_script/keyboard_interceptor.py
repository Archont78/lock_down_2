#!/usr/bin/env python3
"""
Keyboard Command Interceptor

This script intercepts specified keyboard combinations (like Cmd+Q, Cmd+Tab, Ctrl+C)
and completely blocks them, replacing with random alphanumeric key presses.

Requires: 
- Python 3.6+
- pynput library (pip install pynput)
- Accessibility permissions granted to Terminal/Python

Usage:
- Run with 'python3 keyboard_interceptor.py'
- Press Ctrl+Shift+X to exit the script
"""
import random
import string
import sys
import time
import os
import subprocess
import signal
from threading import Thread, Event, Lock
from pathlib import Path
import logging

try:
    from pynput import keyboard
    from pynput.keyboard import Key, KeyCode
except ImportError:
    print("The pynput package is required. Installing...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pynput"])
    from pynput import keyboard
    from pynput.keyboard import Key, KeyCode

# Configure logging
LOG_DIR = Path.home() / "Library" / "Logs" / "project_lockdown"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "keyboard_interceptor.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('keyboard_interceptor')

# Event to signal termination
stop_event = Event()

# Lock for synchronizing key handling
key_lock = Lock()

# Set to keep track of currently pressed keys
current_keys = set()
# Import the skull_animation function from laugh_skull.py if available
DIR = Path(__file__).parent.resolve()
LAUGH_SKULL_SCRIPT = DIR / "visual" / "laugh_skull.py"
if not LAUGH_SKULL_SCRIPT.exists():
    LAUGH_SKULL_SCRIPT = DIR / "laugh_skull.py"

try:
    import importlib.util
    spec = importlib.util.spec_from_file_location("laugh_skull", str(LAUGH_SKULL_SCRIPT))
    laugh_skull = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(laugh_skull)
    skull_animation = laugh_skull.skull_animation
    logger.info("Imported skull_animation from laugh_skull.py")
except Exception as e:
    skull_animation = None
    logger.warning(f"Could not import skull_animation from laugh_skull.py: {e}")

# Taunting messages to display when a blocked key combination is detected
TAUNTING_MESSAGES = [
    "Huh, nice try)",
    "Oopsie doopsie kiddo, something went wrong?",
    "Nope, not today!",
    "You thought it would be that easy?",
    "Sorry, the exit is... elsewhere",
    "Those keys are disabled. Try harder!",
    "Clever, but not clever enough",
    "This lockdown isn't broken that easily",
    "Good luck getting out that way",
    "Access Denied: Unauthorized Escape Attempt",
    "The system is disappointed in your attempt",
    "Did you really think Cmd+Q would work? LOL",
    "That's not how this works, that's not how any of this works",
    "Error 403: Freedom Forbidden",
    "The universe laughs at your escape attempt"
]

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

# Список кадров для анимации

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

# Функция печати ASCII-арта черепа построчно (с небольшой задержкой для эффекта построения)
def print_skull_art():
    sys.stdout.write(GREEN)  # устанавливаем цвет (белый)
    sys.stdout.flush()
    for line in skull_frames:
        print(line, flush=True)
        time.sleep(0.03)  # пауза между строками
    sys.stdout.write(RESET)  # сброс цвета к стандартному
    sys.stdout.flush()

# Функция запуска анимации черепа в отдельном потоке
def run_skull():
    """Run the skull animation in a separate thread"""
    while not stop_event.is_set():
        for frame in skull_frames:
            print("\n".join(frame))
            time.sleep(0.1)  # пауза между кадрами
        time.sleep(0.5)  # пауза перед повтором
        os.system('clear')  # очистка экрана после каждого цикла
        print_skull_art()  # печать черепа
        time.sleep(0.5)  # пауза перед повтором
        os.system('clear')  # очистка экрана после каждого цикла


# Define combinations to intercept
COMBINATIONS = [
    {
        'name': 'cmd+q',
        'keys': {Key.cmd, KeyCode.from_char('q')},
        'description': 'Quit application'
    },
    {
        'name': 'cmd+tab',
        'keys': {Key.cmd, Key.tab},
        'description': 'App switcher'
    },
    {
        'name': 'ctrl+c',
        'keys': {Key.ctrl, KeyCode.from_char('c')},
        'description': 'Copy/Interrupt'
    },
    {
        'name': 'cmd+c',
        'keys': {Key.cmd, KeyCode.from_char('c')},
        'description': 'Copy'
    },
    {
        'name': 'cmd+v',
        'keys': {Key.cmd, KeyCode.from_char('v')},
        'description': 'Paste'
    },
    {
        'name': 'cmd+w',
        'keys': {Key.cmd, KeyCode.from_char('w')},
        'description': 'Close window'
    },
    {
        'name': 'cmd+h',
        'keys': {Key.cmd, KeyCode.from_char('h')},
        'description': 'Hide application' 
    },
    {
        'name': 'cmd+m',
        'keys': {Key.cmd, KeyCode.from_char('m')},
        'description': 'Minimize window'
    },
    {
        'name': 'cmd+space',
        'keys': {Key.cmd, Key.space},
        'description': 'Spotlight search'
    },
    {
        'name': 'alt+tab',
        'keys': {Key.alt, Key.tab},
        'description': 'Alt+Tab'
    },
    {
        'name': 'cmd+alt+esc',
        'keys': {Key.cmd, Key.alt, Key.esc},
        'description': 'Force quit'
    },
    # Add more combinations as needed
    {
        'name': 'escape',
        'keys': {Key.esc},
        'description': 'Escape key'
    },
    # Function keys F1-F12
    *[{
        'name': f'f{i}',
        'keys': {getattr(Key, f'f{i}')},
        'description': f'Function key F{i}'
    } for i in range(1, 13)]
]

# Exit combination - pressing this will stop the script
EXIT_COMBINATION = {Key.ctrl, Key.shift, KeyCode.from_char('x')}

# List of alphanumeric characters to simulate when intercepting
ALPHABET = string.ascii_letters + string.digits

# Track last skull animation time to prevent spam
last_skull_time = 0
SKULL_COOLDOWN = 5  # seconds

# Special keys to release immediately to avoid key getting "stuck"
SPECIAL_RELEASE_KEYS = {Key.cmd,  Key.alt, Key.shift}

def display_taunt():
    """Returns a random taunting message"""
    return random.choice(TAUNTING_MESSAGES)

def launch_laugh_skull():
    """Launch the laughing skull animation in a new terminal window and close it after 5 seconds"""
    global last_skull_time
    
    # Check if enough time has passed since the last skull animation
    current_time = time.time()
    if current_time - last_skull_time < SKULL_COOLDOWN:
        return
    
    last_skull_time = current_time
    
    # Get a taunting message
    taunt = display_taunt()
    
    # Create a temporary Python script with the skull animation and taunt
    temp_script_path = DIR / "temp_skull_animation.py"
    
    try:
        # Create a temporary Python script that will display the skull animation
        with open(temp_script_path, 'w') as script_file:
            script_file.write('''#!/usr/bin/env python3
import sys, time, os, random

# ANSI colors
RED = "\\033[91m"
GREEN = "\\033[92m"
YELLOW = "\\033[93m"
RESET = "\\033[0m"
BOLD = "\\033[1m"
BLINK = "\\033[5m"

# Skull frames (copied from the main script)
skull_frame_0 = [
     "                 _,.-------.,_",
    "             ,;~\\'             \\'~;,",
    "           ,;                     ;,",
    "          ;                         ;",
    "         ,\\'                         \\'",
    "        ,;                           ;,",
    "        ; ;      .           .      ; ;",
    "        | ;   ______       ______   ; |",
    "        |  `/~\\"     ~\\" . \\"~     \\"~\\\\\'  |",
    "        |  ~  ,-~~~^~, | ,~^~~~-,  ~  |",
    "         |   |        }:{        |   |",
    "         |   l       / | \\\\       !   |",
    "         .~  (__,.--\\" .^. \\"--.,__)  ~.",
    "         |     ---;\\' / | \\\\ `;---     |",
    "          \\\\__.       \\\\/^\\\\/       .__/",
    "           V| \\\\                 / |V",
    "            | |T~\\\\___!___!___/~T| |",
    "            | |`IIII_I_I_I_IIII\\'| |",
    "            |  \\\\,III I I I III,/  |",
    "             \\\\   `~~~~~~~~~~\\'    /",
    "               \\\\   .       .   /",
    "                 \\\\.    ^    ./",
    "                   ^~~~^~~~^"
]

skull_frame_1 = [
    "                 _,.-------.,_",
    "             ,;~\\'             \\'~;,",
    "           ,;        _          ;,",
    "          ;        (   )          ;",
    "         ,\\'        (_ )           \\'",
    "        ,;           `             ;,",
    "        ; ;      .           .      ; ;",
    "        | ;   ______       ______   ; |",
    "        |  `/~\\"    ~\\" . \\"~    \\"~\\\\\'  |",
    "        |  ~ ,-~~~^~, | ,~^~~~-, ~  |",
    "         |  /|       }:{       |\\\\  |",
    "         |   l      / | \\\\      !   |",
    "         .~ (__,.--\\" .^. \\"--.,__) ~.",
    "         |    ---;\\' / | \\\\ `;---    |",
    "          \\\\__.      \\\\/o\\\\/      .__/",
    "           V| \\\\                 / |V",
    "            | |T~\\\\___!___!___/~T| |",
    "            | |`IIII_I_I_I_IIII\\'| |",
    "            |  \\\\,III I I I III,/  |",
    "             \\\\   `~~~~~~~~~~\\'    /",
    "               \\\\   .  .  .    /",
    "                 \\\\.   -   ./",
    "                   -~~~-~~~-"
]

skull_frame_2 = [
    "                 _,.-------.,_",
    "             ,;~\\'             \\'~;,",
    "           ,;     \\\\     /       ;,",
    "          ;       (x)   (x)      ;",
    "         ,\\'       \\\\  ___  /       \\'",
    "        ,;         \\\\|   |/         ;,",
    "        ; ;      .   \\\\ /   .      ; ;",
    "        | ;   ______\\\\_/_______   ; |",
    "        |  `/~\\"     ~\\" . \\"~     \\"~\\\\\'  |",
    "        |  ~  ,-~~~^~, | ,~^~~~-,  ~  |",
    "         |   |        }:{        |   |",
    "         |   l       / | \\\\       !   |",
    "         .~  (__,.--\\" .^. \\"--.,__)  ~.",
    "         |     ---;\\' / | \\\\ `;---     |",
    "          \\\\__.       \\\\/^\\\\/       .__/",
    "           V| \\\\                 / |V",
    "            | |T~\\\\___!___!___/~T| |",
    "            | |`IIII_I_I_I_IIII\\'| |",
    "            |  \\\\,III I I I III,/  |",
    "             \\\\   `~~~~~~~~~~\\'    /",
    "               \\\\   .       .   /",
    "                 \\\\.    ^    ./",
    "                   ^~~~^~~~^"
]

skull_frame_3 = [
    "                 _,.-------.,_",
    "             ,;~\\'   .-.   .-. \\'~;,",
    "           ,;      (   ) (   )    ;,",
    "          ;         `-\\'   `-\\'       ;",
    "         ,\\'                         \\'",
    "        ,;         .-\\"\\"\\"\\"\\"-          ;,",
    "        ; ;      .           .      ; ;",
    "        | ;   ______  ___  ______   ; |",
    "        |  `/~\\"    ~\\"     \\"~    \\"~\\\\\' |",
    "        |  ~  ,-~~~^~, | ,~^~~~-, ~  |",
    "         |   |  (◕)  }:{  (◕)  |   |",
    "         |   l       / | \\\\       !  |",
    "         .~  (__,.--\\" .^. \\"--.,__) ~.",
    "         |     ---;\\' / | \\\\ `;---     |",
    "          \\\\__.       \\\\/^\\\\/       .__/",
    "           V| \\\\   *           * / |V",
    "            | |T~\\\\___!___!___/~T| |",
    "            | |`IIII_I_I_I_IIII\\'| |",
    "            |  \\\\,III I I I III,/  |",
    "             \\\\   `~~~~~~~~~~\\'    /",
    "               \\\\    \\\\___/     /",
    "                 \\\\.  \\\\_/  ./",
    "                   \\\\~~ ~~/"
]

# Combine all frames
skull_frames = [skull_frame_0, skull_frame_1, skull_frame_2, skull_frame_3]

# Display the taunting message with dramatic effect
taunt = "''' + taunt.replace("'", "\\'") + '''"

def clear_screen():
    os.system('clear' if os.name == 'posix' else 'cls')

def display_centered_text(text, color=RED, effect=""):
    # Get terminal size or use a reasonable default
    try:
        terminal_width = os.get_terminal_size().columns
    except:
        terminal_width = 80
    lines = text.split('\\n')
    for line in lines:
        spaces = (terminal_width - len(line)) // 2
        print(" " * spaces + color + effect + line + RESET)

# Clear screen and show taunt
clear_screen()
print("\\n" * 3)  # Add some space at the top
display_centered_text(taunt, RED, BOLD)
time.sleep(0.5)

# Show the skull animation
for _ in range(10):  # Show animation for about 5 seconds
    clear_screen()
    frame = random.choice(skull_frames)
    print("\\n" * 2)  # Space at top
    display_centered_text("\\n".join(frame), GREEN)
    print("\\n")  # Space after skull
    display_centered_text(taunt, RED, BOLD if random.random() > 0.5 else BLINK)
    time.sleep(0.5)

clear_screen()
print("\\n" * 3)
display_centered_text("ACCESS DENIED", RED, BOLD)
time.sleep(1)
''')
        
        # Make the script executable
        os.chmod(temp_script_path, 0o755)
        
        # Launch the temporary script in a new terminal window that will auto-close after execution
        osascript_cmd = f'''
        tell application "Terminal"
            activate
            do script "python3 '{temp_script_path}'; sleep 0.5; rm '{temp_script_path}'; exit"
            delay 0.2
            set bounds of front window to {{100, 100, 900, 700}}
        end tell'''
        
        subprocess.Popen(["osascript", "-e", osascript_cmd])
        logger.info(f"Launched custom skull animation with taunt: {taunt}")
    except Exception as e:
        logger.error(f"Failed to launch skull animation: {e}")

def simulate_random_keypress():
    """Simulates a random alphanumeric key press"""
    random_char = random.choice(ALPHABET)
    logger.info(f"Simulating random key press: {random_char}")
    
    controller = keyboard.Controller()
    # First, release any special keys that might be held down
    for skey in SPECIAL_RELEASE_KEYS.intersection(current_keys):
        controller.release(skey)
    
    # Press and release the random character
    controller.press(random_char)
    time.sleep(0.05)  # Short delay
    controller.release(random_char)
    
    # Ensure all special keys are released
    for skey in list(current_keys):
        if skey in SPECIAL_RELEASE_KEYS:
            try:
                controller.release(skey)
                current_keys.discard(skey)
            except:
                pass

def is_combination_pressed(combination_keys):
    """Check if a combination of keys is pressed"""
    return all(k in current_keys for k in combination_keys)

def check_accessibility_permissions():
    """
    Check if accessibility permissions are granted.
    Returns True if permissions seem to be in place.
    """
    try:
        # Just creating the controller object is enough to check for permissions
        controller = keyboard.Controller()
        # Try to listen for a key event - this is a more reliable test than pressing a key
        with keyboard.Listener(on_press=lambda k: None, on_release=lambda k: None) as listener:
            # Start and immediately stop - just to check if we can access the listener
            time.sleep(0.1)
            listener.stop()
        return True
    except Exception as e:
        logger.error(f"Failed accessibility test: {e}")
        return False

def handle_key_combination():
    """
    Handle an intercepted key combination by launching the skull,
    showing a taunt message, and simulating a random key press.
    """
    # Acquire lock to prevent race conditions
    with key_lock:
        # Launch laughing skull animation
        launch_laugh_skull()
        
        # Display taunting message
        taunt = display_taunt()
        print(f"\033[91m{taunt}\033[0m")  # Red color
        
        # Simulate random key press
        simulate_random_keypress()

def on_press(key):
    """Handler for key press events"""
    # Add to currently pressed keys
    current_keys.add(key)
    
    # Check for exit combination first
    if is_combination_pressed(EXIT_COMBINATION):
        logger.info("Exit combination detected. Stopping the script.")
        stop_event.set()
        return False  # Stop this key from propagating further
    
    # Check for combinations to intercept
    for combo in COMBINATIONS:
        if is_combination_pressed(combo['keys']):
            logger.info(f"Intercepted: {combo['name']} ({combo['description']})")
            
            # Handle the key combination in a non-blocking way
            Thread(target=handle_key_combination).start()
            
            # Important to release all keys in the combination to avoid "stuck keys"
            controller = keyboard.Controller()
            for k in combo['keys']:
                try:
                    if k in current_keys:
                        controller.release(k)
                        current_keys.discard(k)
                except:
                    pass
                    
            return False  # Critical - stop key from propagating further

def on_release(key):
    """Handler for key release events"""
    try:
        current_keys.remove(key)
    except KeyError:
        # Key might not be in the set if we intercepted its press event
        pass

def anti_stuck_keys_thread():
    """Periodically check for and release any keys that may be "stuck" down"""
    controller = keyboard.Controller()
    while not stop_event.is_set():
        try:
            # Check every 2 seconds
            time.sleep(2)
            # Look for special keys that might be stuck
            for skey in SPECIAL_RELEASE_KEYS.intersection(current_keys):
                controller.release(skey)
                current_keys.discard(skey)
                logger.info(f"Released potentially stuck key: {skey}")
        except:
            pass

def display_status_message():
    """Displays a periodic status message in the terminal"""
    count = 0
    while not stop_event.is_set():
        if count % 60 == 0:  # Every ~60 seconds
            logger.info("Keyboard interceptor active. Press Ctrl+Shift+X to exit.")
        count += 1
        time.sleep(1)

def check_for_pynput():
    """Check if pynput is installed"""
    try:
        import pynput
        return True
    except ImportError:
        return False

def main():
    """Main function to run the keyboard interceptor"""
    logger.info("Starting keyboard interceptor...")
    
    # Handle Ctrl+C to prevent the script from being terminated with a keyboard interrupt
    def handle_sigint(signum, frame):
        print(f"\033[91m{display_taunt()}\033[0m")  # Display taunt when Ctrl+C is pressed
        logger.info("Blocked SIGINT (Ctrl+C) attempt")
        # Launch laughing skull animation when Ctrl+C is pressed
        Thread(target=launch_laugh_skull).start()
        return
    
    # Register the custom signal handler for SIGINT (Ctrl+C)
    signal.signal(signal.SIGINT, handle_sigint)
    
    if not check_for_pynput():
        logger.error("pynput module is not installed. Please install using: pip install pynput")
        print("\nThe pynput module is required. Install it using:")
        print("    pip install pynput")
        print("\nAfter installing, run this script again.")
        return
    
    # First try - if this fails, guide the user through enabling permissions
    if not check_accessibility_permissions():
        logger.error("Accessibility permissions test failed!")
        print("\n\033[1;31m⚠️ ACCESSIBILITY PERMISSIONS REQUIRED ⚠️\033[0m")
        print("\033[1mThis script needs to monitor keyboard events to work properly.\033[0m")
        print("\n\033[1mFollow these steps to grant permissions:\033[0m")
        print("1. Open \033[1mSystem Settings > Privacy & Security > Accessibility\033[0m")
        print("2. Click the '+' button to add an application")
        print("3. Navigate to and select \033[1mTerminal\033[0m (or \033[1miTerm\033[0m if you're using that)")
        print("4. Make sure the checkbox next to Terminal is \033[1mchecked\033[0m")
        
        # Try to open the Accessibility settings directly
        try:
            subprocess.run(["open", "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility"])
            print("\n\033[32mThe System Settings app should be opening now...\033[0m")
        except Exception:
            print("\nPlease open System Settings manually.")
        
        print("\n\033[33mAfter granting permissions:\033[0m")
        print("1. Close and restart Terminal")
        print("2. Run this script again")
        
        # Ask if the user wants to try continuing anyway
        try:
            response = input("\n\033[1mWould you like to try continuing anyway? (y/n): \033[0m")
            if response.lower() != 'y':
                return
            print("\nAttempting to continue without confirmed permissions...")
        except KeyboardInterrupt:
            return
    
    print("\033[1;31m===== LOCKDOWN KEYBOARD INTERCEPTOR ACTIVE =====\033[0m")
    print(f"Intercepting: {', '.join(combo['name'] for combo in COMBINATIONS)}")
    print("Press Ctrl+Shift+X to exit.")
    
    if LAUGH_SKULL_SCRIPT.exists():
        print(f"Laugh skull animation ready at: {LAUGH_SKULL_SCRIPT}")
    else:
        print("\033[33mWarning: Laugh skull animation not found. Taunt messages will still display.\033[0m")
    
    # Start anti-stuck keys thread
    anti_stuck_thread = Thread(target=anti_stuck_keys_thread)
    anti_stuck_thread.daemon = True
    anti_stuck_thread.start()
    
    # Start status display thread
    status_thread = Thread(target=display_status_message)
    status_thread.daemon = True
    status_thread.start()
    
    try:
        # Start the keyboard listener in blocking mode to ensure all keys are captured
        logger.info("Listening for keyboard events...")
        with keyboard.Listener(on_press=on_press, on_release=on_release, suppress=True) as listener:
            listener.join()
    except Exception as e:
        logger.exception(f"Error in keyboard listener: {e}")
    
    logger.info("Keyboard interceptor stopped.")
    print("\n\033[1;32mKeyboard interceptor stopped.\033[0m")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        # This should never be reached due to our signal handler,
        # but just in case something goes wrong with the handler
        print(f"\033[91m{display_taunt()}\033[0m")
        logger.info("Caught KeyboardInterrupt in main")
        # Show skull animation when interrupted
        Thread(target=launch_laugh_skull).start()
        time.sleep(1)  # Give animation time to start
