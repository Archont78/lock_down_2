# Advanced Evidence Collection System for macOS Lockdown

This enhanced security system provides comprehensive evidence collection and monitoring capabilities for your macOS lockdown system.

## Features

### 📸 Comprehensive Evidence Collection
- **Screenshots**: Captures full-screen images during security events
- **Webcam Photos**: Takes pictures of potential intruders using the built-in camera
- **System Logs**: Records detailed system state information
- **Network Activity**: Captures network connections during security incidents

### 🔒 Advanced Security Features
- **Evidence Encryption**: Protects collected evidence from tampering
- **Facial Recognition**: Optional intruder identification (requires setup)
- **Real-time Alerts**: Immediate on-screen notifications
- **Remote Notifications**: Optional email/SMS alerts for critical events

## Setup Guide

### 1. Basic Setup
The setup script has already:
- Created necessary directory structures
- Configured webcam capture using imagesnap
- Set up evidence encryption
- Created configuration templates

### 2. Enabling Facial Recognition

To enable facial recognition:
```bash
# Create a Python virtual environment
python3 -m venv ~/Library/Logs/project_lockdown/venv

# Activate the virtual environment
source ~/Library/Logs/project_lockdown/venv/bin/activate

# Install required libraries
pip install face_recognition opencv-python

# Add authorized users
cd ~/Library/Logs/project_lockdown/scripts_2
./facial_recognition_helper.py enroll /path/to/face_image.jpg username "Full Name"
```

### 3. Configuring Remote Notifications

Edit the notification configuration file:
```bash
nano ~/Library/Logs/project_lockdown/notifications/notification_config.json
```

#### Email Configuration
```json
"email": {
  "enabled": true,
  "smtp_server": "smtp.gmail.com",
  "smtp_port": 587,
  "username": "your.email@gmail.com",
  "password": "your-app-password",
  "recipients": ["recipient@example.com"],
  "send_evidence": true,
  "security_level_threshold": "high"
}
```

#### SMS Configuration (via Twilio)
```json
"sms": {
  "enabled": true,
  "service": "twilio",
  "account_sid": "your-account-sid",
  "auth_token": "your-auth-token",
  "from_number": "+1XXXXXXXXXX",
  "to_numbers": ["+1XXXXXXXXXX"],
  "security_level_threshold": "critical"
}
```

## Using the System

### Viewing Evidence

Use the evidence viewer tool:
```bash
cd ~/Library/Logs/project_lockdown/scripts_2
./evidence_viewer.py auth password
./evidence_viewer.py list
./evidence_viewer.py view [evidence_id]
./evidence_viewer.py report [evidence_id]
```

### Testing the System

1. Test webcam capture:
```bash
cd ~/Library/Logs/project_lockdown/scripts/
./capture_webcam.sh ~/test_capture.jpg
```

2. Test facial recognition (if set up):
```bash
cd ~/Library/Logs/project_lockdown/scripts_2
./facial_recognition_helper.py verify /path/to/test_image.jpg
```

## Security Levels

The system categorizes security events into four levels:
- **Low**: Minor events like unusual process launches
- **Medium**: Potential security concerns, like configuration changes
- **High**: Active bypass attempts like unauthorized logins
- **Critical**: Confirmed security breaches with detected unauthorized users

## Recommended Security Practices

1. **Regular Monitoring**: Check evidence logs weekly
2. **Update Authorized Users**: Keep facial recognition data up to date
3. **Change Password**: Regularly update the security system password
4. **Test System**: Periodically test evidence collection features
5. **Backup Evidence**: Export and securely store critical security evidence

## Troubleshooting

### Webcam Not Working
- Check camera permissions in System Settings > Privacy & Security > Camera
- Test using: `imagesnap ~/test.jpg`

### Facial Recognition Issues
- Ensure face_recognition library is installed
- Use well-lit, clear photos for enrollment
- Reduce the "tolerance" value in the configuration for stricter matching

### Evidence Encryption Problems
- Check openssl installation: `which openssl`
- Create a secure key backup

### System Not Detecting Events
- Check log files: `tail -f ~/Library/Logs/project_lockdown/system_hooks.log`
- Verify the system_hooks process is running: `ps aux | grep system_hooks`

## Support

For additional help, please refer to the individual README files in:
- `~/Library/Logs/project_lockdown/facial_recognition/`
- `~/Library/Logs/project_lockdown/notifications/`
- `~/Library/Logs/project_lockdown/evidence/`
