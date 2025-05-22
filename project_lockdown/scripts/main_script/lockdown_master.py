#!/usr/bin/env python3
"""
Lockdown Master Control System

This script serves as the main controller for the entire lockdown system,
coordinating all security components and implementing self-repair capabilities.

Features:
- Orchestrates all lockdown components
- Monitors component health and restarts failed components
- Implements redundant security measures
- Handles authentication and unlocking
- Provides audit logging and evidence collection

Usage: Run as root for full functionality
"""
import os
import sys
import time
import json
import signal
import hashlib
import logging
import datetime
import threading
import subprocess
import importlib.util
import shutil
from typing import Dict, List, Any, Optional, Union, Tuple
from pathlib import Path

# Configure logging
LOG_DIR = Path.home() / "Library" / "Logs" / "project_lockdown"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "master_control.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('master_control')

# Directory containing lockdown scripts
SCRIPT_DIR = Path(__file__).parent.resolve()

class ComponentStatus:
    UNKNOWN = "unknown"
    RUNNING = "running"
    FAILED = "failed"
    RESTARTING = "restarting"
    DISABLED = "disabled"

class LockdownMasterControl:
    def __init__(self):
        self.stop_flag = threading.Event()
        self.component_locks = {}
        self.config_file = SCRIPT_DIR / "lockdown_config.json"
        self.default_config = {
            "components": {
                "keyboard_interceptor": {
                    "script": "keyboard_interceptor.py",
                    "required": True,
                    "restart_attempts": 3,
                    "restart_delay": 3,
                },
                "input_blocker": {
                    "script": "input_blocker2.py",
                    "required": True,
                    "restart_attempts": 3,
                    "restart_delay": 3,
                },
                "password_checker": {
                    "script": "password_checker.py",
                    "required": True,
                    "restart_attempts": 3,
                    "restart_delay": 3,
                },
                "system_hooks": {
                    "script": "system_hooks.py",
                    "required": False,
                    "restart_attempts": 2,
                    "restart_delay": 5,
                },
                "network_monitor": {
                    "script": "network_monitor.py",
                    "required": False,
                    "restart_attempts": 2,
                    "restart_delay": 5,
                },
                "anti_debug": {
                    "script": "anti_debug.py",
                    "required": False,
                    "restart_attempts": 2,
                    "restart_delay": 5,
                },
            },
            "security": {
                "password_hash": "",  # Will be set on first run
                "max_auth_attempts": 5,
                "lockout_duration": 300,  # 5 minutes
                "auth_required_components": ["password_checker"],
                "auto_update": True,
                "collect_evidence": True,
                "evidence_dir": str(LOG_DIR / "evidence"),
            },
            "runtime": {
                "check_interval": 3,
                "max_downtime": 5,
                "auth_attempts": 0,
                "last_auth_time": 0,
            }
        }
        self.config = self.load_config()
        self.component_processes = {}
        self.component_status = {}
        self.auth_token = None
        
        # Set up component locks
        for component_name in self.config["components"]:
            self.component_locks[component_name] = threading.Lock()
            self.component_status[component_name] = ComponentStatus.UNKNOWN
        
    def load_config(self) -> Dict:
        """Load configuration or create default if it doesn't exist"""
        if not self.config_file.exists():
            logger.info("Creating default configuration")
            os.makedirs(self.config_file.parent, exist_ok=True)
            
            # Create evidence directory
            evidence_dir = Path(self.default_config["security"]["evidence_dir"])
            evidence_dir.mkdir(parents=True, exist_ok=True)
            
            with open(self.config_file, 'w') as f:
                json.dump(self.default_config, f, indent=2)
                
            return self.default_config
        
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)
                # Update with any missing values from default config
                for section, values in self.default_config.items():
                    if section not in config:
                        config[section] = values
                    elif isinstance(values, dict):
                        for key, val in values.items():
                            if key not in config[section]:
                                config[section][key] = val
                return config
        except Exception as e:
            logger.error(f"Error loading config: {e}, using default")
            return self.default_config
    
    def save_config(self) -> None:
        """Save current configuration to file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
            logger.info("Configuration saved")
        except Exception as e:
            logger.error(f"Failed to save config: {e}")
    
    def set_password(self, password: str) -> None:
        """Set a new master password for the lockdown system"""
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        self.config["security"]["password_hash"] = password_hash
        self.save_config()
        logger.info("New master password set")
    
    def verify_password(self, password: str) -> bool:
        """Verify the master password"""
        stored_hash = self.config["security"]["password_hash"]
        if not stored_hash:
            logger.warning("No password hash stored, any password will be accepted")
            return True
            
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        result = password_hash == stored_hash
        
        # Update auth attempts
        if result:
            self.config["runtime"]["auth_attempts"] = 0
            self.config["runtime"]["last_auth_time"] = time.time()
            self.auth_token = hashlib.sha256(os.urandom(32)).hexdigest()
            logger.info("Password verified successfully")
        else:
            self.config["runtime"]["auth_attempts"] += 1
            logger.warning(f"Failed authentication attempt ({self.config['runtime']['auth_attempts']})")
            
        self.save_config()
        return result
    
    def is_locked_out(self) -> bool:
        """Check if authentication is currently locked out due to too many attempts"""
        max_attempts = self.config["security"]["max_auth_attempts"]
        lockout_duration = self.config["security"]["lockout_duration"]
        
        if self.config["runtime"]["auth_attempts"] >= max_attempts:
            last_attempt = self.config["runtime"]["last_auth_time"]
            time_since = time.time() - last_attempt
            
            if time_since < lockout_duration:
                time_left = int(lockout_duration - time_since)
                logger.warning(f"Authentication locked out for {time_left} more seconds")
                return True
            else:
                # Reset the counter after lockout period has passed
                self.config["runtime"]["auth_attempts"] = 0
                self.save_config()
                
        return False
    
    def start_component(self, component_name: str) -> bool:
        """Start a single component of the lockdown system"""
        with self.component_locks[component_name]:
            component_config = self.config["components"][component_name]
            script_path = SCRIPT_DIR / component_config["script"]
            
            if not script_path.exists():
                logger.error(f"Component script not found: {script_path}")
                self.component_status[component_name] = ComponentStatus.FAILED
                return False
            
            try:
                # Check if the component is already running
                if (component_name in self.component_processes and 
                    self.component_processes[component_name] is not None and 
                    self.component_processes[component_name].poll() is None):
                    logger.info(f"Component {component_name} is already running")
                    self.component_status[component_name] = ComponentStatus.RUNNING
                    return True
                
                logger.info(f"Starting component: {component_name}")
                self.component_status[component_name] = ComponentStatus.RESTARTING
                
                # Some components may need to run with elevated privileges
                elevate = False
                if component_name in ["system_hooks", "network_monitor"]:
                    elevate = True
                
                cmd = [sys.executable, str(script_path)]
                if elevate and os.geteuid() == 0:
                    # We're already running as root
                    process = subprocess.Popen(
                        cmd, 
                        stdout=subprocess.PIPE, 
                        stderr=subprocess.PIPE
                    )
                else:
                    # Regular user-level privileges
                    process = subprocess.Popen(
                        cmd, 
                        stdout=subprocess.PIPE, 
                        stderr=subprocess.PIPE
                    )
                
                self.component_processes[component_name] = process
                self.component_status[component_name] = ComponentStatus.RUNNING
                logger.info(f"Component {component_name} started with PID {process.pid}")
                return True
                
            except Exception as e:
                logger.error(f"Failed to start component {component_name}: {e}")
                self.component_status[component_name] = ComponentStatus.FAILED
                return False
    
    def stop_component(self, component_name: str) -> bool:
        """Stop a single component of the lockdown system"""
        with self.component_locks[component_name]:
            if component_name not in self.component_processes:
                logger.warning(f"Component {component_name} not found in process list")
                return False
                
            process = self.component_processes[component_name]
            if process is None or process.poll() is not None:
                logger.info(f"Component {component_name} is not running")
                self.component_status[component_name] = ComponentStatus.DISABLED
                return True
                
            try:
                logger.info(f"Stopping component: {component_name}")
                # Try to terminate gracefully
                process.terminate()
                
                # Wait a bit for graceful termination
                for _ in range(10):
                    if process.poll() is not None:
                        break
                    time.sleep(0.1)
                
                # If still running, force kill
                if process.poll() is None:
                    logger.warning(f"Component {component_name} did not terminate gracefully, force killing")
                    process.kill()
                    
                # Collect any output
                stdout, stderr = process.communicate(timeout=2)
                if stdout:
                    logger.info(f"Component {component_name} output: {stdout.decode('utf-8', errors='ignore').strip()}")
                if stderr:
                    logger.warning(f"Component {component_name} errors: {stderr.decode('utf-8', errors='ignore').strip()}")
                
                self.component_status[component_name] = ComponentStatus.DISABLED
                logger.info(f"Component {component_name} stopped")
                return True
                
            except Exception as e:
                logger.error(f"Failed to stop component {component_name}: {e}")
                return False
    
    def check_component(self, component_name: str) -> bool:
        """Check if a component is running properly and restart if needed"""
        component_config = self.config["components"][component_name]
        required = component_config["required"]
        
        with self.component_locks[component_name]:
            if component_name not in self.component_processes:
                if required:
                    logger.warning(f"Required component {component_name} not started, starting now")
                    return self.start_component(component_name)
                else:
                    return True  # Non-required component, absence is fine
            
            process = self.component_processes[component_name]
            if process is None:
                if required:
                    logger.warning(f"Required component {component_name} has no process, starting now")
                    return self.start_component(component_name)
                else:
                    return True  # Non-required component, absence is fine
            
            # Check if the process is still running
            if process.poll() is not None:
                exit_code = process.poll()
                logger.warning(f"Component {component_name} exited with code {exit_code}")
                
                if required:
                    logger.info(f"Attempting to restart {component_name}")
                    return self.start_component(component_name)
                else:
                    self.component_status[component_name] = ComponentStatus.FAILED
                    return True  # Non-required component, failure is acceptable
            
            # Process is running
            self.component_status[component_name] = ComponentStatus.RUNNING
            return True
    
    def check_all_components(self) -> bool:
        """Check all components and restart any that have failed"""
        all_ok = True
        for component_name in self.config["components"]:
            component_ok = self.check_component(component_name)
            all_ok = all_ok and component_ok
        return all_ok
    
    def monitor_components(self) -> None:
        """Monitor all components in a loop and restart any that fail"""
        check_interval = self.config["runtime"]["check_interval"]
        while not self.stop_flag.is_set():
            try:
                self.check_all_components()
                
                # Report system status periodically
                statuses = {name: status for name, status in self.component_status.items()}
                logger.debug(f"Component statuses: {statuses}")
                
            except Exception as e:
                logger.error(f"Error in component monitor: {e}")
                
            # Sleep for the check interval
            for _ in range(int(check_interval * 10)):
                if self.stop_flag.is_set():
                    break
                time.sleep(0.1)
    
    def collect_evidence(self, event_type: str, details: str = None, security_level: str = "high") -> None:
        """Collect comprehensive evidence of intrusion attempts or suspicious activity
        
        Parameters:
        -----------
        event_type: str
            Type of security event (e.g. "authentication_failure")
        details: str
            Detailed information about the event
        security_level: str
            Severity level ("low", "medium", "high", "critical")
        """
        if not self.config["security"]["collect_evidence"]:
            return
            
        try:
            evidence_dir = Path(self.config["security"]["evidence_dir"])
            evidence_dir.mkdir(parents=True, exist_ok=True)
            
            # Create expanded subdirectories for different types of evidence
            screenshots_dir = evidence_dir / "screenshots"
            webcam_dir = evidence_dir / "webcam" 
            logs_dir = evidence_dir / "logs"
            network_dir = evidence_dir / "network"
            encrypted_dir = evidence_dir / "encrypted"
            facial_dir = evidence_dir / "facial_analysis"
            
            for dir_path in [screenshots_dir, webcam_dir, logs_dir, network_dir, encrypted_dir, facial_dir]:
                dir_path.mkdir(exist_ok=True)
            
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            evidence_id = f"{timestamp}_{event_type.replace(' ', '_')}_{security_level}"
            
            # Create a directory specific to this evidence collection event
            event_dir = evidence_dir / evidence_id
            event_dir.mkdir(exist_ok=True)
            
            # Gather enhanced system information with more detailed diagnostics
            system_info = {
                "timestamp": timestamp,
                "event_type": event_type,
                "security_level": security_level,
                "details": details,
                "components": self.component_status,
                "authentication": {
                    "attempts": self.config["runtime"]["auth_attempts"],
                    "last_auth_time": self.config["runtime"]["last_auth_time"],
                    "lockout_status": self.is_locked_out()
                },
                "user": os.environ.get("USER", "unknown"),
                "hostname": subprocess.getoutput("hostname"),
                "uptime": subprocess.getoutput("uptime"),
                "active_processes": subprocess.getoutput("ps -ef | grep -v grep | grep -E 'Terminal|Activity|Console|Python|bash|zsh|ssh' || echo 'No matching processes'"),
                "network_connections": subprocess.getoutput("netstat -anv | grep ESTABLISHED || echo 'No established connections'"),
                "login_history": subprocess.getoutput("last | head -5"),
                "system_load": subprocess.getoutput("vm_stat"),
                "open_ports": subprocess.getoutput("lsof -i -P | grep LISTEN || echo 'No listening ports'"),
                "usb_devices": subprocess.getoutput("system_profiler SPUSBDataType 2>/dev/null | grep -A 3 'Product' || echo 'No USB devices found'")
            }
            
            # 1. Capture screenshot with multiples methods for redundancy
            screenshot_path = event_dir / "screenshot.png"
            try:
                # Try the primary method
                subprocess.run(['screencapture', '-x', str(screenshot_path)], 
                              check=True, 
                              timeout=5)
                
                # Also save a copy in the screenshots directory for easier browsing
                screenshots_copy = screenshots_dir / f"{evidence_id}.png"
                shutil.copy(screenshot_path, screenshots_copy)
                
                system_info["evidence_files"] = {"screenshot": str(screenshot_path)}
                logger.info(f"Screenshot captured: {screenshot_path}")
            except Exception as e:
                logger.warning(f"Failed to capture screenshot with primary method: {e}")
                
                # Try alternative method using screencapture with different flags
                try:
                    subprocess.run(['screencapture', '-C', '-x', str(screenshot_path)], 
                                  check=True, 
                                  timeout=5)
                    system_info["evidence_files"] = {"screenshot": str(screenshot_path)}
                    logger.info(f"Screenshot captured with alternative method")
                except Exception as e2:
                    logger.error(f"All screenshot capture methods failed: {e2}")
            
            # 2. Try to capture webcam photo using multiple methods
            webcam_script = SCRIPT_DIR / "scripts" / "capture_webcam.sh"
            webcam_path = event_dir / "webcam.jpg"
            
            # Look in multiple locations for the webcam script
            possible_webcam_scripts = [
                webcam_script,
                Path(SCRIPT_DIR).parent / "scripts" / "capture_webcam.sh",
                LOG_DIR / "scripts" / "capture_webcam.sh",
                Path.home() / "Library" / "Logs" / "project_lockdown" / "scripts" / "capture_webcam.sh"
            ]
            
            webcam_script = None
            for script_path in possible_webcam_scripts:
                if script_path.exists():
                    webcam_script = script_path
                    break
            
            if webcam_script:
                try:
                    # Run with a timeout in case camera is blocked
                    webcam_process = subprocess.run(
                        [str(webcam_script), str(webcam_path)],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        timeout=8
                    )
                    if webcam_process.returncode == 0:
                        if not "evidence_files" in system_info:
                            system_info["evidence_files"] = {}
                        system_info["evidence_files"]["webcam"] = str(webcam_path)
                        
                        # Also save a copy in the webcam directory for easier browsing
                        webcam_copy = webcam_dir / f"{evidence_id}.jpg"
                        shutil.copy(webcam_path, webcam_copy)
                        
                        logger.info(f"Webcam photo captured: {webcam_path}")
                    else:
                        logger.warning(f"Webcam capture failed: {webcam_process.stderr.decode('utf-8', errors='ignore')}")
                except Exception as e:
                    logger.warning(f"Failed to capture webcam photo: {e}")
            else:
                # Try to create webcam capture script if it doesn't exist
                try:
                    scripts_dir = LOG_DIR / "scripts"
                    scripts_dir.mkdir(exist_ok=True)
                    
                    # First check if imagesnap is available and use it
                    if subprocess.run(['which', 'imagesnap'], 
                                     stdout=subprocess.PIPE, 
                                     stderr=subprocess.PIPE).returncode == 0:
                        webcam_sh = scripts_dir / "capture_webcam.sh"
                        
                        # Create a more robust script with multiple methods
                        with open(webcam_sh, 'w') as f:
                            f.write("""#!/bin/bash
# Advanced webcam capture script with multiple methods
OUTPUT_PATH="$1"

if [ -z "$OUTPUT_PATH" ]; then
    echo "Error: No output path provided"
    exit 1
fi

# Method 1: Use imagesnap
if command -v imagesnap >/dev/null 2>&1; then
    echo "Attempting capture with imagesnap..."
    imagesnap -w 1 "$OUTPUT_PATH"
    if [ -f "$OUTPUT_PATH" ] && [ -s "$OUTPUT_PATH" ]; then
        echo "Success: Captured with imagesnap"
        exit 0
    fi
fi

# Method 2: Use AppleScript and Photo Booth
echo "Attempting capture with Photo Booth..."
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
        if [ -f "$OUTPUT_PATH" ] && [ -s "$OUTPUT_PATH" ]; then
            echo "Success: Copied from Photo Booth"
            exit 0
        fi
    fi
fi

echo "All webcam capture methods failed"
exit 1
""")
                        os.chmod(webcam_sh, 0o755)
                        
                        # Try using the new script
                        subprocess.run(
                            [str(webcam_sh), str(webcam_path)],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            timeout=10  # Longer timeout for multi-method script
                        )
                        
                        if webcam_path.exists() and webcam_path.stat().st_size > 0:
                            logger.info(f"Created and used new webcam script: {webcam_sh}")
                            if not "evidence_files" in system_info:
                                system_info["evidence_files"] = {}
                            system_info["evidence_files"]["webcam"] = str(webcam_path)
                            
                            # Also save a copy in the webcam directory
                            webcam_copy = webcam_dir / f"{evidence_id}.jpg"
                            shutil.copy(webcam_path, webcam_copy)
                    else:
                        logger.warning("No webcam capture methods available")
                except Exception as e:
                    logger.warning(f"Could not create webcam script: {e}")
            
            # 3. Collect network evidence
            try:
                network_dump_path = event_dir / "network_connections.txt"
                with open(network_dump_path, "w") as f:
                    f.write("ACTIVE NETWORK CONNECTIONS\n")
                    f.write("=========================\n\n")
                    
                    # Get established connections
                    f.write("ESTABLISHED CONNECTIONS:\n")
                    netstat = subprocess.getoutput("netstat -anv | grep ESTABLISHED")
                    f.write(netstat + "\n\n")
                    
                    # Get listening ports
                    f.write("LISTENING PORTS:\n")
                    listening = subprocess.getoutput("lsof -i -P | grep LISTEN")
                    f.write(listening + "\n\n")
                    
                    # Get DNS configuration
                    f.write("DNS CONFIGURATION:\n")
                    dns = subprocess.getoutput("scutil --dns | grep nameserver")
                    f.write(dns + "\n\n")
                
                # Save copy to network directory
                network_copy = network_dir / f"{evidence_id}_network.txt"
                shutil.copy(network_dump_path, network_copy)
                
                if not "evidence_files" in system_info:
                    system_info["evidence_files"] = {}
                system_info["evidence_files"]["network"] = str(network_dump_path)
                
                logger.info(f"Network evidence collected: {network_dump_path}")
            except Exception as e:
                logger.warning(f"Failed to collect network evidence: {e}")
            
            # 4. Write comprehensive JSON log with all evidence
            evidence_file = event_dir / "system_info.json"
            with open(evidence_file, 'w') as f:
                json.dump(system_info, f, indent=2)
            
            # Also save a copy in the logs directory for easier access
            json_copy = logs_dir / f"{evidence_id}.json"
            shutil.copy(evidence_file, json_copy)
            
            # 5. Save human-readable text version too for easier reading
            text_log = event_dir / "event_summary.log"
            with open(text_log, 'w') as f:
                f.write(f"SECURITY EVENT: {event_type} (Level: {security_level.upper()})\n")
                f.write(f"Timestamp: {timestamp}\n")
                f.write(f"Details: {details}\n\n")
                
                f.write("SYSTEM INFORMATION\n")
                f.write("=================\n")
                f.write(f"User: {system_info['user']}\n")
                f.write(f"Hostname: {system_info['hostname']}\n")
                f.write(f"Uptime: {system_info['uptime']}\n\n")
                
                f.write("AUTHENTICATION STATUS\n")
                f.write("====================\n")
                f.write(f"Auth Attempts: {system_info['authentication']['attempts']}\n")
                f.write(f"Lockout Status: {'LOCKED' if system_info['authentication']['lockout_status'] else 'Not Locked'}\n\n")
                
                f.write("COMPONENT STATUS\n")
                f.write("===============\n")
                for component, status in self.component_status.items():
                    f.write(f"  - {component}: {status}\n")
                f.write("\n")
                
                f.write("EVIDENCE FILES\n")
                f.write("=============\n")
                if "evidence_files" in system_info:
                    for evidence_type, path in system_info["evidence_files"].items():
                        f.write(f"  - {evidence_type}: {path}\n")
                f.write("\n")
                
                f.write("SYSTEM DIAGNOSTICS\n")
                f.write("=================\n")
                f.write("Recent logins:\n")
                f.write(f"{system_info['login_history']}\n\n")
                f.write("Open ports:\n")
                f.write(f"{system_info['open_ports']}\n\n")
                
            # Save a copy to the logs directory
            text_copy = logs_dir / f"{evidence_id}.log"
            shutil.copy(text_log, text_copy)
            
            logger.info(f"Collected comprehensive evidence for {event_type} event: {evidence_file}")
            
            # 6. Try to encrypt the evidence directory
            try:
                encryption_key = os.urandom(32).hex()
                encrypted_dir = LOG_DIR / "evidence" / "encrypted"
                encrypted_dir.mkdir(exist_ok=True)
                
                # Create a tar archive of the evidence directory
                archive_path = encrypted_dir / f"{evidence_id}.tar"
                tar_cmd = ["tar", "-cf", str(archive_path), str(event_dir)]
                
                subprocess.run(tar_cmd, 
                              stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE,
                              check=False)
                
                # Encrypt with OpenSSL if available
                if subprocess.run(['which', 'openssl'], 
                                stdout=subprocess.PIPE, 
                                stderr=subprocess.PIPE).returncode == 0:
                    encrypted_path = encrypted_dir / f"{evidence_id}.enc"
                    encrypt_cmd = [
                        "openssl", "enc", "-aes-256-cbc",
                        "-salt", "-pbkdf2",
                        "-in", str(archive_path),
                        "-out", str(encrypted_path),
                        "-k", encryption_key
                    ]
                    
                    subprocess.run(encrypt_cmd, 
                                  stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE,
                                  check=False)
                    
                    if encrypted_path.exists():
                        logger.info(f"Evidence encrypted and saved to {encrypted_path}")
                        
                        # Save key to secure location (in production, would use a more secure method)
                        key_path = encrypted_dir / f"{evidence_id}.key"
                        with open(key_path, 'w') as f:
                            f.write(f"KEY: {encryption_key}\n")
                            f.write(f"TIMESTAMP: {timestamp}\n")
                            f.write(f"EVIDENCE_ID: {evidence_id}\n")
                            f.write("NOTE: In a production environment, this key would be stored securely separately.\n")
                        
                        # Try to remove the unencrypted tar if encryption worked
                        if archive_path.exists():
                            os.unlink(archive_path)
            except Exception as e:
                logger.warning(f"Could not encrypt evidence: {e}")
            
            # 7. Trigger alert based on security level
            try:
                # Define alert parameters based on security level
                alert_sounds = {
                    "low": "Tink",
                    "medium": "Basso",
                    "high": "Sosumi",
                    "critical": "Glass"
                }
                
                alert_titles = {
                    "low": "Security Notice",
                    "medium": "SECURITY ALERT",
                    "high": "SECURITY BREACH",
                    "critical": "CRITICAL SECURITY BREACH"
                }
                
                title = f"{alert_titles.get(security_level, 'SECURITY ALERT')}: {event_type}"
                message = f"Evidence collected: {details[:50]}..." if details else "See logs for details"
                sound = alert_sounds.get(security_level, "Basso")
                
                script = f'''
                display notification "{message}" with title "{title}" subtitle "Lockdown Evidence Collection" sound name "{sound}"
                '''
                
                subprocess.run(['osascript', '-e', script], 
                              stdout=subprocess.PIPE, 
                              stderr=subprocess.PIPE,
                              check=False)
                
                # For high or critical events, also show an alert dialog
                if security_level in ["high", "critical"]:
                    alert_script = f'''
                    tell application "System Events"
                        activate
                        display alert "{title}" message "{message}" buttons {{"OK"}} default button 1 with icon caution
                    end tell
                    '''
                    
                    # Try with a short timeout to avoid blocking if user isn't present
                    try:
                        subprocess.run(['osascript', '-e', alert_script], 
                                      stdout=subprocess.PIPE, 
                                      stderr=subprocess.PIPE,
                                      timeout=2)
                    except subprocess.TimeoutExpired:
                        pass
                
                logger.info(f"Alert triggered for {security_level} {event_type} event")
            except Exception as e:
                logger.warning(f"Could not trigger alert: {e}")
            
        except Exception as e:
            logger.error(f"Failed to collect evidence: {e}")
    
    def authenticate(self, password: str) -> str:
        """Authenticate with the system and get an auth token"""
        if self.is_locked_out():
            return None
        
        if self.verify_password(password):
            return self.auth_token
        
        return None
    
    def unlock_system(self, auth_token: str) -> bool:
        """Unlock the system if the auth token is valid"""
        if auth_token != self.auth_token or self.auth_token is None:
            logger.warning("Invalid auth token provided")
            self.collect_evidence("invalid_unlock_attempt", f"Invalid token: {auth_token}", "critical")
            return False
            
        try:
            logger.info("Valid auth token received, unlocking system")
            
            # Stop all components to release control
            for component_name in list(self.component_processes.keys()):
                logger.info(f"Stopping {component_name} as part of system unlock")
                self.stop_component(component_name)
            
            # Clear the auth token
            self.auth_token = None
            
            logger.info("System unlocked successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error unlocking system: {e}")
            return False
    
    def start(self, master_password: str = None) -> None:
        """Start the master control and all lockdown components"""
        if master_password:
            self.set_password(master_password)
        elif not self.config["security"]["password_hash"]:
            default_password = "lockdown"
            logger.warning(f"No password set, using default password: {default_password}")
            self.set_password(default_password)
            
        logger.info("Starting lockdown master control")
        
        # Start the component monitor thread
        monitor_thread = threading.Thread(target=self.monitor_components)
        monitor_thread.daemon = True
        monitor_thread.start()
        
        # Start all components
        for component_name in self.config["components"]:
            component_config = self.config["components"][component_name]
            if component_config.get("enabled", True):
                self.start_component(component_name)
            
        logger.info("Lockdown system fully activated")
    
    def stop(self) -> None:
        """Stop all lockdown components and the master control"""
        logger.info("Stopping lockdown system")
        self.stop_flag.set()
        
        # Stop all components in reverse startup order
        component_names = list(self.config["components"].keys())
        component_names.reverse()
        
        for component_name in component_names:
            if component_name in self.component_processes:
                self.stop_component(component_name)
                
        logger.info("All lockdown components stopped")

def main():
    """Main entry point for the lockdown system"""
    # Check if running as root for some elevated privilege components
    if os.geteuid() != 0:
        print("Note: Some components may not function fully without root privileges.")
        print("Consider running with sudo for full functionality.")
    
    # Create and start the master control
    master_control = LockdownMasterControl()
    
    # Set up signal handling for clean termination
    def handle_signal(signum, frame):
        logger.info(f"Received signal {signum}, shutting down")
        master_control.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)
    
    try:
        # Get master password from command line if provided
        master_password = None
        if len(sys.argv) > 1:
            master_password = sys.argv[1]
            
        # Start the master control
        master_control.start(master_password)
        
        # Keep the main thread alive and provide a basic CLI
        print("\n=== Lockdown Master Control ===")
        print("The lockdown system is active.")
        print("Type 'status' to check component status")
        print("Type 'unlock <password>' to unlock the system")
        print("Type 'exit' to stop the lockdown system")
        
        while True:
            try:
                command = input("\nlockdown> ").strip()
                
                if not command:
                    continue
                    
                if command == "exit" or command == "quit":
                    print("Shutting down lockdown system...")
                    master_control.stop()
                    break
                
                elif command == "status":
                    print("\nComponent Status:")
                    for name, status in master_control.component_status.items():
                        print(f"- {name}: {status}")
                
                elif command.startswith("unlock "):
                    password = command.split(" ", 1)[1]
                    token = master_control.authenticate(password)
                    
                    if token:
                        if master_control.unlock_system(token):
                            print("\n✅ System unlocked successfully")
                            print("Shutting down lockdown system...")
                            break
                        else:
                            print("\n❌ Failed to unlock system")
                    else:
                        if master_control.is_locked_out():
                            print("\n⚠️ Too many failed attempts, system is locked out")
                        else:
                            print("\n❌ Invalid password")
                
                elif command == "help":
                    print("\nAvailable commands:")
                    print("  status         - Show status of all components")
                    print("  unlock <pass>  - Unlock the system with password")
                    print("  exit/quit      - Stop the lockdown system")
                    print("  help           - Show this help message")
                
                else:
                    print(f"Unknown command: {command}")
                    print("Type 'help' for available commands")
                
            except KeyboardInterrupt:
                print("\nUse 'exit' command to stop the lockdown system")
            except EOFError:
                print("\nLockdown system remains active (use 'exit' to stop)")
                break
                
    except Exception as e:
        logger.error(f"Error in main thread: {e}")
        master_control.stop()
        sys.exit(1)

if __name__ == "__main__":
    main()
