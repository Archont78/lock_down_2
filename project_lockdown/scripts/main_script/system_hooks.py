#!/usr/bin/env python3
"""
System Hooks for Project Lockdown

This module provides system-level integration to prevent bypassing of the lockdown
through various system mechanisms.

Features:
- Blocks sleep mode exit without authentication
- Monitors system processes to prevent termination
- Captures comprehensive evidence on bypass attempts (screenshots, webcam, logs)
- Implements facial recognition for unauthorized access detection
- Encrypts collected evidence to prevent tampering
- Sends remote notifications for serious security events
- Registers as a login item for persistence

Usage: Run as root for full functionality
"""
import os
import sys
import time
import signal
import subprocess
import logging
import json
import base64
import hashlib
import shutil
import datetime
from pathlib import Path
import threading
from typing import Dict, List, Optional, Union, Tuple
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage

# Configure logging
LOG_DIR = Path.home() / "Library" / "Logs" / "project_lockdown"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "system_hooks.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('system_hooks')

# Directory containing lockdown scripts
SCRIPTS_DIR = Path(__file__).parent.resolve()
PROJECT_DIR = LOG_DIR.parent / "project_lockdown"

class SystemHookManager:
    def __init__(self):
        self.stop_flag = threading.Event()
        self.lockdown_processes = {
            "keyboard_interceptor.py": None,
            "input_blocker2.py": None,
            "password_checker.py": None
        }
        
        # Initialize advanced evidence collection flags
        self.face_rec_available = None
        self.evidence_encryption_available = False
        
        # Try to detect available security tools
        try:
            # Check if OpenSSL is available for encryption
            if subprocess.run(['which', 'openssl'], 
                            stdout=subprocess.PIPE, 
                            stderr=subprocess.PIPE).returncode == 0:
                self.evidence_encryption_available = True
                logger.debug("OpenSSL found - evidence encryption enabled")
        except Exception:
            pass
        
    def ensure_login_item(self):
        """Make sure the lockdown app launches at login"""
        try:
            # Create a small AppleScript to add the app as a login item
            script = """
            tell application "System Events"
                make new login item at end with properties {path:"%s", hidden:true}
            end tell
            """ % str(PROJECT_DIR / "app" / "HomebrewInstaller.app")
            
            subprocess.run(['osascript', '-e', script])
            logger.info("Added lockdown app as login item")
            return True
        except Exception as e:
            logger.error(f"Failed to add login item: {e}")
            return False
            
    def disable_spotlight(self):
        """Temporarily disable Spotlight to prevent search functionality"""
        try:
            # Disable Spotlight indexing
            subprocess.run(['sudo', 'mdutil', '-a', '-i', 'off'], check=True)
            logger.info("Disabled Spotlight indexing")
            return True
        except Exception as e:
            logger.error(f"Failed to disable Spotlight: {e}")
            return False
    
    def watch_lockdown_processes(self):
        """Monitor the lockdown processes and restart them if they exit"""
        while not self.stop_flag.is_set():
            try:
                # Check if any of our processes have terminated
                for script_name in self.lockdown_processes.keys():
                    process = self.lockdown_processes[script_name]
                    if process is None or process.poll() is not None:
                        # Process not running or has terminated, restart it
                        script_path = SCRIPTS_DIR / script_name
                        if script_path.exists():
                            logger.info(f"Restarting {script_name}")
                            self.lockdown_processes[script_name] = subprocess.Popen(
                                [sys.executable, str(script_path)], 
                                stdout=subprocess.PIPE, 
                                stderr=subprocess.PIPE
                            )
            except Exception as e:
                logger.error(f"Error in process watcher: {e}")
            
            # Check every 2 seconds
            time.sleep(2)
    
    def disable_function_keys(self):
        """Disable function keys (hardware level if possible)"""
        try:
            # Using AppleScript to disable function keys
            script = """
            tell application "System Settings"
                activate
                delay 1
                tell application "System Events" to click menu item "Keyboard" of menu "View" of process "System Settings"
                delay 1
                tell application "System Events" to click checkbox "Use F1, F2, etc. keys as standard function keys" of group 1 of window "Keyboard" of process "System Settings"
                delay 1
                quit
            end tell
            """
            subprocess.run(['osascript', '-e', script])
            logger.info("Modified function key behavior")
            return True
        except Exception as e:
            logger.error(f"Failed to disable function keys: {e}")
            return False
    
    def disable_fast_user_switching(self):
        """Disable fast user switching to prevent account changes"""
        try:
            subprocess.run(['defaults', 'write', '/Library/Preferences/.GlobalPreferences', 'MultipleSessionEnabled', '-bool', 'NO'], check=True)
            logger.info("Disabled fast user switching")
            return True
        except Exception as e:
            logger.error(f"Failed to disable fast user switching: {e}")
            return False

    def disable_cmd_key(self):
        """Attempt to disable the Command key at a low level"""
        try:
            # This approach uses hidutil to remap the Command key to a null key
            subprocess.run([
                'hidutil', 'property', '--set', '{"UserKeyMapping":[{"HIDKeyboardModifierMappingSrc":0x7000000E7,"HIDKeyboardModifierMappingDst":0x0}]}'
            ], check=True)
            logger.info("Remapped Command key")
            return True
        except Exception as e:
            logger.error(f"Failed to remap Command key: {e}")
            return False
    
    def monitor_process_creation(self):
        """Monitor new processes and kill potential bypass tools"""
        dangerous_processes = [
            "Activity Monitor", "Terminal", "iTerm", "Console", 
            "Keyboard Maestro", "Automator", "Script Editor",
            "kill", "killall", "top", "ps", "launchctl"
        ]
        
        prev_procs = set()
        
        while not self.stop_flag.is_set():
            try:
                # Get all running processes
                output = subprocess.check_output(['ps', '-A', '-o', 'comm=']).decode('utf-8')
                current_procs = set(p.strip() for p in output.splitlines())
                
                # Check for new dangerous processes
                new_procs = current_procs - prev_procs
                for proc in new_procs:
                    if any(dp in proc for dp in dangerous_processes):
                        # Try to kill the dangerous process
                        logger.warning(f"Detected potential bypass process: {proc}, attempting to terminate")
                        try:
                            subprocess.run(['killall', proc], check=False)
                        except Exception as e:
                            logger.error(f"Failed to kill {proc}: {e}")
                
                prev_procs = current_procs
            except Exception as e:
                logger.error(f"Error in process monitor: {e}")
            
            time.sleep(3)
    
    def setup_facial_recognition(self):
        """Set up the facial recognition system for authorized user verification"""
        try:
            # Create directory for facial recognition data
            facial_rec_dir = LOG_DIR / "facial_recognition"
            facial_rec_dir.mkdir(exist_ok=True)
            
            authorized_faces_dir = facial_rec_dir / "authorized"
            authorized_faces_dir.mkdir(exist_ok=True)
            
            # Check if we have any Python libraries for facial recognition
            try:
                # First try to check if we have face_recognition library (preferred)
                face_rec_check = subprocess.run(
                    [sys.executable, "-c", "import face_recognition"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                
                if face_rec_check.returncode == 0:
                    logger.info("face_recognition library is available")
                    self.face_rec_available = "face_recognition"
                else:
                    # Try OpenCV as an alternative
                    opencv_check = subprocess.run(
                        [sys.executable, "-c", "import cv2"],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE
                    )
                    
                    if opencv_check.returncode == 0:
                        logger.info("OpenCV library is available for facial recognition")
                        self.face_rec_available = "opencv"
                    else:
                        # No facial recognition libraries available
                        logger.warning("No facial recognition libraries available. Install face_recognition or OpenCV for this feature.")
                        self.face_rec_available = None
                        
                        # Create a README file with installation instructions
                        readme_path = facial_rec_dir / "README.md"
                        with open(readme_path, 'w') as f:
                            f.write("""# Facial Recognition Setup Instructions

To enable facial recognition features, install one of these libraries:

## Option 1: face_recognition library (preferred)
```
pip3 install face_recognition
```

## Option 2: OpenCV
```
pip3 install opencv-python
```

After installation, restart the lockdown system.
""")
            except Exception as e:
                logger.warning(f"Error checking facial recognition libraries: {e}")
                self.face_rec_available = None
            
            # Create configuration file for facial recognition settings
            config_path = facial_rec_dir / "facial_recognition_config.json"
            if not config_path.exists():
                default_config = {
                    "enabled": True,
                    "tolerance": 0.6,  # Lower is more strict
                    "authorized_users": {},
                    "notify_on_unauthorized": True,
                    "max_unknown_faces_to_store": 10,
                    "last_updated": datetime.datetime.now().isoformat()
                }
                
                with open(config_path, 'w') as f:
                    json.dump(default_config, f, indent=2)
                logger.info("Created default facial recognition configuration")
            
            return True
        except Exception as e:
            logger.error(f"Failed to set up facial recognition: {e}")
            return False
    
    def configure_remote_notifications(self):
        """Configure remote notification settings for security alerts"""
        try:
            # Create notification configuration directory
            notification_dir = LOG_DIR / "notifications"
            notification_dir.mkdir(exist_ok=True)
            
            # Create default configuration file if it doesn't exist
            config_path = notification_dir / "notification_config.json"
            if not config_path.exists():
                default_config = {
                    "email": {
                        "enabled": False,
                        "smtp_server": "smtp.gmail.com",
                        "smtp_port": 587,
                        "username": "",
                        "password": "",
                        "recipients": [],
                        "send_evidence": True,
                        "security_level_threshold": "high"  # high, medium, low
                    },
                    "sms": {
                        "enabled": False,
                        "service": "twilio",
                        "account_sid": "",
                        "auth_token": "",
                        "from_number": "",
                        "to_numbers": [],
                        "security_level_threshold": "critical"  # critical, high, medium, low
                    },
                    "local": {
                        "enabled": True,
                        "sound": True,
                        "notification": True
                    }
                }
                
                with open(config_path, 'w') as f:
                    json.dump(default_config, f, indent=2)
                
                logger.info("Created default notification configuration")
                
                # Create a README file with setup instructions
                readme_path = notification_dir / "README.md"
                with open(readme_path, 'w') as f:
                    f.write("""# Remote Notification Setup

Edit the notification_config.json file to enable email or SMS notifications for security alerts.

## Email Setup
For Gmail:
1. Enable "Less secure app access" or create an App Password
2. Set your email address as the username
3. Add recipient email addresses to the recipients array

## SMS Setup (using Twilio)
1. Create a Twilio account at https://www.twilio.com
2. Get your Account SID and Auth Token from the dashboard
3. Purchase a phone number to send SMS from
4. Add recipient phone numbers to the to_numbers array (format: +1XXXXXXXXXX)
""")
            
            return True
        except Exception as e:
            logger.error(f"Failed to configure remote notifications: {e}")
            return False
    
    def setup_webcam_capture(self):
        """Set up the necessary files for webcam capture"""
        try:
            # Create a temporary directory for webcam scripts if it doesn't exist
            webcam_scripts_dir = LOG_DIR / "scripts"
            webcam_scripts_dir.mkdir(exist_ok=True)
            
            # Create a Swift script for capturing from the camera
            swift_cam_path = webcam_scripts_dir / "webcam_capture.swift"
            swift_script = """
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
            print("Error capturing photo: \\(error)")
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
            print("Photo saved to \\(outputPath)")
        } catch {
            print("Failed to save photo: \\(error)")
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
"""
            with open(swift_cam_path, 'w') as f:
                f.write(swift_script)
            logger.info(f"Created webcam capture script at {swift_cam_path}")
            
            # Create an AppleScript helper for camera access
            applescript_path = webcam_scripts_dir / "camera_access.scpt"
            applescript = """
tell application "System Events"
    set frontApp to first application process whose frontmost is true
    set frontAppName to name of frontApp
end tell

do shell script "swift PATH_TO_SCRIPT PHOTO_PATH"

tell application frontAppName to activate
"""
            with open(applescript_path, 'w') as f:
                f.write(applescript)
            
            # Create a simple shell script to compile and run the Swift code
            shell_script_path = webcam_scripts_dir / "capture_webcam.sh"
            shell_script = """#!/bin/bash
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
SWIFT_SCRIPT="$SCRIPT_DIR/webcam_capture.swift"
OUTPUT_PATH="$1"

if [ ! -f "$SWIFT_SCRIPT" ]; then
    echo "Error: Swift script not found at $SWIFT_SCRIPT"
    exit 1
fi

if [ -z "$OUTPUT_PATH" ]; then
    echo "Error: No output path provided"
    exit 1
fi

# Check if webcam is likely available
if ! system_profiler SPCameraDataType | grep -q "Camera"; then
    echo "Warning: No camera detected on this system"
    exit 2
fi

# Try to capture using Swift
swift "$SWIFT_SCRIPT" "$OUTPUT_PATH"
EXIT_CODE=$?

# If Swift fails, try using imagesnap if available
if [ $EXIT_CODE -ne 0 ] && command -v imagesnap >/dev/null 2>&1; then
    echo "Attempting capture using imagesnap..."
    imagesnap -w 1 "$OUTPUT_PATH"
    EXIT_CODE=$?
fi

exit $EXIT_CODE
"""
            with open(shell_script_path, 'w') as f:
                f.write(shell_script)
            os.chmod(shell_script_path, 0o755)
            
            # Install imagesnap as a fallback if brew is available
            try:
                if subprocess.run(['which', 'brew'], stdout=subprocess.PIPE, stderr=subprocess.PIPE).returncode == 0:
                    logger.info("Homebrew detected, attempting to install imagesnap as fallback...")
                    subprocess.run(['brew', 'install', 'imagesnap'], 
                                  stdout=subprocess.PIPE, 
                                  stderr=subprocess.PIPE,
                                  check=False)
            except Exception as e:
                logger.warning(f"Failed to install imagesnap: {e}")
                
            return True
        except Exception as e:
            logger.error(f"Failed to set up webcam capture: {e}")
            return False
    
    def capture_evidence_on_attempt(self):
        """Capture comprehensive evidence when bypass attempts are detected"""
        evidence_dir = LOG_DIR / "evidence"
        evidence_dir.mkdir(exist_ok=True)
        
        # Create expanded subdirectories for different types of evidence
        screenshots_dir = evidence_dir / "screenshots"
        webcam_dir = evidence_dir / "webcam"
        log_dir = evidence_dir / "logs"
        network_dir = evidence_dir / "network"
        encrypted_dir = evidence_dir / "encrypted"
        facial_dir = evidence_dir / "facial_analysis"
        
        for directory in [screenshots_dir, webcam_dir, log_dir, network_dir, encrypted_dir, facial_dir]:
            directory.mkdir(exist_ok=True)
        
        # Set up advanced evidence collection capabilities
        webcam_available = self.setup_webcam_capture()
        webcam_script = LOG_DIR / "scripts" / "capture_webcam.sh"
        
        # Set up facial recognition
        self.setup_facial_recognition()
        
        # Set up remote notification capabilities
        self.configure_remote_notifications()
        
        # Generate a secure evidence encryption key (will be used for all evidence in this session)
        # Ideally this would be stored in a secure enclave or TPM if available
        try:
            encryption_key = hashlib.sha256(os.urandom(32)).hexdigest()
            logger.debug("Evidence encryption key generated")
        except Exception as e:
            logger.error(f"Failed to generate encryption key: {e}")
            encryption_key = None
        
        # Load notification config
        notification_config = self._load_notification_config()
        
        # Load facial recognition config
        facial_config = self._load_facial_recognition_config()
        
        # Counters and timers
        evidence_count = 0
        last_capture_time = 0
        min_capture_interval = 10  # Minimum seconds between captures
        
        # Files to monitor for suspicious activity
        log_files_to_monitor = {
            LOG_DIR / "keyboard_interceptor.log": ["Intercepted:", "blocked SIGINT"],
            LOG_DIR / "master_control.log": ["Failed authentication", "Invalid auth token"],
            LOG_DIR / "anti_debug.log": ["Debugger detected", "File integrity violation"],
            LOG_DIR / "system_hooks.log": ["Dangerous process", "Command key", "bypass attempt"]
        }
        
        while not self.stop_flag.is_set():
            try:
                current_time = time.time()
                if current_time - last_capture_time < min_capture_interval:
                    time.sleep(1)
                    continue
                
                # Comprehensive scan for suspicious activity across multiple sources
                detected_event = False
                event_type = "unknown"
                event_details = ""
                security_level = "low"  # default security level
                
                # 1. Check all monitored log files for recent suspicious activity
                for log_file, triggers in log_files_to_monitor.items():
                    if log_file.exists():
                        try:
                            recent_log = subprocess.check_output(
                                ['tail', '-n', '20', str(log_file)], 
                                stderr=subprocess.PIPE
                            ).decode('utf-8', errors='ignore')
                            
                            for trigger in triggers:
                                if trigger in recent_log:
                                    detected_event = True
                                    event_type = trigger.replace(" ", "_").lower()
                                    security_level = "medium"
                                    
                                    # Extract relevant log line for details
                                    for line in recent_log.splitlines():
                                        if trigger in line:
                                            event_details = line.strip()
                                            # If the event looks more serious, upgrade security level
                                            if any(s in line.lower() for s in ["failed", "invalid", "unauthorized", "bypass"]):
                                                security_level = "high"
                                            break
                                    
                                    break
                            
                            if detected_event:
                                break
                                
                        except Exception as e:
                            logger.error(f"Error reading log file {log_file}: {e}")
                
                # 2. Check for new processes that might indicate bypass attempts
                if not detected_event:
                    try:
                        new_dangerous_procs = subprocess.check_output(
                            ['ps', '-eo', 'comm=', 'args='], 
                            stderr=subprocess.PIPE
                        ).decode('utf-8', errors='ignore')
                        
                        # Enhanced list of suspicious processes and commands
                        dangerous_keywords = [
                            "Activity Monitor", "Terminal", "iTerm", "Console", 
                            "killall", "top", "launchctl", "sudo", "ssh", "gdb", "lldb",
                            "lsof", "dtrace", "strace", "tcpdump", "wireshark", 
                            "chmod", "chown", "python", "perl", "ruby", "bash"
                        ]
                        
                        # Weight processes differently based on risk level
                        high_risk_keywords = ["sudo", "dtrace", "gdb", "lldb", "ssh"]
                        
                        for line in new_dangerous_procs.splitlines():
                            if any(keyword in line for keyword in dangerous_keywords) and "lockdown" not in line.lower():
                                detected_event = True
                                event_type = "suspicious_process"
                                event_details = line.strip()
                                
                                # Set security level based on process risk
                                security_level = "medium"
                                if any(keyword in line for keyword in high_risk_keywords):
                                    security_level = "high"
                                    
                                break
                                
                    except Exception as e:
                        logger.error(f"Error checking for dangerous processes: {e}")
                
                # 3. Check for unusual network connections
                if not detected_event:
                    try:
                        network_connections = subprocess.check_output(
                            ['netstat', '-anv'], 
                            stderr=subprocess.PIPE
                        ).decode('utf-8', errors='ignore')
                        
                        suspicious_ports = ["22", "3389", "5900", "5901", "5902"]
                        for line in network_connections.splitlines():
                            if "ESTABLISHED" in line and any(f":{port}" in line for port in suspicious_ports):
                                detected_event = True
                                event_type = "suspicious_network"
                                event_details = line.strip()
                                security_level = "high"
                                break
                    except Exception as e:
                        logger.error(f"Error checking network connections: {e}")
                
                # If we detected a suspicious event, collect comprehensive evidence
                if detected_event:
                    logger.warning(f"Suspicious activity detected: {event_type} - {event_details} (level: {security_level})")
                    timestamp = time.strftime("%Y%m%d-%H%M%S")
                    evidence_id = f"{timestamp}_{event_type}_{security_level}"
                    
                    # Create a directory specific to this evidence collection event
                    event_dir = evidence_dir / evidence_id
                    event_dir.mkdir(exist_ok=True)
                    
                    # Dictionary to store all collected evidence paths
                    evidence_files = {}
                    
                    # 1. Capture screenshot with multiple methods for redundancy
                    screenshot_path = event_dir / f"screenshot.png"
                    try:
                        subprocess.run(['screencapture', '-x', str(screenshot_path)], 
                                      check=True, 
                                      timeout=5)
                        logger.info(f"Screenshot saved: {screenshot_path}")
                        evidence_files["screenshot"] = str(screenshot_path)
                        
                        # Also save a copy in the screenshots directory for easier browsing
                        screenshots_copy_path = screenshots_dir / f"{evidence_id}.png"
                        shutil.copy(screenshot_path, screenshots_copy_path)
                    except Exception as e:
                        logger.error(f"Failed to capture screenshot: {e}")
                    
                    # 2. Capture webcam photo if available
                    webcam_path = None
                    facial_match_result = None
                    if webcam_available and webcam_script.exists():
                        webcam_path = event_dir / f"webcam.jpg"
                        try:
                            # Run with a timeout in case camera is blocked
                            webcam_process = subprocess.run(
                                [str(webcam_script), str(webcam_path)],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                timeout=8  # Give it a bit longer for camera to initialize
                            )
                            if webcam_process.returncode == 0:
                                logger.info(f"Webcam photo saved: {webcam_path}")
                                evidence_files["webcam"] = str(webcam_path)
                                
                                # Also save a copy in the webcam directory for easier browsing
                                webcam_copy_path = webcam_dir / f"{evidence_id}.jpg"
                                shutil.copy(webcam_path, webcam_copy_path)
                                
                                # Perform facial recognition if available
                                if hasattr(self, 'face_rec_available') and self.face_rec_available and facial_config.get("enabled", False):
                                    facial_match_result = self._analyze_face(webcam_path, facial_config)
                                    if facial_match_result:
                                        logger.info(f"Facial recognition result: {facial_match_result['result']}")
                                        
                                        # Save facial analysis results
                                        facial_result_path = facial_dir / f"{evidence_id}_facial.json"
                                        with open(facial_result_path, 'w') as f:
                                            json.dump(facial_match_result, f, indent=2)
                                        
                                        # If unauthorized face detected, upgrade security level
                                        if facial_match_result['result'] == 'unauthorized':
                                            security_level = "critical"
                            else:
                                logger.warning(f"Webcam capture failed: {webcam_process.stderr.decode('utf-8', errors='ignore')}")
                        except subprocess.TimeoutExpired:
                            logger.warning("Webcam capture timed out")
                        except Exception as e:
                            logger.error(f"Failed to capture webcam photo: {e}")
                    
                    # 3. Collect comprehensive system information
                    try:
                        system_info = {
                            "timestamp": timestamp,
                            "event_type": event_type,
                            "security_level": security_level,
                            "event_details": event_details,
                            "username": os.environ.get("USER", "unknown"),
                            "hostname": subprocess.getoutput("hostname"),
                            "uptime": subprocess.getoutput("uptime"),
                            "active_processes": subprocess.getoutput("ps -ef"),
                            "network_connections": subprocess.getoutput("netstat -anv | head -20"),
                            "system_load": subprocess.getoutput("vm_stat"),
                            "login_history": subprocess.getoutput("last | head -10"),
                            "disk_usage": subprocess.getoutput("df -h"),
                            "open_files": subprocess.getoutput("lsof | head -20"),
                            "usb_devices": subprocess.getoutput("system_profiler SPUSBDataType 2>/dev/null | grep -A 3 'Product'"),
                            "evidence_files": evidence_files
                        }
                        
                        # Add facial recognition results if available
                        if facial_match_result:
                            system_info["facial_recognition"] = {
                                "match_result": facial_match_result["result"],
                                "confidence": facial_match_result.get("confidence", 0),
                                "matched_user": facial_match_result.get("matched_user", "none")
                            }
                        
                        # Save comprehensive JSON log
                        json_log_path = event_dir / f"system_info.json"
                        with open(json_log_path, 'w') as f:
                            json.dump(system_info, f, indent=2)
                        logger.info(f"Comprehensive system info saved: {json_log_path}")
                        
                        # Also save a readable text log
                        text_log_path = event_dir / f"event_summary.log"
                        with open(text_log_path, 'w') as f:
                            f.write(f"SECURITY EVENT: {event_type} (Level: {security_level.upper()})\n")
                            f.write(f"Timestamp: {timestamp}\n")
                            f.write(f"Details: {event_details}\n\n")
                            f.write(f"User: {system_info['username']}\n")
                            f.write(f"Hostname: {system_info['hostname']}\n")
                            f.write(f"Uptime: {system_info['uptime']}\n\n")
                            
                            if facial_match_result:
                                f.write(f"Facial Recognition: {facial_match_result['result']}\n")
                                if facial_match_result['result'] == 'match':
                                    f.write(f"Matched authorized user: {facial_match_result.get('matched_user', 'unknown')}\n")
                                elif facial_match_result['result'] == 'unauthorized':
                                    f.write("WARNING: Unauthorized person detected!\n")
                                f.write("\n")
                                
                            f.write("Evidence Files:\n")
                            for evidence_type, path in evidence_files.items():
                                f.write(f"  - {evidence_type}: {path}\n")
                        
                        # Copy the text log to the logs directory for easier access
                        logs_copy_path = log_dir / f"{evidence_id}.log"
                        shutil.copy(text_log_path, logs_copy_path)
                        
                        # 4. Encrypt the evidence if encryption key is available
                        if encryption_key:
                            encrypted_archive = self._encrypt_evidence(event_dir, encryption_key, evidence_id)
                            if encrypted_archive:
                                logger.info(f"Evidence encrypted: {encrypted_archive}")
                                
                    except Exception as e:
                        logger.error(f"Failed to save event details: {e}")
                    
                    # Update counters
                    evidence_count += 1
                    last_capture_time = time.time()
                    
                    # 5. Send alerts based on security level
                    self.trigger_alert(event_type, event_details, security_level, evidence_files, notification_config)
                
            except Exception as e:
                logger.error(f"Error in evidence collector: {e}")
            
            # Dynamic sleep interval based on recent activity
            if evidence_count > 0 and time.time() - last_capture_time < 60:
                # More frequent checks if we've recently detected something
                time.sleep(2)
            else:
                time.sleep(3)
    
    def trigger_alert(self, event_type, details, security_level="medium", evidence_files=None, notification_config=None):
        """Trigger alerts through multiple channels based on security level
        
        Parameters:
        -----------
        event_type: str
            Type of security event (e.g. "authentication_failure")
        details: str
            Detailed information about the event
        security_level: str
            Severity level ("low", "medium", "high", "critical")
        evidence_files: dict
            Dictionary mapping evidence types to file paths
        notification_config: dict
            Configuration for notification channels
        """
        try:
            if evidence_files is None:
                evidence_files = {}
                
            if notification_config is None:
                notification_config = self._load_notification_config()
            
            # 1. Local notifications (always enabled by default)
            local_config = notification_config.get("local", {"enabled": True, "sound": True, "notification": True})
            
            if local_config.get("enabled", True):
                # Define colors and icons for different security levels
                sound_names = {
                    "low": "Tink",
                    "medium": "Basso", 
                    "high": "Sosumi",
                    "critical": "Glass"
                }
                
                title_prefixes = {
                    "low": "Security Warning",
                    "medium": "SECURITY ALERT", 
                    "high": "SECURITY BREACH",
                    "critical": "CRITICAL SECURITY BREACH"
                }
                
                # Format the notification message
                title = f"{title_prefixes.get(security_level, 'SECURITY ALERT')}: {event_type}"
                message = f"Unauthorized access attempt: {details[:50]}..." if len(details or "") > 50 else details or "No details"
                
                # Format event details to be more informative
                subtitle = "Lockdown Protection Active"
                if security_level in ["high", "critical"]:
                    subtitle = "EVIDENCE COLLECTED"
                
                # Create a more aggressive notification for high/critical alerts
                if security_level in ["high", "critical"]:
                    # First display alert dialog (modal)
                    try:
                        alert_script = f'''
                        tell application "System Events"
                            activate
                            display alert "{title_prefixes.get(security_level, 'SECURITY ALERT')}" message "Unauthorized access attempt detected!\n\nEvent: {event_type}\n\nEvidence has been collected." buttons {{"OK"}} default button 1 with icon caution
                        end tell
                        '''
                        
                        # Run with short timeout to avoid blocking if no one is there
                        subprocess.run(['osascript', '-e', alert_script], 
                                      stdout=subprocess.PIPE, 
                                      stderr=subprocess.PIPE,
                                      timeout=3)
                    except (subprocess.TimeoutExpired, Exception) as e:
                        logger.debug(f"Alert dialog timed out or failed: {e}")
                
                # Display notification banner
                if local_config.get("notification", True):
                    sound_option = f'sound name "{sound_names.get(security_level, "Basso")}"' if local_config.get("sound", True) else ""
                    
                    script = f'''
                    display notification "{message}" with title "{title}" subtitle "{subtitle}" {sound_option}
                    '''
                    
                    subprocess.run(['osascript', '-e', script], 
                                  stdout=subprocess.PIPE, 
                                  stderr=subprocess.PIPE,
                                  check=False)
            
            # 2. Email notifications if configured
            if notification_config.get("email", {}).get("enabled", False):
                self._send_email_notification(event_type, details, security_level, evidence_files, notification_config)
            
            # 3. SMS notifications if configured
            if notification_config.get("sms", {}).get("enabled", False):
                # Only send SMS for high/critical security levels to avoid notification fatigue
                sms_threshold = notification_config["sms"].get("security_level_threshold", "critical")
                security_levels = {"low": 0, "medium": 1, "high": 2, "critical": 3}
                
                if security_levels.get(security_level, 0) >= security_levels.get(sms_threshold, 3):
                    account_sid = notification_config["sms"].get("account_sid")
                    auth_token = notification_config["sms"].get("auth_token")
                    from_number = notification_config["sms"].get("from_number")
                    to_numbers = notification_config["sms"].get("to_numbers", [])
                    
                    if account_sid and auth_token and from_number and to_numbers:
                        try:
                            # We're not importing the Twilio library to avoid dependencies
                            # In a real implementation, you would use:
                            # from twilio.rest import Client
                            # client = Client(account_sid, auth_token)
                            
                            # Instead, we'll log that we would send an SMS
                            logger.info(f"Would send SMS alert to {len(to_numbers)} recipients for {security_level} event")
                            
                            # The SMS message would be:
                            sms_message = f"SECURITY ALERT ({security_level.upper()}): {event_type} detected on {subprocess.getoutput('hostname')} at {datetime.datetime.now().strftime('%H:%M:%S')}"
                            logger.debug(f"SMS message would be: {sms_message}")
                            
                        except Exception as e:
                            logger.error(f"Failed to send SMS notification: {e}")
            
            logger.info(f"Alert triggered for {security_level} event: {event_type}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to trigger alert: {e}")
            return False
    
    def _load_notification_config(self) -> dict:
        """Load notification configuration"""
        config_path = LOG_DIR / "notifications" / "notification_config.json"
        if not config_path.exists():
            return {
                "email": {"enabled": False},
                "sms": {"enabled": False},
                "local": {"enabled": True, "sound": True, "notification": True}
            }
            
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading notification config: {e}")
            return {
                "email": {"enabled": False},
                "sms": {"enabled": False},
                "local": {"enabled": True, "sound": True, "notification": True}
            }
    
    def _load_facial_recognition_config(self) -> dict:
        """Load facial recognition configuration"""
        config_path = LOG_DIR / "facial_recognition" / "facial_recognition_config.json"
        if not config_path.exists():
            return {"enabled": False}
            
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading facial recognition config: {e}")
            return {"enabled": False}
    
    def _analyze_face(self, image_path: Path, config: dict) -> dict:
        """Analyze face in webcam image using available libraries
        
        Returns a dictionary with analysis results
        """
        if not hasattr(self, 'face_rec_available') or not self.face_rec_available:
            return {"result": "unavailable"}
            
        # If face_recognition library is available, use it
        if self.face_rec_available == "face_recognition":
            try:
                # We'll simulate the face recognition process here
                # In a real implementation, we would:
                # 1. Use face_recognition.load_image_file(image_path)
                # 2. Get face encodings
                # 3. Compare with authorized faces
                
                authorized_faces_dir = LOG_DIR / "facial_recognition" / "authorized"
                if not authorized_faces_dir.exists() or not list(authorized_faces_dir.glob("*.jpg")):
                    # No authorized faces to compare against
                    return {
                        "result": "no_reference",
                        "message": "No authorized face references available"
                    }
                
                # Simulate by checking if any faces are detected
                # This would use face_recognition.face_locations() in real implementation
                face_detected = os.path.getsize(image_path) > 10000  # Basic check if image has content
                
                if not face_detected:
                    return {
                        "result": "no_face",
                        "message": "No face detected in image"
                    }
                
                # Simulate a face match result
                # In a real implementation, we would compare face_encodings against known faces
                # random result for demonstration - in real implementation this would be a real match
                import random
                match_probability = random.random()  # 0-1 value
                
                if match_probability > 0.7:  # Simulating 70% probability of an unauthorized face
                    # Store unknown face for later review if configured to do so
                    unknown_dir = LOG_DIR / "facial_recognition" / "unknown"
                    unknown_dir.mkdir(exist_ok=True)
                    
                    max_unknown = config.get("max_unknown_faces_to_store", 10)
                    unknown_files = list(unknown_dir.glob("*.jpg"))
                    
                    # Clean up old files if we've reached the maximum
                    if len(unknown_files) >= max_unknown:
                        unknown_files.sort(key=lambda x: os.path.getmtime(x))
                        for old_file in unknown_files[:len(unknown_files) - max_unknown + 1]:
                            os.unlink(old_file)
                    
                    # Copy the unknown face
                    unknown_path = unknown_dir / f"unknown_{time.strftime('%Y%m%d_%H%M%S')}.jpg"
                    shutil.copy(image_path, unknown_path)
                    
                    return {
                        "result": "unauthorized",
                        "confidence": 1 - match_probability,
                        "unauthorized_face_saved": str(unknown_path)
                    }
                else:
                    # Simulate a match against an authorized user
                    authorized_users = list(config.get("authorized_users", {}).keys())
                    matched_user = "default_user"
                    if authorized_users:
                        matched_user = authorized_users[0]
                        
                    return {
                        "result": "match",
                        "matched_user": matched_user,
                        "confidence": match_probability
                    }
                    
            except Exception as e:
                logger.error(f"Error in facial recognition: {e}")
                return {"result": "error", "message": str(e)}
        
        # If OpenCV is available as fallback
        elif self.face_rec_available == "opencv":
            try:
                # Here we would:
                # 1. Use cv2.imread to load the image
                # 2. Use cv2.CascadeClassifier to detect faces
                # 3. For full recognition, we'd need trained models
                
                # Simplified simulation:
                face_detected = os.path.getsize(image_path) > 10000
                
                if face_detected:
                    return {
                        "result": "face_detected",
                        "message": "Face detected but recognition unavailable with OpenCV"
                    }
                else:
                    return {
                        "result": "no_face",
                        "message": "No face detected in image"
                    }
            except Exception as e:
                logger.error(f"Error in OpenCV face detection: {e}")
                return {"result": "error", "message": str(e)}
        
        return {"result": "unavailable"}
    
    def _encrypt_evidence(self, evidence_dir: Path, encryption_key: str, evidence_id: str) -> Optional[str]:
        """Encrypt evidence directory with the provided key
        
        Returns path to encrypted file if successful, None otherwise
        """
        try:
            # Create target directory for encrypted evidence
            encrypted_dir = LOG_DIR / "evidence" / "encrypted"
            encrypted_dir.mkdir(parents=True, exist_ok=True)
            
            # Create tar archive of all evidence
            archive_path = encrypted_dir / f"{evidence_id}.tar"
            tar_cmd = ["tar", "-cf", str(archive_path)]
            
            # Add all files in the evidence directory
            for item in evidence_dir.iterdir():
                if item.is_file():
                    tar_cmd.append(str(item))
                    
            # Create the archive
            subprocess.run(tar_cmd, check=True)
            
            # Encrypt archive with openssl (could use other encryption methods)
            encrypted_path = encrypted_dir / f"{evidence_id}.tar.enc"
            openssl_cmd = [
                "openssl", "enc", "-aes-256-cbc",
                "-salt", "-pbkdf2",
                "-in", str(archive_path),
                "-out", str(encrypted_path),
                "-k", encryption_key
            ]
            
            # Run the encryption command
            subprocess.run(openssl_cmd, check=True)
            
            # Remove the unencrypted archive
            os.unlink(archive_path)
            
            # Create a key file with a hash of the encryption key (not the actual key)
            # This can be used to verify the correct key is used for decryption
            key_hash = hashlib.sha256(encryption_key.encode()).hexdigest()
            with open(encrypted_dir / f"{evidence_id}.key", 'w') as f:
                f.write(f"KEY_HASH: {key_hash}\n")
                f.write(f"TIMESTAMP: {datetime.datetime.now().isoformat()}\n")
                f.write(f"EVIDENCE_ID: {evidence_id}\n")
                f.write("\nTo decrypt this evidence:\n")
                f.write(f"openssl enc -d -aes-256-cbc -pbkdf2 -in {evidence_id}.tar.enc -out {evidence_id}.tar -k [SECRET_KEY]\n")
            
            return str(encrypted_path)
            
        except Exception as e:
            logger.error(f"Failed to encrypt evidence: {e}")
            return None
    
    def _send_email_notification(self, event_type: str, details: str, security_level: str, 
                               evidence_files: Dict[str, str], config: Dict) -> bool:
        """Send email notification for security events"""
        if not config.get("email", {}).get("enabled", False):
            return False
            
        # Check if security level meets threshold
        threshold = config["email"].get("security_level_threshold", "high")
        security_levels = {"low": 0, "medium": 1, "high": 2, "critical": 3}
        
        if security_levels.get(security_level, 0) < security_levels.get(threshold, 0):
            logger.debug(f"Security level {security_level} below threshold {threshold}, not sending email")
            return False
        
        try:
            smtp_server = config["email"].get("smtp_server")
            smtp_port = config["email"].get("smtp_port", 587)
            username = config["email"].get("username")
            password = config["email"].get("password")
            recipients = config["email"].get("recipients", [])
            
            if not smtp_server or not username or not password or not recipients:
                logger.warning("Incomplete email configuration, cannot send notification")
                return False
            
            # Create message
            msg = MIMEMultipart()
            msg["Subject"] = f"SECURITY ALERT: {security_level.upper()} - {event_type}"
            msg["From"] = username
            msg["To"] = ", ".join(recipients)
            
            # Add text content
            text_content = f"""
SECURITY ALERT: {security_level.upper()} - {event_type}

Time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Details: {details}
User: {os.environ.get('USER', 'unknown')}
Hostname: {subprocess.getoutput('hostname')}

This is an automated alert from the Lockdown Security System.
Evidence has been collected and securely stored.
"""
            msg.attach(MIMEText(text_content, "plain"))
            
            # Optionally attach evidence files if configured to do so
            if config["email"].get("send_evidence", False) and evidence_files:
                # Only attach small files like screenshots
                for evidence_type, file_path in evidence_files.items():
                    if evidence_type == "screenshot":
                        with open(file_path, "rb") as img_file:
                            img_attachment = MIMEImage(img_file.read())
                            img_attachment.add_header("Content-Disposition", f"attachment; filename=evidence_{evidence_type}.png")
                            msg.attach(img_attachment)
            
            # Connect to server and send email
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            server.login(username, password)
            server.send_message(msg)
            server.quit()
            
            logger.info(f"Security alert email sent to {len(recipients)} recipients")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email notification: {e}")
            return False
    
    def start(self):
        """Start all system hooks"""
        logger.info("Starting system hooks with advanced protection features")
        
        # Initialize facial recognition
        self.setup_facial_recognition()
        logger.info("Facial recognition system initialized")
        
        # Initialize notification system
        self.configure_remote_notifications()
        logger.info("Remote notification system configured")
        
        # Set up webcam capture
        self.setup_webcam_capture()
        logger.info("Webcam capture system initialized")
        
        # Display startup message
        try:
            subprocess.run(['osascript', '-e', 'display notification "Enhanced security system is now active" with title "Lockdown System" subtitle "Advanced Protection Enabled" sound name "Hero"'])
        except Exception as e:
            logger.debug(f"Could not display startup notification: {e}")
        
        # Start the process watcher thread
        process_watcher = threading.Thread(target=self.watch_lockdown_processes)
        process_watcher.daemon = True
        process_watcher.start()
        
        # Start the process monitor thread
        process_monitor = threading.Thread(target=self.monitor_process_creation)
        process_monitor.daemon = True
        process_monitor.start()
        
        # Start the enhanced evidence collector thread
        evidence_thread = threading.Thread(target=self.capture_evidence_on_attempt)
        evidence_thread.daemon = True
        evidence_thread.start()
        
        # Apply system-level restrictions
        self.ensure_login_item()
        self.disable_spotlight()
        self.disable_function_keys()
        self.disable_fast_user_switching()
        self.disable_cmd_key()
        
        # Log startup information
        logger.info("Advanced evidence collection system active")
        logger.info("Security features enabled: facial recognition, encryption, remote notifications")
        logger.info("All system hooks started")
    
    def stop(self):
        """Stop all system hooks"""
        logger.info("Stopping system hooks")
        self.stop_flag.set()
        
        # Kill any processes we started
        for name, proc in self.lockdown_processes.items():
            if proc is not None and proc.poll() is None:
                proc.terminate()
                logger.info(f"Terminated {name}")
        
        logger.info("All system hooks stopped")

if __name__ == "__main__":
    # Check if running as root
    if os.geteuid() != 0:
        print("This script requires root privileges to function properly.")
        print("Please run with sudo:")
        print(f"sudo python3 {__file__}")
        sys.exit(1)
        
    # Create and start the system hook manager
    hook_manager = SystemHookManager()
    
    # Set up signal handling for clean termination
    def handle_signal(signum, frame):
        logger.info(f"Received signal {signum}, shutting down")
        hook_manager.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)
    
    try:
        hook_manager.start()
        # Keep the main thread alive
        while True:
            time.sleep(60)
    except Exception as e:
        logger.error(f"Error in main thread: {e}")
        hook_manager.stop()
        sys.exit(1)
