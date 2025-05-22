#!/usr/bin/env python3
"""
Network Security Monitor for Project Lockdown

This script monitors network connections and prevents attempts to bypass the lockdown
through network-based solutions (SSH, remote desktop, etc.).

Features:
- Blocks all outgoing connections except for specified whitelisted ones
- Prevents SSH connections
- Monitors unusual network activity during lockdown
- Logs all connection attempts

Usage: Run as root for full functionality
"""
import os
import sys
import time
import signal
import socket
import subprocess
import logging
import threading
from pathlib import Path
from datetime import datetime

# Configure logging
LOG_DIR = Path.home() / "Library" / "Logs" / "project_lockdown"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "network_monitor.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('network_monitor')

class NetworkMonitor:
    def __init__(self):
        self.stop_flag = threading.Event()
        self.firewall_enabled = False
        self.original_hostname = socket.gethostname()
        
    def enable_firewall(self):
        """Enable and configure macOS firewall"""
        try:
            # Turn on the firewall
            subprocess.run(['sudo', 'defaults', 'write', '/Library/Preferences/com.apple.alf', 'globalstate', '-int', '1'], check=True)
            
            # Block all incoming connections
            subprocess.run(['sudo', 'defaults', 'write', '/Library/Preferences/com.apple.alf', 'allowsignedenabled', '-int', '1'], check=True)
            
            # Disable stealth mode to make the computer visible on the network
            subprocess.run(['sudo', 'defaults', 'write', '/Library/Preferences/com.apple.alf', 'stealthenabled', '-int', '0'], check=True)
            
            # Load the changes
            subprocess.run(['sudo', 'launchctl', 'unload', '/System/Library/LaunchDaemons/com.apple.alf.agent.plist'], check=False)
            subprocess.run(['sudo', 'launchctl', 'load', '/System/Library/LaunchDaemons/com.apple.alf.agent.plist'], check=True)
            
            logger.info("Firewall enabled and configured")
            self.firewall_enabled = True
            return True
        except Exception as e:
            logger.error(f"Failed to enable firewall: {e}")
            return False
    
    def block_outgoing_connections(self):
        """Block all outgoing connections except whitelisted ones"""
        try:
            # Create temporary pf.conf file
            pf_rules = """
            # Block all outgoing connections by default
            block out all
            
            # Allow DNS resolution to continue working
            pass out proto udp to any port 53 keep state
            
            # Allow local network traffic
            pass out to 127.0.0.0/8 keep state
            pass out to 192.168.0.0/16 keep state
            pass out to 10.0.0.0/8 keep state
            """
            
            # Write rules to a temporary file
            pf_conf_path = "/tmp/lockdown_pf.conf"
            with open(pf_conf_path, "w") as f:
                f.write(pf_rules)
                
            # Load the rules
            subprocess.run(['sudo', 'pfctl', '-f', pf_conf_path], check=True)
            subprocess.run(['sudo', 'pfctl', '-e'], check=True)
            
            logger.info("Outgoing connections blocked")
            return True
        except Exception as e:
            logger.error(f"Failed to block outgoing connections: {e}")
            return False
    
    def disable_ssh(self):
        """Disable SSH service"""
        try:
            subprocess.run(['sudo', 'launchctl', 'unload', '-w', '/System/Library/LaunchDaemons/ssh.plist'], check=False)
            logger.info("SSH service disabled")
            return True
        except Exception as e:
            logger.error(f"Failed to disable SSH: {e}")
            return False
    
    def change_hostname(self):
        """Change the computer's hostname to make it harder to identify remotely"""
        try:
            new_hostname = f"unknown-device-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            subprocess.run(['sudo', 'scutil', '--set', 'ComputerName', new_hostname], check=True)
            subprocess.run(['sudo', 'scutil', '--set', 'LocalHostName', new_hostname], check=True)
            subprocess.run(['sudo', 'scutil', '--set', 'HostName', new_hostname], check=True)
            
            logger.info(f"Changed hostname from {self.original_hostname} to {new_hostname}")
            return True
        except Exception as e:
            logger.error(f"Failed to change hostname: {e}")
            return False
    
    def monitor_network_connections(self):
        """Monitor network connections for suspicious activity"""
        while not self.stop_flag.is_set():
            try:
                # Get all active network connections
                output = subprocess.check_output(['netstat', '-anp', 'tcp'], text=True)
                
                # Check for SSH connections (port 22)
                if " 22 " in output:
                    logger.warning("Detected possible SSH connection attempt")
                    # Try to kill SSH processes
                    subprocess.run(['sudo', 'killall', 'sshd'], check=False)
                
                # Check for other common remote access ports
                suspicious_ports = ["3389", "5900", "5800", "3283"]
                for port in suspicious_ports:
                    if f" {port} " in output:
                        logger.warning(f"Detected possible remote access attempt on port {port}")
                        
            except Exception as e:
                logger.error(f"Error monitoring network connections: {e}")
            
            time.sleep(5)
    
    def restore_network_settings(self):
        """Restore original network settings"""
        try:
            # Disable packet filter if it was enabled
            subprocess.run(['sudo', 'pfctl', '-d'], check=False)
            
            # Restore original hostname
            if self.original_hostname:
                subprocess.run(['sudo', 'scutil', '--set', 'ComputerName', self.original_hostname], check=False)
                subprocess.run(['sudo', 'scutil', '--set', 'LocalHostName', self.original_hostname], check=False)
                subprocess.run(['sudo', 'scutil', '--set', 'HostName', self.original_hostname], check=False)
            
            # Re-enable SSH if desired
            # subprocess.run(['sudo', 'launchctl', 'load', '-w', '/System/Library/LaunchDaemons/ssh.plist'], check=False)
            
            logger.info("Network settings restored")
            return True
        except Exception as e:
            logger.error(f"Failed to restore network settings: {e}")
            return False
    
    def start(self):
        """Start the network monitor"""
        logger.info("Starting network security monitor")
        
        # Configure network restrictions
        self.enable_firewall()
        self.block_outgoing_connections()
        self.disable_ssh()
        self.change_hostname()
        
        # Start monitoring thread
        monitor_thread = threading.Thread(target=self.monitor_network_connections)
        monitor_thread.daemon = True
        monitor_thread.start()
        
        logger.info("Network security monitor started")
    
    def stop(self):
        """Stop the network monitor and restore settings"""
        logger.info("Stopping network security monitor")
        self.stop_flag.set()
        self.restore_network_settings()
        logger.info("Network security monitor stopped")

if __name__ == "__main__":
    # Check if running as root
    if os.geteuid() != 0:
        print("This script requires root privileges to function properly.")
        print("Please run with sudo:")
        print(f"sudo python3 {__file__}")
        sys.exit(1)
        
    # Create and start the network monitor
    net_monitor = NetworkMonitor()
    
    # Set up signal handling for clean termination
    def handle_signal(signum, frame):
        logger.info(f"Received signal {signum}, shutting down")
        net_monitor.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)
    
    try:
        net_monitor.start()
        # Keep the main thread alive
        while True:
            time.sleep(60)
    except Exception as e:
        logger.error(f"Error in main thread: {e}")
        net_monitor.stop()
        sys.exit(1)
