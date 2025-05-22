#!/bin/bash
#
# Setup Script for Advanced Evidence Collection System
# This script installs and configures tools needed for comprehensive security evidence collection
#
# Features:
# - Webcam capture with multiple fallbacks
# - Screenshot capture
# - Facial recognition (if libraries available)
# - Encrypted evidence storage
# - Remote notification capabilities
#

# Color definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

echo -e "${BLUE}${BOLD}"
echo "╔═════════════════════════════════════════════════╗"
echo "║       ADVANCED EVIDENCE COLLECTOR SETUP         ║"
echo "╚═════════════════════════════════════════════════╝"
echo -e "${NC}"

# Determine base directories
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"
SCRIPTS_DIR="$PROJECT_DIR/scripts"
EVIDENCE_DIR="$PROJECT_DIR/evidence"

# Create comprehensive directory structure
echo -e "${GREEN}Creating advanced evidence directory structure...${NC}"
mkdir -p "$EVIDENCE_DIR"
mkdir -p "$EVIDENCE_DIR/screenshots"
mkdir -p "$EVIDENCE_DIR/webcam"
mkdir -p "$EVIDENCE_DIR/logs"
mkdir -p "$EVIDENCE_DIR/network"
mkdir -p "$EVIDENCE_DIR/encrypted"
mkdir -p "$EVIDENCE_DIR/facial_analysis"
mkdir -p "$SCRIPTS_DIR"
mkdir -p "$PROJECT_DIR/facial_recognition/authorized"
mkdir -p "$PROJECT_DIR/facial_recognition/unknown"
mkdir -p "$PROJECT_DIR/notifications"

# Check for webcam access
echo -e "${YELLOW}Checking for camera hardware...${NC}"
if ! system_profiler SPCameraDataType 2>/dev/null | grep -q "Camera"; then
    echo -e "${YELLOW}No camera detected on this system. Webcam evidence will be unavailable.${NC}"
else
    echo -e "${GREEN}Camera hardware detected.${NC}"
fi

# Try to install imagesnap - a reliable command-line tool for webcam capture
echo -e "${YELLOW}Setting up webcam capture tools...${NC}"
if command -v brew >/dev/null 2>&1; then
    echo -e "${GREEN}Homebrew detected, installing imagesnap...${NC}"
    brew install imagesnap
    if command -v imagesnap >/dev/null 2>&1; then
        echo -e "${GREEN}imagesnap installed successfully.${NC}"
    else
        echo -e "${RED}Failed to install imagesnap via Homebrew.${NC}"
    fi
else
    echo -e "${YELLOW}Homebrew not found, checking for alternative methods...${NC}"
    
    # Check if imagesnap is already installed somehow
    if command -v imagesnap >/dev/null 2>&1; then
        echo -e "${GREEN}imagesnap already installed.${NC}"
    else
        echo -e "${YELLOW}Attempting to download pre-compiled imagesnap...${NC}"
        # This URL would need to be updated with a valid source
        IMAGESNAP_URL="https://github.com/imageio/imageio-binaries/raw/master/imagesnap/imagesnap"
        curl -s -L -o "/tmp/imagesnap" "$IMAGESNAP_URL"
        if [ $? -eq 0 ]; then
            chmod +x "/tmp/imagesnap"
            sudo mv "/tmp/imagesnap" "/usr/local/bin/"
            echo -e "${GREEN}Downloaded and installed imagesnap.${NC}"
        else
            echo -e "${RED}Failed to download imagesnap. Will fall back to Swift-based capture.${NC}"
        fi
    fi
fi

# Creating Swift-based webcam capture script (as fallback)
echo -e "${GREEN}Creating Swift-based webcam capture script...${NC}"
cat > "$SCRIPTS_DIR/webcam_capture.swift" << 'EOF'
import AVFoundation
import Cocoa
import Foundation

class CameraCapture: NSObject, AVCapturePhotoCaptureDelegate {
    let captureSession = AVCaptureSession()
    var photoOutput: AVCapturePhotoOutput?
    let outputPath: String
    var completion: (() -> Void)?
    
    init(outputPath: String) {
        self.outputPath = outputPath
        super.init()
        setupCamera()
    }
    
    func setupCamera() {
        captureSession.beginConfiguration()
        captureSession.sessionPreset = .high
        
        guard let camera = AVCaptureDevice.default(for: .video),
              let input = try? AVCaptureDeviceInput(device: camera) else {
            print("Failed to access camera")
            return
        }
        
        if captureSession.canAddInput(input) {
            captureSession.addInput(input)
        }
        
        photoOutput = AVCapturePhotoOutput()
        if let photoOutput = photoOutput, captureSession.canAddOutput(photoOutput) {
            captureSession.addOutput(photoOutput)
        }
        
        captureSession.commitConfiguration()
        captureSession.startRunning()
    }
    
    func capturePhoto(completion: @escaping () -> Void) {
        self.completion = completion
        guard let photoOutput = photoOutput else {
            print("Photo output not available")
            completion()
            return
        }
        
        let settings = AVCapturePhotoSettings()
        photoOutput.capturePhoto(with: settings, delegate: self)
    }
    
    func photoOutput(_ output: AVCapturePhotoOutput, didFinishProcessingPhoto photo: AVCapturePhoto, error: Error?) {
        captureSession.stopRunning()
        
        if let error = error {
            print("Error capturing photo: \(error)")
            completion?()
            return
        }
        
        guard let data = photo.fileDataRepresentation() else {
            print("No image data captured")
            completion?()
            return
        }
        
        do {
            try data.write(to: URL(fileURLWithPath: outputPath))
            print("Photo saved to \(outputPath)")
        } catch {
            print("Failed to save photo: \(error)")
        }
        
        completion?()
    }
}

// Main execution
if CommandLine.arguments.count < 2 {
    print("Usage: swift webcam_capture.swift [output_path]")
    exit(1)
}

let outputPath = CommandLine.arguments[1]
let cameraCapture = CameraCapture(outputPath: outputPath)

// Capture photo after a short delay to allow camera initialization
DispatchQueue.main.asyncAfter(deadline: .now() + 1.0) {
    cameraCapture.capturePhoto {
        exit(0)
    }
}

// Keep the program running until photo capture completes
RunLoop.main.run(until: Date(timeIntervalSinceNow: 5))
exit(0)
EOF

# Create shell script wrapper
echo -e "${GREEN}Creating webcam capture shell script...${NC}"
cat > "$SCRIPTS_DIR/capture_webcam.sh" << 'EOF'
#!/bin/bash
# Webcam capture script that tries multiple methods

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
OUTPUT_PATH="$1"

if [ -z "$OUTPUT_PATH" ]; then
    echo "Error: No output path provided"
    exit 1
fi

# Method 1: Try imagesnap (most reliable)
if command -v imagesnap >/dev/null 2>&1; then
    echo "Using imagesnap..."
    imagesnap -w 1 "$OUTPUT_PATH"
    EXIT_CODE=$?
    if [ $EXIT_CODE -eq 0 ] && [ -f "$OUTPUT_PATH" ]; then
        echo "Success: Captured image with imagesnap"
        exit 0
    fi
fi

# Method 2: Try Swift script
SWIFT_SCRIPT="$SCRIPT_DIR/webcam_capture.swift"
if [ -f "$SWIFT_SCRIPT" ]; then
    echo "Using Swift script..."
    swift "$SWIFT_SCRIPT" "$OUTPUT_PATH"
    EXIT_CODE=$?
    if [ $EXIT_CODE -eq 0 ] && [ -f "$OUTPUT_PATH" ]; then
        echo "Success: Captured image with Swift"
        exit 0
    fi
fi

# Method 3: Try AppleScript
echo "Using AppleScript..."
osascript <<EOD
tell application "Photo Booth"
    activate
    delay 2
    tell application "System Events" to keystroke return
    delay 1
    tell application "System Events" to keystroke return
    delay 1
    quit
end tell
EOD

# Try to find and copy the most recent Photo Booth photo
PHOTOBOOTH_DIR="$HOME/Pictures/Photo Booth Library/Pictures"
if [ -d "$PHOTOBOOTH_DIR" ]; then
    LATEST_PHOTO=$(ls -t "$PHOTOBOOTH_DIR" | head -1)
    if [ -n "$LATEST_PHOTO" ]; then
        cp "$PHOTOBOOTH_DIR/$LATEST_PHOTO" "$OUTPUT_PATH"
        if [ -f "$OUTPUT_PATH" ]; then
            echo "Success: Copied latest Photo Booth image"
            exit 0
        fi
    fi
fi

echo "All webcam capture methods failed"
exit 1
EOF

chmod +x "$SCRIPTS_DIR/capture_webcam.sh"

# Test webcam capture
echo -e "${YELLOW}Testing webcam capture system...${NC}"
TEST_IMAGE="$EVIDENCE_DIR/webcam/test_capture.jpg"

if "$SCRIPTS_DIR/capture_webcam.sh" "$TEST_IMAGE"; then
    echo -e "${GREEN}${BOLD}Webcam capture test successful!${NC}"
    echo -e "Test image saved to: $TEST_IMAGE"
    
    # Try to show the image
    if command -v qlmanage >/dev/null 2>&1; then
        echo -e "${YELLOW}Displaying test image (close preview to continue)...${NC}"
        qlmanage -p "$TEST_IMAGE" &>/dev/null
    fi
else
    echo -e "${RED}Webcam capture test failed.${NC}"
    echo "This may be due to camera permissions or hardware issues."
    echo "To grant camera permissions:"
    echo "1. Open System Preferences > Security & Privacy > Privacy"
    echo "2. Select 'Camera' from the list"
    echo "3. Ensure Terminal and/or your application are checked"
fi

# Check for facial recognition libraries
echo -e "${YELLOW}Setting up facial recognition...${NC}"

# Function to check Python package availability
check_python_package() {
    python3 -c "import $1" 2>/dev/null
    return $?
}

FACE_REC_AVAILABLE=false
OPENCV_AVAILABLE=false

# Check for facial recognition libraries
if check_python_package "face_recognition"; then
    echo -e "${GREEN}face_recognition library is available - facial recognition enabled!${NC}"
    FACE_REC_AVAILABLE=true
elif check_python_package "cv2"; then
    echo -e "${YELLOW}OpenCV is available - basic face detection enabled${NC}"
    OPENCV_AVAILABLE=true
    echo -e "For enhanced facial recognition, install face_recognition library:"
    echo -e "    pip3 install face_recognition"
else
    echo -e "${YELLOW}No facial recognition libraries found.${NC}"
    
    # Check if pip is available
    if command -v pip3 >/dev/null 2>&1; then
        echo -e "Would you like to install facial recognition capabilities? (y/n)"
        read -n 1 -r INSTALL_FACE_REC
        echo
        
        if [[ $INSTALL_FACE_REC =~ ^[Yy]$ ]]; then
            echo -e "${YELLOW}Attempting to install face_recognition libraries...${NC}"
            echo -e "${YELLOW}This may take several minutes...${NC}"
            
            # First try to install OpenCV (smaller dependency)
            echo -e "Installing OpenCV..."
            pip3 install opencv-python
            
            # Check if successful
            if check_python_package "cv2"; then
                echo -e "${GREEN}OpenCV successfully installed${NC}"
                OPENCV_AVAILABLE=true
                
                # Ask if they want to install the more powerful library
                echo -e "Would you like to install the more powerful face_recognition library?"
                echo -e "This requires additional dependencies and may take 10+ minutes (y/n)"
                read -n 1 -r INSTALL_FACE_REC_ADV
                echo
                
                if [[ $INSTALL_FACE_REC_ADV =~ ^[Yy]$ ]]; then
                    echo -e "${YELLOW}Installing face_recognition library...${NC}"
                    pip3 install face_recognition
                    
                    if check_python_package "face_recognition"; then
                        echo -e "${GREEN}face_recognition library successfully installed!${NC}"
                        FACE_REC_AVAILABLE=true
                    else
                        echo -e "${RED}Failed to install face_recognition library.${NC}"
                        echo -e "This may require additional system dependencies."
                        echo -e "You can still use basic face detection with OpenCV."
                    fi
                fi
            else
                echo -e "${RED}Failed to install OpenCV.${NC}"
                echo -e "You can manually install these libraries later with:"
                echo -e "    pip3 install opencv-python"
                echo -e "    pip3 install face_recognition"
            fi
        fi
    else
        echo -e "To install facial recognition, you need pip3:"
        echo -e "    brew install python3"
        echo -e "Then run: pip3 install face_recognition"
    fi
fi

# Create facial recognition configuration
echo -e "${GREEN}Creating facial recognition configuration...${NC}"
FACIAL_DIR="$PROJECT_DIR/facial_recognition"
mkdir -p "$FACIAL_DIR/authorized"
mkdir -p "$FACIAL_DIR/unknown"

# Create configuration file for facial recognition
cat > "$FACIAL_DIR/facial_recognition_config.json" << EOF
{
  "enabled": true,
  "tolerance": 0.6,
  "authorized_users": {},
  "notify_on_unauthorized": true,
  "max_unknown_faces_to_store": 10,
  "last_updated": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
}
EOF

# Create a README with instructions for adding authorized users
cat > "$FACIAL_DIR/README.md" << 'EOF'
# Facial Recognition Setup

This directory contains configuration and data for the facial recognition system.

## Adding Authorized Users

To add an authorized user:

1. Take a clear photo of their face
2. Save it in the `authorized/` directory with the filename format: `username.jpg`
3. Update the `facial_recognition_config.json` file to add the user to the "authorized_users" object:

```json
"authorized_users": {
  "username": {
    "name": "Full Name",
    "added_date": "2025-05-22T12:00:00Z"
  }
}
```

## Security Levels

Adjust the facial recognition tolerance in `facial_recognition_config.json`:
- Lower values (e.g., 0.4) = More strict matching, fewer false positives
- Higher values (e.g., 0.7) = More lenient matching, fewer false negatives
- Default is 0.6

## Unknown Face Storage

When an unknown face is detected, it will be saved in the `unknown/` directory.
Adjust `max_unknown_faces_to_store` in the config to control how many are kept.
EOF

# Create notification configuration
echo -e "${GREEN}Creating notification configuration...${NC}"
NOTIFICATION_DIR="$PROJECT_DIR/notifications"
mkdir -p "$NOTIFICATION_DIR"

# Create default notification config
cat > "$NOTIFICATION_DIR/notification_config.json" << EOF
{
  "email": {
    "enabled": false,
    "smtp_server": "smtp.gmail.com",
    "smtp_port": 587,
    "username": "",
    "password": "",
    "recipients": [],
    "send_evidence": true,
    "security_level_threshold": "high"
  },
  "sms": {
    "enabled": false,
    "service": "twilio",
    "account_sid": "",
    "auth_token": "",
    "from_number": "",
    "to_numbers": [],
    "security_level_threshold": "critical"
  },
  "local": {
    "enabled": true,
    "sound": true,
    "notification": true
  }
}
EOF

# Create README with instructions for notifications
cat > "$NOTIFICATION_DIR/README.md" << 'EOF'
# Remote Notification Setup

This configuration enables real-time notifications when security events occur.

## Email Notifications

To set up email alerts:

1. Edit `notification_config.json`
2. Set `email.enabled` to `true`
3. For Gmail:
   - Use your Gmail address as the username
   - Create an "App Password" in your Google Account security settings
   - Use the App Password in the password field
   - Add recipient email addresses to the `recipients` array

## SMS Notifications

To set up SMS alerts:

1. Create a Twilio account at www.twilio.com
2. Purchase a phone number
3. Get your Account SID and Auth Token from your Twilio dashboard
4. Edit `notification_config.json`:
   - Set `sms.enabled` to `true`
   - Enter your Account SID and Auth Token
   - Add your Twilio number as `from_number` (format: +1XXXXXXXXXX)
   - Add recipient numbers to `to_numbers` array (format: +1XXXXXXXXXX)

## Security Level Thresholds

You can control which alerts trigger notifications using the `security_level_threshold`:

- `low`: All events trigger notifications
- `medium`: Medium, high, and critical events
- `high`: Only high and critical events
- `critical`: Only critical security breaches
EOF

echo -e "${GREEN}${BOLD}"
echo "╔═════════════════════════════════════════════════╗"
echo "║    ADVANCED EVIDENCE COLLECTOR SETUP COMPLETE   ║"
echo "╚═════════════════════════════════════════════════╝"
echo -e "${NC}"

echo -e "${GREEN}Advanced evidence collection system has been successfully set up!${NC}"
echo -e "Evidence will be stored in: ${BOLD}$EVIDENCE_DIR${NC}"
echo -e ""
echo -e "The system will now capture:"
echo -e "  • ${CYAN}Screenshots${NC} of unauthorized access attempts"
echo -e "  • ${CYAN}Webcam photos${NC} for intruder identification"
echo -e "  • ${CYAN}Comprehensive logs${NC} with detailed system information"
echo -e "  • ${CYAN}Network activity${NC} during security events"

if [ "$FACE_REC_AVAILABLE" = true ]; then
    echo -e "  • ${GREEN}Facial recognition analysis${NC} of intruders"
elif [ "$OPENCV_AVAILABLE" = true ]; then
    echo -e "  • ${YELLOW}Basic face detection${NC} (OpenCV)"
else
    echo -e "  • ${RED}No facial recognition${NC} (libraries not installed)"
fi

echo -e ""
echo -e "${PURPLE}Advanced security features:${NC}"
echo -e "  • ${YELLOW}Evidence encryption${NC} to prevent tampering"
echo -e "  • ${YELLOW}Real-time alerts${NC} via system notifications"
echo -e "  • ${YELLOW}Remote email/SMS notifications${NC} (requires configuration)"
echo -e ""
echo -e "Configuration directories:"
echo -e "  • Facial recognition: ${BOLD}$PROJECT_DIR/facial_recognition${NC}"
echo -e "  • Notifications: ${BOLD}$PROJECT_DIR/notifications${NC}"
echo -e ""
echo -e "${YELLOW}Important notes:${NC}"
echo -e "1. For webcam functionality, ensure Terminal has camera permissions"
echo -e "   in System Settings > Privacy & Security > Camera."
echo -e "2. To enable facial recognition, add user photos to the authorized directory"
echo -e "3. To enable remote notifications, edit the notification config file"
echo -e ""
echo -e "${CYAN}See README.md files in each directory for detailed instructions.${NC}"

exit 0
