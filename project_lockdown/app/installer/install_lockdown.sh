#!/usr/bin/env bash
# 
# Project Lockdown Installation and Integration Script
# This script installs, configures and integrates all components of the lockdown security system
#
# Usage: sudo ./install_lockdown.sh
#

# Color definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Check for root privileges
if [ "$EUID" -ne 0 ]; then
  echo -e "${RED}${BOLD}Please run as root:${NC} sudo $0"
  exit 1
fi

# Display banner
echo -e "${BLUE}${BOLD}"
echo "╔═════════════════════════════════════════════════╗"
echo "║             PROJECT LOCKDOWN INSTALLER           ║"
echo "║                                                 ║"
echo "║  Comprehensive Security System for macOS        ║"
echo "╚═════════════════════════════════════════════════╝"
echo -e "${NC}"

# Determine script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$HOME/Library/Logs/project_lockdown"
SCRIPTS_DIR="$PROJECT_DIR/scripts_2"

# Create necessary directories
echo -e "${GREEN}Creating project directories...${NC}"
mkdir -p "$PROJECT_DIR"
mkdir -p "$SCRIPTS_DIR"
mkdir -p "$PROJECT_DIR/backup"
mkdir -p "$PROJECT_DIR/evidence"
mkdir -p "$PROJECT_DIR/app"
mkdir -p "$PROJECT_DIR/logs"

# Copy scripts to project directory if not already there
echo -e "${GREEN}Copying scripts to project directory...${NC}"
cp -n "$SCRIPT_DIR"/*.py "$SCRIPTS_DIR/"
cp -n "$SCRIPT_DIR"/visual/*.py "$SCRIPTS_DIR/visual/"
cp -n "$SCRIPT_DIR"/visual/fix_permissions.sh "$SCRIPTS_DIR/visual/"
chmod +x "$SCRIPTS_DIR"/*.py
chmod +x "$SCRIPTS_DIR"/visual/*.py
chmod +x "$SCRIPTS_DIR"/visual/fix_permissions.sh

# Create backup of scripts
echo -e "${GREEN}Creating backups...${NC}"
cp "$SCRIPTS_DIR"/*.py "$PROJECT_DIR/backup/"
cp "$SCRIPTS_DIR"/visual/*.py "$PROJECT_DIR/backup/"

# Install required packages
echo -e "${GREEN}Installing required packages...${NC}"
pip3 install pynput pyobjc-framework-Quartz pyobjc-framework-AppKit

# Configure launch agent for auto-start
echo -e "${GREEN}Configuring auto-start on login...${NC}"
LAUNCH_AGENT_DIR="$HOME/Library/LaunchAgents"
mkdir -p "$LAUNCH_AGENT_DIR"

cat > "$LAUNCH_AGENT_DIR/com.phenix.lockdown.plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.phenix.lockdown</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>${SCRIPTS_DIR}/lockdown_master.py</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardErrorPath</key>
    <string>${PROJECT_DIR}/logs/lockdown_error.log</string>
    <key>StandardOutPath</key>
    <string>${PROJECT_DIR}/logs/lockdown_output.log</string>
</dict>
</plist>
EOF

# Load the launch agent
launchctl unload "$LAUNCH_AGENT_DIR/com.phenix.lockdown.plist" 2>/dev/null || true
launchctl load "$LAUNCH_AGENT_DIR/com.phenix.lockdown.plist"

# Create an application for the lockdown system
echo -e "${GREEN}Creating lockdown application...${NC}"
APP_DIR="$PROJECT_DIR/app/Lockdown.app/Contents/MacOS"
mkdir -p "$APP_DIR"

# Create the executable script
cat > "$APP_DIR/Lockdown" << EOF
#!/bin/bash
# Lockdown application launcher
cd "${SCRIPTS_DIR}"
exec python3 "${SCRIPTS_DIR}/lockdown_master.py"
EOF

chmod +x "$APP_DIR/Lockdown"

# Create the Info.plist
mkdir -p "$PROJECT_DIR/app/Lockdown.app/Contents"
cat > "$PROJECT_DIR/app/Lockdown.app/Contents/Info.plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>Lockdown</string>
    <key>CFBundleIconFile</key>
    <string>AppIcon</string>
    <key>CFBundleIdentifier</key>
    <string>com.phenix.lockdown</string>
    <key>CFBundleInfoDictionaryVersion</key>
    <string>6.0</string>
    <key>CFBundleName</key>
    <string>Lockdown</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0</string>
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>LSBackgroundOnly</key>
    <true/>
</dict>
</plist>
EOF

# Create Resources directory (for icon)
mkdir -p "$PROJECT_DIR/app/Lockdown.app/Contents/Resources"

# Grant accessibility permissions script
echo -e "${GREEN}Setting up accessibility permissions script...${NC}"
cat > "$PROJECT_DIR/fix_permissions.command" << EOF
#!/bin/bash
# Helper script to fix accessibility permissions for Project Lockdown

# Color definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

echo -e "\${BLUE}\${BOLD}"
echo "╔═════════════════════════════════════════════════╗"
echo "║        LOCKDOWN ACCESSIBILITY PERMISSIONS       ║"
echo "╚═════════════════════════════════════════════════╝"
echo -e "\${NC}"

echo -e "\${YELLOW}This script will help you enable accessibility permissions required by Lockdown.\${NC}"
echo ""

# Open System Preferences to Accessibility
echo -e "\${GREEN}Opening System Settings > Privacy & Security > Accessibility...\${NC}"
open "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility"

echo ""
echo -e "\${BOLD}Please follow these steps:\${NC}"
echo "1. Click the lock icon and authenticate if needed"
echo "2. Click the '+' button to add an application"
echo "3. Navigate to Applications and select Terminal.app"
echo "4. Ensure the checkbox next to Terminal is checked"
echo ""

read -p "Press Enter when you've completed these steps..." 

echo ""
echo -e "\${YELLOW}Testing accessibility permissions...\${NC}"
python3 -c "
try:
    from pynput import keyboard
    controller = keyboard.Controller()
    print('\033[0;32mSuccess! Accessibility permissions are working correctly.\033[0m')
except Exception as e:
    print('\033[0;31mError: Accessibility permissions are not properly configured.\033[0m')
    print(f'Details: {e}')
    print('\033[0;33mPlease make sure you added Terminal.app to the Accessibility permissions list.\033[0m')
"

echo ""
echo -e "\${GREEN}\${BOLD}Setup Complete!\${NC}"
echo "You can now run the Lockdown system with full functionality."
echo ""
echo -e "\${YELLOW}To start Lockdown manually, run:\${NC}"
echo "python3 $SCRIPTS_DIR/lockdown_master.py"
echo ""
echo -e "\${YELLOW}Lockdown will also start automatically at login.\${NC}"
echo ""

read -p "Press Enter to exit..." 
EOF

chmod +x "$PROJECT_DIR/fix_permissions.command"

# Create uninstall script
echo -e "${GREEN}Creating uninstaller...${NC}"
cat > "$PROJECT_DIR/uninstall_lockdown.command" << EOF
#!/bin/bash
# Uninstaller for Project Lockdown

# Color definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BOLD='\033[1m'
NC='\033[0m' # No Color

echo -e "\${RED}\${BOLD}"
echo "╔═════════════════════════════════════════════════╗"
echo "║           PROJECT LOCKDOWN UNINSTALLER          ║"
echo "╚═════════════════════════════════════════════════╝"
echo -e "\${NC}"

echo -e "\${YELLOW}This will completely remove Project Lockdown from your system.\${NC}"
echo -e "\${YELLOW}Are you sure you want to continue? (y/n)\${NC}"
read -p "> " confirm

if [ "\$confirm" != "y" ]; then
    echo -e "\${GREEN}Uninstall cancelled.\${NC}"
    exit 0
fi

echo -e "\${YELLOW}Stopping all lockdown processes...\${NC}"
pkill -f "lockdown_master.py" || true
pkill -f "keyboard_interceptor.py" || true
pkill -f "input_blocker2.py" || true
pkill -f "password_checker.py" || true
pkill -f "system_hooks.py" || true
pkill -f "network_monitor.py" || true
pkill -f "anti_debug.py" || true

echo -e "\${YELLOW}Removing launch agent...\${NC}"
launchctl unload "\$HOME/Library/LaunchAgents/com.phenix.lockdown.plist" 2>/dev/null || true
rm -f "\$HOME/Library/LaunchAgents/com.phenix.lockdown.plist"

echo -e "\${YELLOW}Do you want to remove all lockdown files? (y/n)\${NC}"
read -p "> " confirm_files

if [ "\$confirm_files" == "y" ]; then
    echo -e "\${YELLOW}Removing all lockdown files...\${NC}"
    rm -rf "$PROJECT_DIR"
    echo -e "\${GREEN}All lockdown files removed.\${NC}"
else
    echo -e "\${YELLOW}Leaving lockdown files intact. They remain at:\${NC}"
    echo "$PROJECT_DIR"
fi

echo -e "\${GREEN}\${BOLD}Lockdown has been successfully uninstalled!\${NC}"
read -p "Press Enter to exit..." 
EOF

chmod +x "$PROJECT_DIR/uninstall_lockdown.command"

# Create a README file
echo -e "${GREEN}Creating README...${NC}"
cat > "$PROJECT_DIR/README.md" << EOF
# Project Lockdown

## Overview
Project Lockdown is a comprehensive security system for macOS that provides an extra layer of defense
when unauthorized users gain access to your Mac. The system activates automatically after login and
blocks common methods of bypassing security measures.

## Components
- **Keyboard Interceptor**: Blocks keyboard shortcuts that could be used to escape
- **Input Blocker**: Disables mouse functionality
- **Password Checker**: Requires a password to unlock the system
- **System Hooks**: Low-level system integration for enhanced security
- **Network Monitor**: Prevents network-based bypass attempts
- **Anti-Debug Protection**: Prevents analysis and debugging of the security system

## Usage
The lockdown system starts automatically at login. To unlock it, the correct password must be provided.

### Manual Control
You can manually control the lockdown system using the master control interface:

\`\`\`
python3 $SCRIPTS_DIR/lockdown_master.py
\`\`\`

### Commands
- \`status\` - Check the status of all components
- \`unlock <password>\` - Unlock the system with the correct password
- \`exit\` or \`quit\` - Stop the lockdown system
- \`help\` - Show available commands

## Accessibility Permissions
For full functionality, you need to grant Terminal accessibility permissions. 
Run the \`fix_permissions.command\` script to set this up.

## Uninstalling
To remove Project Lockdown, run the \`uninstall_lockdown.command\` script.

## Security Notes
- The default password is "lockdown" (change it immediately)
- The system needs accessibility permissions to function properly
- Some components require root privileges for full functionality
EOF

# Set password step
echo -e "${YELLOW}Would you like to set a custom lockdown password now? (y/n)${NC}"
read -p "> " set_password

if [ "$set_password" == "y" ]; then
    echo -e "${YELLOW}Enter new password:${NC}"
    read -s new_password
    echo -e "${YELLOW}Confirm password:${NC}"
    read -s confirm_password
    
    if [ "$new_password" == "$confirm_password" ]; then
        echo -e "${GREEN}Setting password...${NC}"
        python3 -c "
import hashlib
import json
import os
from pathlib import Path

config_file = Path('$SCRIPTS_DIR/lockdown_config.json')
if not config_file.exists():
    config = {
        'components': {},
        'security': {
            'password_hash': hashlib.sha256('$new_password'.encode()).hexdigest(),
        },
        'runtime': {}
    }
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2)
    print('Password set successfully')
else:
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
        config['security']['password_hash'] = hashlib.sha256('$new_password'.encode()).hexdigest()
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)
        print('Password set successfully')
    except Exception as e:
        print(f'Error setting password: {e}')
"
    else
        echo -e "${RED}Passwords do not match. Using default password.${NC}"
    fi
else
    echo -e "${YELLOW}Using default password: 'lockdown'${NC}"
    echo -e "${RED}IMPORTANT: Change this password when you first run the system!${NC}"
fi

# Final instructions
echo -e "${GREEN}${BOLD}"
echo "╔═════════════════════════════════════════════════╗"
echo "║           INSTALLATION COMPLETE!                ║"
echo "╚═════════════════════════════════════════════════╝"
echo -e "${NC}"

echo -e "${YELLOW}Important next steps:${NC}"
echo "1. Run the fix_permissions.command script to set up accessibility permissions"
echo "   ${BOLD}$PROJECT_DIR/fix_permissions.command${NC}"
echo ""
echo "2. Lockdown will start automatically at next login, or you can start it manually:"
echo "   ${BOLD}python3 $SCRIPTS_DIR/lockdown_master.py${NC}"
echo ""
echo "3. The README.md file contains important usage information:"
echo "   ${BOLD}$PROJECT_DIR/README.md${NC}"
echo ""
echo -e "${RED}${BOLD}SECURITY NOTE:${NC} If you didn't set a custom password, the default is 'lockdown'"
echo "Change this immediately when you first run the system!"
echo ""
echo -e "${GREEN}Would you like to run the fix_permissions script now? (y/n)${NC}"
read -p "> " run_permissions

if [ "$run_permissions" == "y" ]; then
    echo -e "${GREEN}Running fix_permissions.command...${NC}"
    "$PROJECT_DIR/fix_permissions.command"
fi

echo -e "${GREEN}Installation completed successfully!${NC}"
exit 0
