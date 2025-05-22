#!/bin/zsh

# Function to display an AppleScript dialog
show_dialog() {
    osascript -e "display dialog \"$1\" with title \"Homebrew Installer\" buttons {\"OK\"} default button \"OK\""
}

echo "Starting Homebrew installation check..."

# Check if Homebrew is installed
if command -v brew &>/dev/null; then
    echo "Homebrew is already installed."
    show_dialog "Homebrew is already installed at: $(which brew)"
    brew --version
else
    echo "Homebrew not found. Attempting to install..."
    show_dialog "Homebrew is not installed. Click OK to begin the installation process. This may take a few minutes and require your password."

    # Install Homebrew
    # The official command from brew.sh
    if /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"; then
        echo "Homebrew installation script finished."
        # Attempt to add Homebrew to PATH for the current session if the installer didn't.
        # For zsh, the installer usually handles .zprofile.
        if [ -x "/opt/homebrew/bin/brew" ]; then
             eval "$(/opt/homebrew/bin/brew shellenv)"
        elif [ -x "/usr/local/bin/brew" ]; then
             eval "$(/usr/local/bin/brew shellenv)"
        fi

        if command -v brew &>/dev/null; then
            echo "Homebrew installation successful and 'brew' command is available."
            show_dialog "Homebrew installation was successful! You can now use 'brew' in your terminal."
            brew --version
        else
            echo "'brew' command is not immediately available. PATH might need update or new terminal."
            show_dialog "Homebrew installation script finished, but the 'brew' command is not available in this script's session. You might need to open a new terminal window or ensure your shell profile (e.g., ~/.zprofile) is correctly updated by the installer. Check the messages above from the installer."
        fi
    else
        echo "Homebrew installation failed."
        show_dialog "Homebrew installation failed. Please check the terminal output for errors or try installing manually from https://brew.sh"
        exit 1
    fi
fi

echo "Script finished."
# Add a small delay so the user can see the final messages in the terminal before it closes.
sleep 5
exit 0
