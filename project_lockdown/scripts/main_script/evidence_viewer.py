#!/usr/bin/env python3
"""
Evidence Viewer for Project Lockdown

This tool provides secure access to view and manage collected security evidence.

Features:
- View screenshots, webcam images, and logs
- Decrypt encrypted evidence
- Generate incident reports
- Manage evidence retention

Usage: Run with appropriate privileges
"""

import os
import sys
import json
import time
import shutil
import hashlib
import logging
import argparse
import datetime
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

# Configure logging
LOG_DIR = Path.home() / "Library" / "Logs" / "project_lockdown"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "evidence_viewer.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('evidence_viewer')

# Directory for storing evidence
EVIDENCE_DIR = LOG_DIR / "evidence"

# Authentication hash - in a real implementation, this would be stored more securely
DEFAULT_ADMIN_PASSWORD_HASH = "5f4dcc3b5aa765d61d8327deb882cf99"  # "password"

class EvidenceManager:
    def __init__(self):
        self.authenticated = False
        self.password_hash = self._load_password_hash()
        self.evidence_dirs = [
            EVIDENCE_DIR / "screenshots",
            EVIDENCE_DIR / "webcam",
            EVIDENCE_DIR / "logs",
            EVIDENCE_DIR / "network",
            EVIDENCE_DIR / "encrypted",
            EVIDENCE_DIR / "facial_analysis"
        ]
        
        # Create directories if they don't exist
        for directory in self.evidence_dirs:
            directory.mkdir(parents=True, exist_ok=True)

    def _load_password_hash(self) -> str:
        """Load admin password hash or set default"""
        config_path = EVIDENCE_DIR / "security_config.json"
        
        if not config_path.exists():
            # Create default config
            config = {
                "password_hash": DEFAULT_ADMIN_PASSWORD_HASH,
                "last_updated": datetime.datetime.now().isoformat()
            }
            
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)
                
            return DEFAULT_ADMIN_PASSWORD_HASH
        
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
                return config.get("password_hash", DEFAULT_ADMIN_PASSWORD_HASH)
        except Exception as e:
            logger.error(f"Failed to load security config: {e}")
            return DEFAULT_ADMIN_PASSWORD_HASH

    def authenticate(self, password: str) -> bool:
        """Authenticate with the provided password"""
        hashed = hashlib.md5(password.encode()).hexdigest()
        self.authenticated = (hashed == self.password_hash)
        
        if self.authenticated:
            logger.info("Evidence viewer authentication successful")
        else:
            logger.warning("Failed authentication attempt to evidence viewer")
            
        return self.authenticated

    def change_password(self, current_password: str, new_password: str) -> bool:
        """Change the admin password"""
        if not self.authenticate(current_password):
            logger.warning("Password change failed: incorrect current password")
            return False
            
        # Update the password hash
        new_hash = hashlib.md5(new_password.encode()).hexdigest()
        config_path = EVIDENCE_DIR / "security_config.json"
        
        try:
            if config_path.exists():
                with open(config_path, 'r') as f:
                    config = json.load(f)
            else:
                config = {}
                
            config["password_hash"] = new_hash
            config["last_updated"] = datetime.datetime.now().isoformat()
            
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)
                
            self.password_hash = new_hash
            logger.info("Password changed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to change password: {e}")
            return False

    def list_evidence(self, evidence_type: Optional[str] = None, 
                     limit: int = 10, detailed: bool = False) -> List[Dict[str, Any]]:
        """List available evidence"""
        if not self.authenticated:
            logger.warning("Unauthorized attempt to list evidence")
            return []
            
        evidence_list = []
        
        try:
            if evidence_type is None:
                # List all types of evidence
                for directory in self.evidence_dirs:
                    if directory.exists():
                        for file_path in directory.glob("*.*"):
                            if not file_path.is_file():
                                continue
                                
                            evidence_item = {
                                "id": file_path.stem,
                                "type": directory.name,
                                "path": str(file_path),
                                "timestamp": datetime.datetime.fromtimestamp(
                                    file_path.stat().st_mtime
                                ).isoformat()
                            }
                            
                            if detailed:
                                evidence_item["size"] = file_path.stat().st_size
                                evidence_item["extension"] = file_path.suffix
                                
                                # Try to extract more info from JSON logs
                                if file_path.suffix == ".json" and directory.name == "logs":
                                    try:
                                        with open(file_path, 'r') as f:
                                            data = json.load(f)
                                            evidence_item["event_type"] = data.get("event_type", "unknown")
                                            evidence_item["details"] = data.get("details", "")
                                    except Exception:
                                        pass
                            
                            evidence_list.append(evidence_item)
            else:
                # List specific type of evidence
                directory = EVIDENCE_DIR / evidence_type
                
                if directory.exists():
                    for file_path in directory.glob("*.*"):
                        if not file_path.is_file():
                            continue
                            
                        evidence_item = {
                            "id": file_path.stem,
                            "type": directory.name,
                            "path": str(file_path),
                            "timestamp": datetime.datetime.fromtimestamp(
                                file_path.stat().st_mtime
                            ).isoformat()
                        }
                        
                        if detailed:
                            evidence_item["size"] = file_path.stat().st_size
                            evidence_item["extension"] = file_path.suffix
                        
                        evidence_list.append(evidence_item)
            
            # Sort by timestamp, newest first
            evidence_list.sort(key=lambda x: x["timestamp"], reverse=True)
            
            # Apply limit
            if limit > 0:
                evidence_list = evidence_list[:limit]
                
            return evidence_list
            
        except Exception as e:
            logger.error(f"Error listing evidence: {e}")
            return []

    def get_evidence_details(self, evidence_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific evidence item"""
        if not self.authenticated:
            logger.warning("Unauthorized attempt to view evidence details")
            return None
            
        try:
            # Search for the evidence item by ID
            for directory in self.evidence_dirs:
                if not directory.exists():
                    continue
                    
                for file_path in directory.glob(f"{evidence_id}*.*"):
                    if not file_path.is_file():
                        continue
                        
                    details = {
                        "id": file_path.stem,
                        "type": directory.name,
                        "path": str(file_path),
                        "filename": file_path.name,
                        "extension": file_path.suffix,
                        "size": file_path.stat().st_size,
                        "created": datetime.datetime.fromtimestamp(
                            file_path.stat().st_ctime
                        ).isoformat(),
                        "modified": datetime.datetime.fromtimestamp(
                            file_path.stat().st_mtime
                        ).isoformat()
                    }
                    
                    # For logs (JSON or text), add content preview
                    if file_path.suffix in [".json", ".log", ".txt"]:
                        try:
                            with open(file_path, 'r') as f:
                                content = f.read(2000)  # Read up to 2000 chars for preview
                                if len(content) == 2000:
                                    content += "...\n[Content truncated]"
                                details["content_preview"] = content
                                
                            if file_path.suffix == ".json":
                                try:
                                    with open(file_path, 'r') as f:
                                        data = json.load(f)
                                        details["event_type"] = data.get("event_type", "unknown")
                                        details["security_level"] = data.get("security_level", "unknown")
                                        details["event_details"] = data.get("details", "")
                                        
                                        # Include list of related evidence
                                        if "evidence_files" in data:
                                            details["related_evidence"] = data["evidence_files"]
                                except Exception as e:
                                    logger.warning(f"Could not parse JSON: {e}")
                        except Exception as e:
                            logger.warning(f"Could not read file content: {e}")
                    
                    # For images, add preview command (for CLI) or dimensions (for GUI)
                    if file_path.suffix in [".png", ".jpg", ".jpeg"]:
                        details["preview_command"] = f"open {file_path}"
                        
                        # Try to get image dimensions if PIL is available
                        try:
                            import PIL.Image
                            with PIL.Image.open(file_path) as img:
                                details["dimensions"] = f"{img.width}x{img.height}"
                        except ImportError:
                            details["dimensions"] = "unknown (PIL not available)"
                        except Exception as e:
                            details["dimensions"] = f"unknown ({str(e)})"
                    
                    return details
                    
            return None
            
        except Exception as e:
            logger.error(f"Error getting evidence details: {e}")
            return None

    def decrypt_evidence(self, encrypted_path: str, key: str, output_path: Optional[str] = None) -> str:
        """Decrypt encrypted evidence"""
        if not self.authenticated:
            logger.warning("Unauthorized attempt to decrypt evidence")
            return "Not authenticated"
            
        try:
            encrypted_path = Path(encrypted_path)
            
            if not encrypted_path.exists():
                return f"File not found: {encrypted_path}"
                
            if not output_path:
                # Generate output path if not provided
                output_path = EVIDENCE_DIR / "decrypted" / encrypted_path.stem
                
                # Create directory if needed
                output_dir = output_path.parent
                output_dir.mkdir(parents=True, exist_ok=True)
            
            # Check if it's a .enc file (encrypted with OpenSSL)
            if encrypted_path.suffix == ".enc":
                # Use OpenSSL to decrypt
                decrypt_cmd = [
                    "openssl", "enc", "-d", "-aes-256-cbc",
                    "-pbkdf2",
                    "-in", str(encrypted_path),
                    "-out", str(output_path),
                    "-k", key
                ]
                
                process = subprocess.run(
                    decrypt_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                
                if process.returncode != 0:
                    return f"Decryption failed: {process.stderr.decode('utf-8', errors='ignore')}"
                    
                # If it's a tar archive, extract it
                if output_path.suffix == ".tar":
                    extract_dir = output_path.parent / output_path.stem
                    extract_dir.mkdir(exist_ok=True)
                    
                    extract_cmd = [
                        "tar", "-xf", str(output_path),
                        "-C", str(extract_dir)
                    ]
                    
                    extract_process = subprocess.run(
                        extract_cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE
                    )
                    
                    if extract_process.returncode == 0:
                        # Remove the tar file after successful extraction
                        os.unlink(output_path)
                        return f"Evidence successfully decrypted and extracted to: {extract_dir}"
                    else:
                        return f"Evidence decrypted to {output_path}, but extraction failed: {extract_process.stderr.decode('utf-8', errors='ignore')}"
                
                return f"Evidence successfully decrypted to: {output_path}"
            else:
                return f"Unknown encryption format: {encrypted_path.suffix}"
                
        except Exception as e:
            logger.error(f"Error decrypting evidence: {e}")
            return f"Decryption error: {str(e)}"

    def generate_report(self, evidence_id: str, output_format: str = "text") -> Tuple[bool, str]:
        """Generate a comprehensive report for a security incident"""
        if not self.authenticated:
            logger.warning("Unauthorized attempt to generate report")
            return False, "Not authenticated"
            
        try:
            # Find all related evidence files for this incident
            related_files = []
            
            # Look for the primary log file first
            log_dir = EVIDENCE_DIR / "logs"
            log_file = None
            
            if log_dir.exists():
                for file_path in log_dir.glob(f"{evidence_id}*.json"):
                    log_file = file_path
                    related_files.append({
                        "type": "log",
                        "path": str(file_path)
                    })
                    break
            
            if not log_file:
                return False, f"Could not find log file for evidence ID: {evidence_id}"
                
            # Load the log data
            with open(log_file, 'r') as f:
                log_data = json.load(f)
            
            # Find related evidence mentioned in the log
            if "evidence_files" in log_data:
                for evidence_type, file_path in log_data["evidence_files"].items():
                    related_files.append({
                        "type": evidence_type,
                        "path": file_path
                    })
            
            # Also search for files with the same ID in other directories
            for directory in self.evidence_dirs:
                if not directory.exists() or directory.name == "logs":
                    continue
                    
                for file_path in directory.glob(f"{evidence_id}*.*"):
                    if not file_path.is_file():
                        continue
                        
                    related_files.append({
                        "type": directory.name,
                        "path": str(file_path)
                    })
            
            # Generate the report
            report_dir = EVIDENCE_DIR / "reports"
            report_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
            
            if output_format == "text":
                report_path = report_dir / f"report_{evidence_id}_{timestamp}.txt"
                
                with open(report_path, 'w') as f:
                    f.write(f"SECURITY INCIDENT REPORT\n")
                    f.write(f"=======================\n\n")
                    f.write(f"Report generated: {datetime.datetime.now().isoformat()}\n")
                    f.write(f"Evidence ID: {evidence_id}\n\n")
                    
                    f.write("INCIDENT DETAILS\n")
                    f.write("----------------\n")
                    f.write(f"Event Type: {log_data.get('event_type', 'Unknown')}\n")
                    f.write(f"Security Level: {log_data.get('security_level', 'Unknown')}\n")
                    f.write(f"Timestamp: {log_data.get('timestamp', 'Unknown')}\n")
                    f.write(f"Details: {log_data.get('details', 'No details available')}\n\n")
                    
                    f.write("SYSTEM INFORMATION\n")
                    f.write("-----------------\n")
                    f.write(f"User: {log_data.get('user', 'Unknown')}\n")
                    f.write(f"Hostname: {log_data.get('hostname', 'Unknown')}\n")
                    f.write(f"Uptime: {log_data.get('uptime', 'Unknown')}\n\n")
                    
                    if "authentication" in log_data:
                        f.write("AUTHENTICATION STATUS\n")
                        f.write("--------------------\n")
                        auth = log_data["authentication"]
                        f.write(f"Auth Attempts: {auth.get('attempts', 'Unknown')}\n")
                        f.write(f"Last Auth Time: {auth.get('last_auth_time', 'Unknown')}\n")
                        f.write(f"Lockout Status: {'LOCKED' if auth.get('lockout_status', False) else 'Not Locked'}\n\n")
                    
                    f.write("COLLECTED EVIDENCE\n")
                    f.write("-----------------\n")
                    for item in related_files:
                        f.write(f"- {item['type']}: {item['path']}\n")
                    f.write("\n")
                    
                    if "network_connections" in log_data:
                        f.write("NETWORK ACTIVITY\n")
                        f.write("---------------\n")
                        f.write(f"{log_data['network_connections']}\n\n")
                    
                    if "active_processes" in log_data:
                        f.write("ACTIVE PROCESSES\n")
                        f.write("---------------\n")
                        f.write(f"{log_data['active_processes']}\n\n")
                    
                    f.write("RECOMMENDATIONS\n")
                    f.write("--------------\n")
                    if log_data.get("security_level") in ["high", "critical"]:
                        f.write("1. Review webcam evidence to identify potential intruders\n")
                        f.write("2. Check all system logs for additional unauthorized access\n")
                        f.write("3. Consider changing authentication credentials\n")
                        f.write("4. Review network connections for suspicious activity\n")
                    else:
                        f.write("1. Monitor for similar events\n")
                        f.write("2. Review security settings if events continue\n")
                
                return True, str(report_path)
                
            elif output_format == "json":
                report_path = report_dir / f"report_{evidence_id}_{timestamp}.json"
                
                report_data = {
                    "report_id": f"report_{evidence_id}_{timestamp}",
                    "generated_at": datetime.datetime.now().isoformat(),
                    "evidence_id": evidence_id,
                    "incident": {
                        "event_type": log_data.get("event_type", "Unknown"),
                        "security_level": log_data.get("security_level", "Unknown"),
                        "timestamp": log_data.get("timestamp", "Unknown"),
                        "details": log_data.get("details", "No details available")
                    },
                    "system": {
                        "user": log_data.get("user", "Unknown"),
                        "hostname": log_data.get("hostname", "Unknown"),
                        "uptime": log_data.get("uptime", "Unknown")
                    },
                    "evidence": related_files,
                    "raw_data": log_data
                }
                
                with open(report_path, 'w') as f:
                    json.dump(report_data, f, indent=2)
                
                return True, str(report_path)
                
            else:
                return False, f"Unsupported report format: {output_format}"
        
        except Exception as e:
            logger.error(f"Error generating report: {e}")
            return False, f"Failed to generate report: {str(e)}"

    def delete_evidence(self, evidence_id: str, confirm: bool = False) -> bool:
        """Delete evidence files"""
        if not self.authenticated:
            logger.warning("Unauthorized attempt to delete evidence")
            return False
            
        if not confirm:
            logger.warning("Evidence deletion requires confirmation")
            return False
            
        try:
            files_deleted = 0
            
            for directory in self.evidence_dirs:
                if not directory.exists():
                    continue
                    
                for file_path in directory.glob(f"{evidence_id}*.*"):
                    if not file_path.is_file():
                        continue
                        
                    try:
                        logger.info(f"Deleting evidence file: {file_path}")
                        os.unlink(file_path)
                        files_deleted += 1
                    except Exception as e:
                        logger.error(f"Failed to delete {file_path}: {e}")
            
            if files_deleted > 0:
                logger.info(f"Deleted {files_deleted} evidence files with ID: {evidence_id}")
                return True
            else:
                logger.warning(f"No evidence files found with ID: {evidence_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error deleting evidence: {e}")
            return False


def print_usage():
    print("Lockdown Evidence Viewer")
    print("======================")
    print()
    print("Usage:")
    print("  python evidence_viewer.py [command] [options]")
    print()
    print("Commands:")
    print("  auth <password>              - Authenticate (required before other commands)")
    print("  list [--type TYPE] [--limit N] [--detailed]")
    print("                               - List available evidence")
    print("  view <evidence_id>           - View detailed information about evidence")
    print("  decrypt <path> <key>         - Decrypt encrypted evidence")
    print("  report <evidence_id> [--format FORMAT]")
    print("                               - Generate a report for an incident")
    print("  delete <evidence_id> --confirm")
    print("                               - Delete evidence files")
    print("  change-password <current> <new>")
    print("                               - Change the admin password")
    print()
    print("Examples:")
    print("  python evidence_viewer.py auth mypassword")
    print("  python evidence_viewer.py list --type webcam --limit 5")
    print("  python evidence_viewer.py view 20250522_143015_authentication_failure")
    print("  python evidence_viewer.py report 20250522_143015 --format json")


def main():
    manager = EvidenceManager()
    
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "auth" and len(sys.argv) >= 3:
        password = sys.argv[2]
        if manager.authenticate(password):
            print("Authentication successful")
        else:
            print("Authentication failed")
            sys.exit(1)
    
    elif command == "list":
        if not manager.authenticated:
            print("Not authenticated. Use 'auth <password>' first.")
            sys.exit(1)
            
        import argparse
        parser = argparse.ArgumentParser(description="List evidence")
        parser.add_argument("--type", help="Type of evidence to list")
        parser.add_argument("--limit", type=int, default=10, help="Maximum number of items to show")
        parser.add_argument("--detailed", action="store_true", help="Show detailed information")
        
        # Parse only the arguments that follow the 'list' command
        args = parser.parse_args(sys.argv[2:])
        
        evidence = manager.list_evidence(args.type, args.limit, args.detailed)
        
        if not evidence:
            print("No evidence found")
            return
            
        print(f"Found {len(evidence)} evidence items:")
        for item in evidence:
            timestamp = item["timestamp"].split("T")[0]  # Just show the date part
            print(f"- {timestamp} {item['type']}: {item['id']}")
            
            if args.detailed:
                print(f"  Path: {item['path']}")
                print(f"  Size: {item['size']} bytes")
                if "event_type" in item:
                    print(f"  Event: {item['event_type']}")
                print()
                
    elif command == "view" and len(sys.argv) >= 3:
        if not manager.authenticated:
            print("Not authenticated. Use 'auth <password>' first.")
            sys.exit(1)
            
        evidence_id = sys.argv[2]
        details = manager.get_evidence_details(evidence_id)
        
        if not details:
            print(f"Evidence not found: {evidence_id}")
            sys.exit(1)
            
        print(f"Evidence Details: {details['id']}")
        print("=" * (16 + len(details['id'])))
        print(f"Type: {details['type']}")
        print(f"Path: {details['path']}")
        print(f"Size: {details['size']} bytes")
        print(f"Created: {details['created']}")
        print(f"Modified: {details['modified']}")
        
        if "dimensions" in details:
            print(f"Dimensions: {details['dimensions']}")
            
        if "event_type" in details:
            print(f"\nEvent Type: {details['event_type']}")
            print(f"Security Level: {details['security_level']}")
            print(f"Details: {details['event_details']}")
            
        if "related_evidence" in details:
            print("\nRelated Evidence:")
            for evidence_type, path in details["related_evidence"].items():
                print(f"- {evidence_type}: {path}")
                
        if "content_preview" in details:
            print("\nContent Preview:")
            print("-" * 40)
            print(details["content_preview"])
            print("-" * 40)
            
        if "preview_command" in details:
            print(f"\nTo view image: {details['preview_command']}")
            
    elif command == "decrypt" and len(sys.argv) >= 4:
        if not manager.authenticated:
            print("Not authenticated. Use 'auth <password>' first.")
            sys.exit(1)
            
        encrypted_path = sys.argv[2]
        key = sys.argv[3]
        
        output_path = None
        if len(sys.argv) >= 5:
            output_path = sys.argv[4]
            
        result = manager.decrypt_evidence(encrypted_path, key, output_path)
        print(result)
        
    elif command == "report" and len(sys.argv) >= 3:
        if not manager.authenticated:
            print("Not authenticated. Use 'auth <password>' first.")
            sys.exit(1)
            
        evidence_id = sys.argv[2]
        
        output_format = "text"
        if len(sys.argv) >= 5 and sys.argv[3] == "--format":
            output_format = sys.argv[4]
            
        success, result = manager.generate_report(evidence_id, output_format)
        
        if success:
            print(f"Report generated: {result}")
        else:
            print(f"Failed to generate report: {result}")
            sys.exit(1)
            
    elif command == "delete" and len(sys.argv) >= 3:
        if not manager.authenticated:
            print("Not authenticated. Use 'auth <password>' first.")
            sys.exit(1)
            
        evidence_id = sys.argv[2]
        
        confirm = False
        if "--confirm" in sys.argv:
            confirm = True
            
        if not confirm:
            print("WARNING: This will permanently delete evidence files.")
            print("To confirm, add the --confirm flag:")
            print(f"  python evidence_viewer.py delete {evidence_id} --confirm")
            sys.exit(1)
            
        success = manager.delete_evidence(evidence_id, confirm=True)
        
        if success:
            print(f"Successfully deleted evidence: {evidence_id}")
        else:
            print(f"Failed to delete evidence: {evidence_id}")
            sys.exit(1)
            
    elif command == "change-password" and len(sys.argv) >= 4:
        current_password = sys.argv[2]
        new_password = sys.argv[3]
        
        success = manager.change_password(current_password, new_password)
        
        if success:
            print("Password changed successfully")
        else:
            print("Failed to change password")
            sys.exit(1)
            
    else:
        print_usage()
        sys.exit(1)


if __name__ == "__main__":
    main()
