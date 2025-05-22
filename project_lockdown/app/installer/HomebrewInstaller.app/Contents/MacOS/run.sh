#!/bin/zsh

# Get the directory where the script is located
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT_PATH="$APP_DIR/../Resources/install_homebrew.sh"

# Make the script executable if it's not already
if [ ! -x "$SCRIPT_PATH" ]; then
    chmod +x "$SCRIPT_PATH"
fi

# Open Terminal and run the script
# Using osascript to ensure Terminal gains focus and runs the command.
# The script will keep the Terminal window open until it finishes or is closed by the user.
osascript <<EOF
tell application "Terminal"
    activate
    do script "'$SCRIPT_PATH'; exit"
end tell
EOF
