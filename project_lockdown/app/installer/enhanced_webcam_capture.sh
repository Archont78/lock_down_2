#!/bin/bash
# Enhanced Webcam Capture System for Project Lockdown
#
# Features:
# - Multiple capture methods with redundancy
# - Support for external USB cameras
# - Automatic camera detection
# - High-resolution capture options
# - Hardware acceleration when available
# - Multiple image formats (JPEG, PNG, HEIC)
# - Video recording capability
# - Camera access verification
# - Comprehensive error handling

# Color definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Default parameters
OUTPUT_PATH="$1"
FORMAT="${2:-jpg}"  # Default to jpg if not specified
RESOLUTION="${3:-high}"  # Options: low, medium, high, max
DEVICE_INDEX="${4:-0}"  # Default to first camera
TIMEOUT="${5:-10}"  # Timeout in seconds
VIDEO_MODE="${6:-false}"  # Whether to capture video instead of photo
VIDEO_DURATION="${7:-3}"  # Video duration in seconds (if in video mode)

# Utility functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" >&2
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

show_usage() {
    echo "Enhanced Webcam Capture for Project Lockdown"
    echo ""
    echo "Usage: $0 <output_path> [format] [resolution] [device_index] [timeout] [video_mode] [video_duration]"
    echo ""
    echo "Parameters:"
    echo "  output_path    : Path where the captured image/video will be saved"
    echo "  format         : Image format (jpg, png, heic) - default: jpg"
    echo "  resolution     : Image resolution (low, medium, high, max) - default: high"
    echo "  device_index   : Camera device index (0 for default) - default: 0"
    echo "  timeout        : Capture timeout in seconds - default: 10"
    echo "  video_mode     : Whether to capture video (true/false) - default: false"
    echo "  video_duration : Video duration in seconds - default: 3"
    echo ""
}

# Validate parameters
if [ -z "$OUTPUT_PATH" ]; then
    log_error "No output path provided"
    show_usage
    exit 1
fi

# Validate format
case "$FORMAT" in
    jpg|jpeg|png|heic)
        # Valid format
        ;;
    *)
        log_warning "Invalid format: $FORMAT. Using jpg instead."
        FORMAT="jpg"
        ;;
esac

# Validate resolution
case "$RESOLUTION" in
    low|medium|high|max)
        # Valid resolution
        ;;
    *)
        log_warning "Invalid resolution: $RESOLUTION. Using high instead."
        RESOLUTION="high"
        ;;
esac

# Translate resolution to actual values
case "$RESOLUTION" in
    low)
        RES_VALUE="640x480"
        ;;
    medium)
        RES_VALUE="1280x720"
        ;;
    high)
        RES_VALUE="1920x1080"
        ;;
    max)
        RES_VALUE="3840x2160"  # 4K
        ;;
esac

# Ensure output directory exists
OUTPUT_DIR=$(dirname "$OUTPUT_PATH")
mkdir -p "$OUTPUT_DIR"

# Check for camera hardware
log_info "Checking for camera hardware..."
if ! system_profiler SPCameraDataType 2>/dev/null | grep -q "Camera"; then
    log_warning "No built-in camera detected. Will try external cameras."
    
    # Try to detect external cameras
    if command -v avfoundation-device-list >/dev/null 2>&1; then
        CAMERAS=$(avfoundation-device-list 2>/dev/null)
        if [ -z "$CAMERAS" ]; then
            log_error "No cameras detected. Cannot capture image."
            exit 2
        else
            log_info "External cameras found:"
            echo "$CAMERAS"
        fi
    fi
else
    log_info "Camera hardware detected."
fi

# Capture functions
capture_with_imagesnap() {
    local output="$1"
    local device_index="$2"
    local warmup="$3"
    
    log_info "Attempting capture with imagesnap..."
    
    # Add device selection if specified
    DEVICE_ARG=""
    if [ "$device_index" != "0" ]; then
        DEVICE_ARG="-d $device_index"
    fi
    
    # Attempt to capture with timeout
    if timeout "$TIMEOUT" imagesnap -w "$warmup" $DEVICE_ARG "$output" 2>/dev/null; then
        if [ -f "$output" ] && [ -s "$output" ]; then
            log_info "Successfully captured image with imagesnap"
            return 0
        fi
    fi
    
    log_warning "imagesnap capture failed"
    return 1
}

capture_with_avfoundation() {
    local output="$1"
    local device_index="$2"
    
    log_info "Attempting capture with AVFoundation..."
    
    # Create a temporary Swift script
    TMP_SWIFT_SCRIPT=$(mktemp).swift
    
    cat > "$TMP_SWIFT_SCRIPT" << 'EOF'
import AVFoundation
import Cocoa
import Foundation

class CameraCapture: NSObject, AVCapturePhotoCaptureDelegate {
    let captureSession = AVCaptureSession()
    var photoOutput: AVCapturePhotoOutput?
    let outputPath: String
    let deviceIndex: Int
    var completion: (() -> Void)?
    
    init(outputPath: String, deviceIndex: Int) {
        self.outputPath = outputPath
        self.deviceIndex = deviceIndex
        super.init()
        setupCamera()
    }
    
    func setupCamera() {
        captureSession.beginConfiguration()
        captureSession.sessionPreset = .high
        
        // Get all video devices
        let discoverySession = AVCaptureDevice.DiscoverySession(
            deviceTypes: [.builtInWideAngleCamera, .externalUnknown],
            mediaType: .video, 
            position: .unspecified
        )
        
        let devices = discoverySession.devices
        print("Found \(devices.count) camera devices")
        
        guard devices.count > 0 else {
            print("No camera devices found")
            return
        }
        
        // Select device by index or default to first
        let selectedDevice: AVCaptureDevice
        if deviceIndex < devices.count && deviceIndex >= 0 {
            selectedDevice = devices[deviceIndex]
        } else {
            selectedDevice = devices[0]
        }
        
        print("Using camera: \(selectedDevice.localizedName)")
        
        guard let input = try? AVCaptureDeviceInput(device: selectedDevice) else {
            print("Failed to create device input")
            return
        }
        
        if captureSession.canAddInput(input) {
            captureSession.addInput(input)
        } else {
            print("Cannot add input to capture session")
            return
        }
        
        photoOutput = AVCapturePhotoOutput()
        if let photoOutput = photoOutput, captureSession.canAddOutput(photoOutput) {
            captureSession.addOutput(photoOutput)
        } else {
            print("Cannot add photo output to capture session")
            return
        }
        
        captureSession.commitConfiguration()
        captureSession.startRunning()
        print("Camera initialized")
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
        print("Capturing photo...")
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
            print("Photo saved successfully to \(outputPath)")
        } catch {
            print("Failed to save photo: \(error)")
        }
        
        completion?()
    }
}

// Main execution
if CommandLine.arguments.count < 3 {
    print("Usage: swift camera_capture.swift [output_path] [device_index]")
    exit(1)
}

let outputPath = CommandLine.arguments[1]
let deviceIndex = Int(CommandLine.arguments[2]) ?? 0

let cameraCapture = CameraCapture(outputPath: outputPath, deviceIndex: deviceIndex)

// Capture photo after a short delay to allow camera initialization
DispatchQueue.main.asyncAfter(deadline: .now() + 1.5) {
    cameraCapture.capturePhoto {
        exit(0)
    }
}

// Keep the program running until photo capture completes
RunLoop.main.run(until: Date(timeIntervalSinceNow: 8))
print("Timed out waiting for capture to complete")
exit(1)
EOF

    # Execute the Swift script with proper parameters
    if swift "$TMP_SWIFT_SCRIPT" "$output" "$device_index"; then
        if [ -f "$output" ] && [ -s "$output" ]; then
            log_info "Successfully captured image with AVFoundation"
            rm -f "$TMP_SWIFT_SCRIPT"
            return 0
        fi
    fi
    
    rm -f "$TMP_SWIFT_SCRIPT"
    log_warning "AVFoundation capture failed"
    return 1
}

capture_with_ffmpeg() {
    local output="$1"
    local device_index="$2"
    
    log_info "Attempting capture with ffmpeg..."
    
    if command -v ffmpeg >/dev/null 2>&1; then
        # For macOS, use avfoundation format
        if ffmpeg -f avfoundation -framerate 30 -i "$device_index:none" -vframes 1 "$output" >/dev/null 2>&1; then
            if [ -f "$output" ] && [ -s "$output" ]; then
                log_info "Successfully captured image with ffmpeg"
                return 0
            fi
        fi
    fi
    
    log_warning "ffmpeg capture failed"
    return 1
}

capture_with_photobooth() {
    local output="$1"
    
    log_info "Attempting capture with Photo Booth..."
    
    # Use AppleScript to control Photo Booth
    osascript <<EOD >/dev/null 2>&1
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

    # Find and copy the most recent Photo Booth photo
    PHOTOBOOTH_DIR="$HOME/Pictures/Photo Booth Library/Pictures"
    if [ -d "$PHOTOBOOTH_DIR" ]; then
        LATEST_PHOTO=$(ls -t "$PHOTOBOOTH_DIR" | grep -v "^\..*" | head -1)
        if [ -n "$LATEST_PHOTO" ]; then
            if cp "$PHOTOBOOTH_DIR/$LATEST_PHOTO" "$output"; then
                log_info "Successfully captured image with Photo Booth"
                return 0
            fi
        fi
    fi
    
    log_warning "Photo Booth capture failed"
    return 1
}

capture_video_with_ffmpeg() {
    local output="$1"
    local device_index="$2"
    local duration="$3"
    
    log_info "Capturing video with ffmpeg (duration: ${duration}s)..."
    
    if command -v ffmpeg >/dev/null 2>&1; then
        if ffmpeg -f avfoundation -framerate 30 -i "$device_index:none" -t "$duration" -c:v h264 -crf 23 "$output" >/dev/null 2>&1; then
            if [ -f "$output" ] && [ -s "$output" ]; then
                log_info "Successfully captured video with ffmpeg"
                return 0
            fi
        fi
    fi
    
    log_warning "ffmpeg video capture failed"
    return 1
}

convert_image_format() {
    local input="$1"
    local output="$2"
    local format="$3"
    
    log_info "Converting image to $format format..."
    
    if command -v sips >/dev/null 2>&1; then
        if sips -s format "$format" "$input" --out "$output" >/dev/null 2>&1; then
            log_info "Image format converted successfully"
            return 0
        fi
    fi
    
    log_warning "Image format conversion failed"
    return 1
}

# Main execution
log_info "Starting webcam capture..."
log_info "Output path: $OUTPUT_PATH"
log_info "Format: $FORMAT, Resolution: $RESOLUTION"

# Create a temporary file for initial capture
TMP_OUTPUT=$(mktemp).jpg

# Determine if video or still image capture
if [ "$VIDEO_MODE" = "true" ]; then
    # Video capture
    log_info "Video capture mode (duration: ${VIDEO_DURATION}s)"
    OUTPUT_WITH_EXTENSION="${OUTPUT_PATH%.*}.mp4"
    
    if capture_video_with_ffmpeg "$OUTPUT_WITH_EXTENSION" "$DEVICE_INDEX" "$VIDEO_DURATION"; then
        log_info "Video captured successfully: $OUTPUT_WITH_EXTENSION"
        exit 0
    else
        log_error "All video capture methods failed"
        exit 1
    fi
else
    # Still image capture - try multiple methods
    CAPTURE_SUCCESS=false
    
    # 1. Try imagesnap (most reliable)
    if command -v imagesnap >/dev/null 2>&1; then
        if capture_with_imagesnap "$TMP_OUTPUT" "$DEVICE_INDEX" "1"; then
            CAPTURE_SUCCESS=true
        fi
    fi
    
    # 2. Try AVFoundation if imagesnap failed
    if [ "$CAPTURE_SUCCESS" != "true" ]; then
        if capture_with_avfoundation "$TMP_OUTPUT" "$DEVICE_INDEX"; then
            CAPTURE_SUCCESS=true
        fi
    fi
    
    # 3. Try ffmpeg if previous methods failed
    if [ "$CAPTURE_SUCCESS" != "true" ] && command -v ffmpeg >/dev/null 2>&1; then
        if capture_with_ffmpeg "$TMP_OUTPUT" "$DEVICE_INDEX"; then
            CAPTURE_SUCCESS=true
        fi
    fi
    
    # 4. Last resort: Photo Booth
    if [ "$CAPTURE_SUCCESS" != "true" ]; then
        if capture_with_photobooth "$TMP_OUTPUT"; then
            CAPTURE_SUCCESS=true
        fi
    fi
    
    # Check if any method succeeded
    if [ "$CAPTURE_SUCCESS" = "true" ]; then
        log_info "Image captured successfully"
        
        # Convert to desired format if needed
        if [ "$FORMAT" != "jpg" ] && [ "$FORMAT" != "jpeg" ]; then
            OUTPUT_WITH_EXTENSION="${OUTPUT_PATH%.*}.${FORMAT}"
            if convert_image_format "$TMP_OUTPUT" "$OUTPUT_WITH_EXTENSION" "$FORMAT"; then
                rm -f "$TMP_OUTPUT"
                log_info "Final image saved as: $OUTPUT_WITH_EXTENSION"
                exit 0
            else
                # If conversion fails, just use the jpg
                cp "$TMP_OUTPUT" "${OUTPUT_PATH%.*}.jpg"
                rm -f "$TMP_OUTPUT"
                log_info "Conversion failed. Image saved as jpg: ${OUTPUT_PATH%.*}.jpg"
                exit 0
            fi
        else
            # Just use jpg directly
            cp "$TMP_OUTPUT" "${OUTPUT_PATH%.*}.jpg"
            rm -f "$TMP_OUTPUT"
            log_info "Image saved as: ${OUTPUT_PATH%.*}.jpg"
            exit 0
        fi
    else
        rm -f "$TMP_OUTPUT"
        log_error "All capture methods failed"
        exit 1
    fi
fi
