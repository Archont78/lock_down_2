#!/bin/bash
# Test Script for Evidence Collection System
#
# This script demonstrates the advanced evidence collection capabilities 
# by simulating different types of security events

# Color definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Base directories
PROJECT_DIR="$HOME/Library/Logs/project_lockdown"
SCRIPTS_DIR="$PROJECT_DIR/scripts_2"
EVIDENCE_DIR="$PROJECT_DIR/evidence"

# Ensure we have the required tools
if ! command -v imagesnap &> /dev/null; then
    echo -e "${RED}Error: imagesnap is not installed${NC}"
    echo "Please run setup_evidence_collector.sh first"
    exit 1
fi

echo -e "${BLUE}${BOLD}"
echo "╔═════════════════════════════════════════════════╗"
echo "║          EVIDENCE COLLECTION TEST               ║"
echo "╚═════════════════════════════════════════════════╝"
echo -e "${NC}"

# Function to simulate a security event
simulate_security_event() {
    local event_type="$1"
    local security_level="$2"
    local details="$3"
    
    echo -e "${YELLOW}Simulating security event: $event_type (Level: $security_level)${NC}"
    echo "Details: $details"
    
    # Create timestamp
    local timestamp=$(date +"%Y%m%d-%H%M%S")
    local evidence_id="${timestamp}_${event_type}_${security_level}"
    local event_dir="$EVIDENCE_DIR/$evidence_id"
    
    # Create directory structure
    mkdir -p "$event_dir"
    
    # 1. Capture screenshot
    echo -e "${GREEN}Capturing screenshot...${NC}"
    screencapture -x "$event_dir/screenshot.png"
    
    # Copy to screenshots directory
    cp "$event_dir/screenshot.png" "$EVIDENCE_DIR/screenshots/$evidence_id.png"
    
    # 2. Capture webcam photo
    echo -e "${GREEN}Capturing webcam photo...${NC}"
    "$PROJECT_DIR/scripts/capture_webcam.sh" "$event_dir/webcam.jpg"
    
    # Copy to webcam directory if it exists
    if [ -f "$event_dir/webcam.jpg" ]; then
        cp "$event_dir/webcam.jpg" "$EVIDENCE_DIR/webcam/$evidence_id.jpg"
    fi
    
    # 3. Collect system information
    echo -e "${GREEN}Collecting system information...${NC}"
    
    # Create JSON system info
    cat > "$event_dir/system_info.json" <<EOF
{
  "timestamp": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "event_type": "$event_type",
  "security_level": "$security_level",
  "details": "$details",
  "user": "$(whoami)",
  "hostname": "$(hostname)",
  "uptime": "$(uptime)",
  "active_processes": "$(ps -ef | head -5 | base64)",
  "network_connections": "$(netstat -an | grep ESTAB | head -5 | base64)",
  "system_load": "$(vm_stat | head -5 | base64)",
  "evidence_files": {
    "screenshot": "$event_dir/screenshot.png",
    "webcam": "$event_dir/webcam.jpg"
  }
}
EOF
    
    # Copy to logs directory
    cp "$event_dir/system_info.json" "$EVIDENCE_DIR/logs/$evidence_id.json"
    
    # 4. Create human-readable log
    cat > "$event_dir/event_summary.log" <<EOF
SECURITY EVENT: $event_type (Level: ${security_level^^})
Timestamp: $(date -u +"%Y-%m-%d %H:%M:%S")
Details: $details

SYSTEM INFORMATION
=================
User: $(whoami)
Hostname: $(hostname)
Uptime: $(uptime)

EVIDENCE FILES
=============
  - screenshot: $event_dir/screenshot.png
  - webcam: $event_dir/webcam.jpg
EOF
    
    # Copy to logs directory
    cp "$event_dir/event_summary.log" "$EVIDENCE_DIR/logs/$evidence_id.log"
    
    # 5. Display notification
    osascript -e "display notification \"$details\" with title \"SECURITY ALERT: $event_type\" subtitle \"Evidence Collection Test\" sound name \"Basso\""
    
    echo -e "${GREEN}Event simulated successfully. Evidence ID: $evidence_id${NC}"
    echo "Evidence stored in: $event_dir"
    echo ""
    
    # Return the evidence ID for later use
    echo "$evidence_id"
}

# Function to create a test report
create_test_report() {
    local evidence_id="$1"
    
    echo -e "${YELLOW}Creating test report for evidence ID: $evidence_id${NC}"
    
    if [ ! -f "$EVIDENCE_DIR/logs/$evidence_id.json" ]; then
        echo -e "${RED}Error: Evidence file not found${NC}"
        return 1
    fi
    
    # Generate report filename
    local report_dir="$EVIDENCE_DIR/reports"
    mkdir -p "$report_dir"
    local report_path="$report_dir/report_${evidence_id}.txt"
    
    cat > "$report_path" <<EOF
SECURITY INCIDENT REPORT
=======================

Report generated: $(date -u +"%Y-%m-%d %H:%M:%S")
Evidence ID: $evidence_id

INCIDENT DETAILS
----------------
$(grep -A 3 '"event_type"' "$EVIDENCE_DIR/logs/$evidence_id.json" | sed 's/"//g')

SYSTEM INFORMATION
-----------------
User: $(whoami)
Hostname: $(hostname)
Uptime: $(uptime)

COLLECTED EVIDENCE
-----------------
- Screenshot: $EVIDENCE_DIR/screenshots/$evidence_id.png
- Webcam: $EVIDENCE_DIR/webcam/$evidence_id.jpg
- Logs: $EVIDENCE_DIR/logs/$evidence_id.json

RECOMMENDATIONS
--------------
1. Review webcam evidence to identify potential intruders
2. Check all system logs for additional unauthorized access
3. Consider changing authentication credentials
EOF
    
    echo -e "${GREEN}Report created: $report_path${NC}"
}

# Ask user which test to run
echo -e "Please select a test to run:"
echo -e "  ${BOLD}1${NC}. Simulate authentication failure (Medium level)"
echo -e "  ${BOLD}2${NC}. Simulate bypass attempt (High level)"
echo -e "  ${BOLD}3${NC}. Simulate critical security breach (Critical level)"
echo -e "  ${BOLD}4${NC}. Run all tests"
echo -e "  ${BOLD}5${NC}. Exit"
echo -e ""
read -p "Enter your choice (1-5): " choice

case "$choice" in
    1)
        event_id=$(simulate_security_event "authentication_failure" "medium" "Multiple failed password attempts detected from user $(whoami)")
        ;;
    2)
        event_id=$(simulate_security_event "bypass_attempt" "high" "Suspicious process launch detected: Terminal with escalated privileges")
        ;;
    3)
        event_id=$(simulate_security_event "security_breach" "critical" "Unauthorized user detected with access to lockdown system files")
        create_test_report "$event_id"
        ;;
    4)
        echo -e "${YELLOW}Running all tests with 5 second intervals...${NC}"
        event1=$(simulate_security_event "authentication_failure" "medium" "Multiple failed password attempts detected from user $(whoami)")
        sleep 5
        event2=$(simulate_security_event "bypass_attempt" "high" "Suspicious process launch detected: Terminal with escalated privileges")
        sleep 5
        event3=$(simulate_security_event "security_breach" "critical" "Unauthorized user detected with access to lockdown system files")
        create_test_report "$event3"
        
        echo -e "${BLUE}${BOLD}All tests completed successfully!${NC}"
        echo -e "Evidence IDs:"
        echo -e "  - $event1"
        echo -e "  - $event2"
        echo -e "  - $event3"
        ;;
    5)
        echo -e "${YELLOW}Exiting...${NC}"
        exit 0
        ;;
    *)
        echo -e "${RED}Invalid choice. Exiting.${NC}"
        exit 1
        ;;
esac

echo -e "${GREEN}${BOLD}"
echo "╔═════════════════════════════════════════════════╗"
echo "║          TEST COMPLETED SUCCESSFULLY            ║"
echo "╚═════════════════════════════════════════════════╝"
echo -e "${NC}"

echo -e "To view collected evidence, use the evidence viewer:"
echo -e "${BLUE}cd $SCRIPTS_DIR${NC}"
echo -e "${BLUE}./evidence_viewer.py auth password${NC}"
echo -e "${BLUE}./evidence_viewer.py list${NC}"
echo -e "${BLUE}./evidence_viewer.py view $event_id${NC}"
