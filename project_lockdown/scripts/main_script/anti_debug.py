#!/usr/bin/env python3
"""
Anti-Debug Protection for Project Lockdown

This script implements anti-debugging techniques to prevent attackers from 
analyzing or debugging the lockdown scripts. It detects and prevents common 
bypass techniques used by advanced users.

Features:
- Detects debuggers and developer tools
- Monitors for process attachments
- Self-checking code integrity
- Prevents code injection attempts
- Misdirection and decoy behavior

Usage: Include in the lockdown process chain
"""
import os
import sys
import time
import random
import signal
import hashlib
import logging
import platform
import threading
import subprocess
import traceback
from pathlib import Path
from typing import Dict, List, Set

# Configure logging
LOG_DIR = Path.home() / "Library" / "Logs" / "project_lockdown"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "anti_debug.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('anti_debug')

# Script directories
DIR = Path(__file__).parent.resolve()
SCRIPTS_DIR = DIR
PROJECT_ROOT = LOG_DIR.parent

class AntiDebugProtection:
    def __init__(self):
        self.stop_flag = threading.Event()
        self.protected_files = {
            "keyboard_interceptor.py": "",
            "input_blocker2.py": "",
            "password_checker.py": "",
            "lockdown2.py": "",
            "system_hooks.py": "",
            "network_monitor.py": "",
            "laugh_skull.py": ""
        }
        self.file_hashes = {}
        self.known_debuggers = [
            "lldb", "gdb", "ida", "hopper", "x64dbg", "ollydbg", "radare2", 
            "ghidra", "debugserver", "dtrace", "dtruss", "strace", "frida"
        ]
        # Initialize with initial file hashes
        self.calculate_file_hashes()
    
    def calculate_file_hashes(self) -> None:
        """Calculate SHA-256 hashes for all protected files"""
        for filename in self.protected_files.keys():
            file_path = SCRIPTS_DIR / filename
            if file_path.exists():
                try:
                    with open(file_path, 'rb') as f:
                        file_hash = hashlib.sha256(f.read()).hexdigest()
                        self.file_hashes[filename] = file_hash
                        logger.info(f"Calculated hash for {filename}: {file_hash[:8]}...")
                except Exception as e:
                    logger.error(f"Failed to calculate hash for {filename}: {e}")
    
    def check_file_integrity(self) -> bool:
        """Check if any protected files have been modified"""
        for filename, original_hash in self.file_hashes.items():
            if not original_hash:  # Skip if we don't have an original hash
                continue
                
            file_path = SCRIPTS_DIR / filename
            if not file_path.exists():
                logger.warning(f"Protected file missing: {filename}")
                return False
                
            try:
                with open(file_path, 'rb') as f:
                    current_hash = hashlib.sha256(f.read()).hexdigest()
                    if current_hash != original_hash:
                        logger.warning(f"File integrity violation: {filename}")
                        return False
            except Exception as e:
                logger.error(f"Error checking file {filename}: {e}")
                return False
        
        return True
    
    def detect_debugger(self) -> bool:
        """Check if a debugger is attached to this process"""
        try:
            # On macOS, use sysctl to check for debugger
            if platform.system() == "Darwin":
                output = subprocess.check_output(['sysctl', 'kern.proc.pid.%d' % os.getpid()], text=True)
                if "P_TRACED" in output:
                    logger.warning("Debugger detected through sysctl")
                    return True
            
            # Check for common debugger processes
            ps_output = subprocess.check_output(['ps', 'aux'], text=True).lower()
            for debugger in self.known_debuggers:
                if debugger in ps_output:
                    logger.warning(f"Debugger detected: {debugger}")
                    return True
            
            return False
        except Exception as e:
            logger.error(f"Error in debugger detection: {e}")
            return False
    
    def detect_development_tools(self) -> bool:
        """Check for presence of development tools that could be used to bypass protection"""
        dev_paths = [
            "/Library/Developer",
            "/Applications/Xcode.app",
            "/usr/bin/gcc",
            "/usr/bin/lldb",
            "/usr/bin/dtrace",
            "/usr/bin/nm",
            "/usr/bin/gdb"
        ]
        
        for path in dev_paths:
            if os.path.exists(path):
                logger.warning(f"Development tool detected: {path}")
                return True
        
        return False
    
    def detect_virtualization(self) -> bool:
        """Check if running in a virtual machine or sandbox environment"""
        try:
            # Check for VM-specific files or directories
            vm_indicators = [
                "/Library/Preferences/VMware Fusion",
                "/Library/Application Support/VMware Fusion",
                "/Library/Preferences/Parallels",
                ".VirtualBox"
            ]
            
            for indicator in vm_indicators:
                if os.path.exists(os.path.expanduser(f"~/{indicator}")) or os.path.exists(indicator):
                    logger.warning(f"Virtualization detected: {indicator}")
                    return True
            
            # Check system_profiler for virtualization info
            output = subprocess.check_output(['system_profiler', 'SPHardwareDataType'], text=True)
            vm_keywords = ["VMware", "VirtualBox", "Parallels", "QEMU", "Virtual Machine"]
            for keyword in vm_keywords:
                if keyword in output:
                    logger.warning(f"Virtualization detected through system_profiler: {keyword}")
                    return True
            
            return False
        except Exception as e:
            logger.error(f"Error in virtualization detection: {e}")
            return False
    
    def implement_anti_analysis_measures(self):
        """Implement counter-measures against analysis and debugging"""
        # Create some decoy variables and code paths to confuse debuggers
        decoy_password = ''.join(random.choice('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789') for _ in range(24))
        decoy_counter = random.randint(10000, 99999)
        
        # Add some timing checks to detect step-debugging
        start_time = time.time()
        for _ in range(5):
            # Adding some pointless calculations that would be slow if single-stepping
            for i in range(1000):
                decoy_counter = (decoy_counter * 31337 + 12345) % 1000000
            
            # Anti-pattern to make static analysis harder
            if decoy_counter % 5 == 0:
                decoy_password = hashlib.sha256(decoy_password.encode()).hexdigest()
                
        elapsed_time = time.time() - start_time
        if elapsed_time > 1.0:  # This should be very fast unless being debugged
            logger.warning(f"Timing anomaly detected: {elapsed_time:.2f}s - possible step-debugging")
            return True
            
        return False
    
    def monitor_file_changes(self):
        """Monitor protected files for changes and take action if they're modified"""
        while not self.stop_flag.is_set():
            try:
                if not self.check_file_integrity():
                    logger.critical("File integrity violation detected!")
                    # Take action - could trigger lockdown or alert
                    self.trigger_countermeasures("file_integrity")
                    
                # Also check for debuggers periodically
                if self.detect_debugger():
                    logger.critical("Debugger detected!")
                    self.trigger_countermeasures("debugger")
                
                if self.implement_anti_analysis_measures():
                    logger.critical("Code analysis attempt detected!")
                    self.trigger_countermeasures("analysis")
                
                if self.detect_development_tools():
                    logger.warning("Development tools detected")
                    # No immediate action, just log this
                
            except Exception as e:
                logger.error(f"Error in file monitor: {e}")
                
            time.sleep(random.uniform(5, 15))  # Random interval to make timing attacks harder
    
    def trigger_countermeasures(self, trigger_type):
        """Implement countermeasures when tampering is detected"""
        try:
            # Log the event with stack trace for context
            logger.critical(f"SECURITY BREACH: {trigger_type} - Taking countermeasures")
            logger.critical(f"Stack trace: {traceback.format_stack()}")
            
            # Different responses based on the type of tampering
            if trigger_type == "file_integrity":
                # Files were modified, try to restore from backup or restart services
                self.restore_from_backup()
                
            elif trigger_type == "debugger":
                # Detected a debugger, could insert misleading data or redirect flow
                # For example, make password checker appear to succeed but actually fail
                self.implement_deception()
                
            elif trigger_type == "analysis":
                # Code analysis tools detected, could slow down execution or add delays
                time.sleep(random.uniform(5, 15))  # Add random delays
                self.implement_obfuscation()
        
        except Exception as e:
            logger.error(f"Error in countermeasures: {e}")
    
    def restore_from_backup(self):
        """Attempt to restore files from backup if they exist"""
        backup_dir = PROJECT_ROOT / "backup"
        if not backup_dir.exists():
            logger.error("No backup directory found")
            return False
        
        success = True
        for filename in self.protected_files.keys():
            backup_file = backup_dir / filename
            target_file = SCRIPTS_DIR / filename
            if backup_file.exists():
                try:
                    # Copy backup to original location
                    with open(backup_file, 'rb') as src, open(target_file, 'wb') as dst:
                        dst.write(src.read())
                    logger.info(f"Restored {filename} from backup")
                except Exception as e:
                    logger.error(f"Failed to restore {filename}: {e}")
                    success = False
        
        return success
    
    def implement_deception(self):
        """Implement deceptive behavior to confuse attackers"""
        # Create false success signals
        print("\033[92mAccess granted - Unlocking system\033[0m")
        time.sleep(2)
        
        # But actually trigger more security
        try:
            # Launch distractions
            for _ in range(3):
                subprocess.Popen([
                    'osascript', '-e', 
                    'tell application "Terminal" to do script "echo SECURITY ALERT: Intrusion detected; sleep 1; exit"'
                ])
                time.sleep(0.5)
                
            # Redirect to fake interface that appears to give access but doesn't
            print("\033[93mLoading user profile...\033[0m")
            time.sleep(1)
            print("\033[91mError in user profile - Access restricted\033[0m")
            
        except Exception as e:
            logger.error(f"Deception implementation failed: {e}")
    
    def implement_obfuscation(self):
        """Implement additional obfuscation when under attack"""
        # This would typically modify runtime behavior to confuse analysis
        try:
            global logger  # Modify logger to send false information
            original_info = logger.info
            original_warning = logger.warning
            
            def misleading_info(msg, *args, **kwargs):
                if "password" in str(msg).lower() or "authentication" in str(msg).lower():
                    return  # Suppress logging of sensitive info
                return original_info(msg, *args, **kwargs)
                
            def misleading_warning(msg, *args, **kwargs):
                return original_warning("NOTICE: System performing maintenance", *args, **kwargs)
                
            # Apply our wrappers
            logger.info = misleading_info
            logger.warning = misleading_warning
            
            logger.critical("Applied obfuscation techniques")
        except Exception as e:
            logger.error(f"Obfuscation implementation failed: {e}")
    
    def start(self):
        """Start the anti-debug protection"""
        logger.info("Starting anti-debug protection")
        
        # Start the file monitor thread
        monitor_thread = threading.Thread(target=self.monitor_file_changes)
        monitor_thread.daemon = True
        monitor_thread.start()
        
        logger.info("Anti-debug protection active")
    
    def stop(self):
        """Stop the anti-debug protection"""
        logger.info("Stopping anti-debug protection")
        self.stop_flag.set()
        logger.info("Anti-debug protection stopped")

if __name__ == "__main__":
    # Create and start the anti-debug protection
    protection = AntiDebugProtection()
    
    # Set up signal handling for clean termination
    def handle_signal(signum, frame):
        logger.info(f"Received signal {signum}, shutting down")
        protection.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)
    
    try:
        protection.start()
        # Keep the main thread alive
        while True:
            time.sleep(60)
    except Exception as e:
        logger.error(f"Error in main thread: {e}")
        protection.stop()
        sys.exit(1)
