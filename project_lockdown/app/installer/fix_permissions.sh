#!/bin/bash

# Script to help grant accessibility permissions for keyboard_interceptor.py

# ANSI color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

clear
echo -e "${BOLD}${BLUE}=======================================${NC}"
echo -e "${BOLD}${BLUE}   Keyboard Interceptor Permission Fix ${NC}"
echo -e "${BOLD}${BLUE}=======================================${NC}"
echo

echo -e "${YELLOW}This script will help you grant the necessary accessibility permissions${NC}"
echo -e "${YELLOW}for the keyboard interceptor to work properly.${NC}"
echo

# Check if Terminal already has accessibility permissions
echo -e "${BOLD}Step 1: Checking current permissions...${NC}"
echo "Attempting to run a basic keyboard listener test..."
sleep 1

# Try to run a simple keyboard operation (will fail if no permissions)
python3 -c "
try:
    from pynput import keyboard
    controller = keyboard.Controller()
    print('Keyboard controller created successfully.')
    with keyboard.Listener(on_press=lambda k: None) as listener:
        print('Listener created successfully.')
        listener.stop()
    print('\\n${GREEN}Good news! Permissions appear to be working.${NC}')
    exit(0)
except Exception as e:
    print(f'\\n${RED}Permission test failed: {e}${NC}')
    exit(1)
"

# Check the result of the test
if [ $? -eq 0 ]; then
    echo -e "\n${GREEN}${BOLD}Accessibility permissions are already granted!${NC}"
    echo "The keyboard interceptor should work correctly."
    echo -e "\n${BOLD}Would you like to run the keyboard interceptor now? (y/n)${NC}"
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}Starting keyboard interceptor...${NC}"
        cd "$(dirname "$0")/.."
        python3 keyboard_interceptor.py
    else
        echo -e "\nYou can run the keyboard interceptor later with:"
        echo -e "${BOLD}python3 $(dirname "$0")/../keyboard_interceptor.py${NC}"
    fi
    exit 0
fi

echo
echo -e "${YELLOW}${BOLD}Accessibility permissions need to be granted.${NC}"
echo -e "Follow these steps to fix the issue:\n"

echo -e "${BOLD}Step 2: Opening System Preferences...${NC}"
echo "Opening Privacy & Security settings..."
open "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility"
sleep 2

echo -e "\n${BOLD}Step 3: Adding Terminal to accessibility permissions${NC}"
echo -e "1. Click the ${BOLD}+${NC} button in the Accessibility section"
echo -e "2. Navigate to ${BOLD}/Applications/Utilities/${NC}"
echo -e "3. Select ${BOLD}Terminal.app${NC} and click ${BOLD}Open${NC}"
echo -e "4. Make sure the checkbox next to Terminal is ${BOLD}checked${NC}"

echo -e "\n${YELLOW}NOTE: You might need to unlock the settings first by clicking the lock icon${NC}"
echo -e "${YELLOW}      and entering your administrator password.${NC}"

echo -e "\n${BOLD}Once you've added Terminal to the list and checked its checkbox:${NC}"
echo -e "1. Close Terminal completely (⌘+Q)"
echo -e "2. Open Terminal again"
echo -e "3. Run the keyboard interceptor with:"
echo -e "${BOLD}   python3 $(dirname "$0")/../keyboard_interceptor.py${NC}"

echo
echo -e "${BLUE}=======================================${NC}"
echo -e "${BOLD}You may need to restart your computer if the permissions${NC}"
echo -e "${BOLD}still don't work after following these steps.${NC}"
echo -e "${BLUE}=======================================${NC}"

# Offer to restart Terminal
echo -e "\n${BOLD}Would you like to close and restart Terminal now? (y/n)${NC}"
read -r restart
if [[ "$restart" =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}Closing Terminal in 3 seconds...${NC}"
    sleep 1
    echo -e "${YELLOW}Closing Terminal in 2 seconds...${NC}"
    sleep 1 
    echo -e "${YELLOW}Closing Terminal in 1 second...${NC}"
    sleep 1
    osascript -e 'tell application "Terminal" to quit'
    sleep 0.5
    open -a Terminal "$(dirname "$0")/fix_permissions.sh"
fi

exit 0
