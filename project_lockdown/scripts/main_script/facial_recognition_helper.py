#!/usr/bin/env python3
"""
Facial Recognition Helper Module for Project Lockdown

This module provides utilities for working with facial recognition
in the lockdown security system.

Features:
- Enrollment of authorized users
- Verification against authorized users
- Detection of unknown faces

Requirements:
- face_recognition package (pip install face_recognition) or
- OpenCV (pip install opencv-python) as fallback
"""

import os
import sys
import json
import time
import logging
import datetime
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

# Configure logging
LOG_DIR = Path.home() / "Library" / "Logs" / "project_lockdown"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "facial_recognition.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('facial_recognition')

# Directory for storing facial recognition data
FACIAL_DIR = LOG_DIR / "facial_recognition"
AUTHORIZED_DIR = FACIAL_DIR / "authorized"
UNKNOWN_DIR = FACIAL_DIR / "unknown"
CONFIG_PATH = FACIAL_DIR / "facial_recognition_config.json"

for directory in [FACIAL_DIR, AUTHORIZED_DIR, UNKNOWN_DIR]:
    directory.mkdir(exist_ok=True)


class FacialRecognitionManager:
    def __init__(self):
        self.available_library = None
        self.config = self._load_config()
        self._detect_libraries()

    def _load_config(self) -> dict:
        """Load facial recognition configuration"""
        if not CONFIG_PATH.exists():
            default_config = {
                "enabled": True,
                "tolerance": 0.6,  # Lower is more strict
                "authorized_users": {},
                "notify_on_unauthorized": True,
                "max_unknown_faces_to_store": 10,
                "last_updated": datetime.datetime.now().isoformat()
            }
            
            with open(CONFIG_PATH, 'w') as f:
                json.dump(default_config, f, indent=2)
            
            return default_config
        
        try:
            with open(CONFIG_PATH, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load config, using defaults: {e}")
            return {
                "enabled": True,
                "tolerance": 0.6,
                "authorized_users": {},
                "notify_on_unauthorized": True,
                "max_unknown_faces_to_store": 10
            }

    def _detect_libraries(self) -> None:
        """Check which facial recognition libraries are available"""
        try:
            # Check for face_recognition library (preferred)
            import_cmd = "import face_recognition"
            result = subprocess.run(
                [sys.executable, "-c", import_cmd],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            if result.returncode == 0:
                self.available_library = "face_recognition"
                logger.info("Using face_recognition library")
                try:
                    import face_recognition
                    self.face_recognition = face_recognition
                except ImportError:
                    logger.error("Failed to import face_recognition despite successful check")
            else:
                # Try OpenCV as fallback
                import_cmd = "import cv2"
                result = subprocess.run(
                    [sys.executable, "-c", import_cmd],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                
                if result.returncode == 0:
                    self.available_library = "opencv"
                    logger.info("Using OpenCV for basic face detection")
                    try:
                        import cv2
                        self.cv2 = cv2
                    except ImportError:
                        logger.error("Failed to import cv2 despite successful check")
                else:
                    self.available_library = None
                    logger.warning("No facial recognition libraries available")
        except Exception as e:
            logger.error(f"Error detecting libraries: {e}")
            self.available_library = None

    def enroll_user(self, image_path: str, username: str, full_name: str = None) -> bool:
        """
        Enroll a new authorized user
        
        Parameters:
        -----------
        image_path: str
            Path to the image of the user's face
        username: str
            Username identifier for this user
        full_name: str, optional
            Full name of the user
            
        Returns:
        --------
        bool: True if enrollment was successful
        """
        if not self.available_library:
            logger.error("No facial recognition libraries available")
            return False
            
        try:
            # Verify the image contains a face
            if self.available_library == "face_recognition":
                import face_recognition
                try:
                    image = face_recognition.load_image_file(image_path)
                    face_locations = face_recognition.face_locations(image)
                    
                    if len(face_locations) == 0:
                        logger.error("No face detected in the image")
                        return False
                    
                    if len(face_locations) > 1:
                        logger.warning(f"Multiple faces ({len(face_locations)}) detected in the image")
                    
                    # Copy the image to the authorized directory
                    user_image_path = AUTHORIZED_DIR / f"{username}.jpg"
                    from shutil import copy
                    copy(image_path, user_image_path)
                    
                    # Update the configuration
                    self.config["authorized_users"][username] = {
                        "name": full_name or username,
                        "image_path": str(user_image_path),
                        "added_date": datetime.datetime.now().isoformat()
                    }
                    
                    with open(CONFIG_PATH, 'w') as f:
                        json.dump(self.config, f, indent=2)
                    
                    logger.info(f"Successfully enrolled user: {username}")
                    return True
                    
                except Exception as e:
                    logger.error(f"Error enrolling user with face_recognition: {e}")
                    return False
            
            elif self.available_library == "opencv":
                import cv2
                try:
                    # Load OpenCV face detector
                    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
                    img = cv2.imread(image_path)
                    
                    if img is None:
                        logger.error(f"Failed to load image: {image_path}")
                        return False
                        
                    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                    faces = face_cascade.detectMultiScale(gray, 1.3, 5)
                    
                    if len(faces) == 0:
                        logger.error("No face detected in the image")
                        return False
                        
                    if len(faces) > 1:
                        logger.warning(f"Multiple faces ({len(faces)}) detected in the image")
                    
                    # Copy the image to the authorized directory
                    user_image_path = AUTHORIZED_DIR / f"{username}.jpg"
                    from shutil import copy
                    copy(image_path, user_image_path)
                    
                    # Update the configuration
                    self.config["authorized_users"][username] = {
                        "name": full_name or username,
                        "image_path": str(user_image_path),
                        "added_date": datetime.datetime.now().isoformat()
                    }
                    
                    with open(CONFIG_PATH, 'w') as f:
                        json.dump(self.config, f, indent=2)
                    
                    logger.info(f"Successfully enrolled user with OpenCV: {username}")
                    return True
                    
                except Exception as e:
                    logger.error(f"Error enrolling user with OpenCV: {e}")
                    return False
            
            return False
            
        except Exception as e:
            logger.error(f"Error in enroll_user: {e}")
            return False

    def verify_face(self, image_path: str) -> dict:
        """
        Verify if a face matches any authorized user
        
        Parameters:
        -----------
        image_path: str
            Path to the image to verify
            
        Returns:
        --------
        dict: Result with match information
        """
        if not self.available_library:
            return {"result": "no_library", "message": "No facial recognition libraries available"}
            
        if not self.config["authorized_users"]:
            return {"result": "no_users", "message": "No authorized users enrolled"}
            
        try:
            if self.available_library == "face_recognition":
                import face_recognition
                try:
                    # Load the unknown image
                    unknown_image = face_recognition.load_image_file(image_path)
                    unknown_face_locations = face_recognition.face_locations(unknown_image)
                    
                    if len(unknown_face_locations) == 0:
                        return {"result": "no_face", "message": "No face detected in image"}
                    
                    # Get facial encoding for the first face in the image
                    unknown_encoding = face_recognition.face_encodings(unknown_image, [unknown_face_locations[0]])[0]
                    
                    # Compare with all authorized users
                    best_match = None
                    best_distance = 1.0  # Lower is better, 0 is perfect match
                    
                    for username, user_data in self.config["authorized_users"].items():
                        user_image_path = user_data["image_path"]
                        
                        if not os.path.exists(user_image_path):
                            logger.warning(f"Image for user {username} not found: {user_image_path}")
                            continue
                        
                        # Load the known image
                        known_image = face_recognition.load_image_file(user_image_path)
                        known_face_locations = face_recognition.face_locations(known_image)
                        
                        if len(known_face_locations) == 0:
                            logger.warning(f"No face found in authorized image for {username}")
                            continue
                            
                        # Get encoding for the first face
                        known_encoding = face_recognition.face_encodings(known_image, [known_face_locations[0]])[0]
                        
                        # Compare faces
                        face_distance = face_recognition.face_distance([known_encoding], unknown_encoding)[0]
                        
                        if face_distance < best_distance:
                            best_distance = face_distance
                            best_match = {
                                "username": username,
                                "name": user_data["name"],
                                "confidence": 1 - face_distance
                            }
                    
                    # Determine if it's a match based on tolerance
                    tolerance = self.config.get("tolerance", 0.6)
                    
                    if best_match and best_distance <= tolerance:
                        return {
                            "result": "match",
                            "matched_user": best_match["username"],
                            "name": best_match["name"],
                            "confidence": best_match["confidence"]
                        }
                    else:
                        # Store unknown face if configured
                        if self.config.get("max_unknown_faces_to_store", 0) > 0:
                            self._store_unknown_face(image_path)
                        
                        return {
                            "result": "no_match",
                            "message": "Face does not match any authorized user",
                            "best_distance": best_distance if best_match else 1.0
                        }
                        
                except Exception as e:
                    logger.error(f"Error verifying face with face_recognition: {e}")
                    return {"result": "error", "message": str(e)}
                    
            elif self.available_library == "opencv":
                # OpenCV can only detect faces, not recognize/compare them
                import cv2
                try:
                    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
                    img = cv2.imread(image_path)
                    
                    if img is None:
                        return {"result": "error", "message": f"Failed to load image: {image_path}"}
                        
                    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                    faces = face_cascade.detectMultiScale(gray, 1.3, 5)
                    
                    if len(faces) == 0:
                        return {"result": "no_face", "message": "No face detected in image"}
                    
                    # With OpenCV alone, we can only detect faces, not recognize them
                    # So we just return that we found a face
                    return {
                        "result": "face_detected",
                        "message": "Face detected but recognition unavailable with OpenCV only",
                        "faces_found": len(faces)
                    }
                    
                except Exception as e:
                    logger.error(f"Error detecting face with OpenCV: {e}")
                    return {"result": "error", "message": str(e)}
            
            return {"result": "unavailable", "message": "No suitable facial recognition method available"}
            
        except Exception as e:
            logger.error(f"Error in verify_face: {e}")
            return {"result": "error", "message": str(e)}

    def _store_unknown_face(self, image_path: str) -> bool:
        """Store an unknown face for later review"""
        try:
            max_unknown = self.config.get("max_unknown_faces_to_store", 10)
            if max_unknown <= 0:
                return False
                
            # Check if we need to clean up old files
            unknown_files = list(UNKNOWN_DIR.glob("*.jpg"))
            if len(unknown_files) >= max_unknown:
                # Sort by creation time, oldest first
                unknown_files.sort(key=lambda x: os.path.getctime(x))
                
                # Remove oldest files to stay under the limit
                for old_file in unknown_files[:len(unknown_files) - max_unknown + 1]:
                    try:
                        os.unlink(old_file)
                    except Exception as e:
                        logger.error(f"Could not remove old unknown face: {e}")
            
            # Save the new unknown face
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            unknown_path = UNKNOWN_DIR / f"unknown_{timestamp}.jpg"
            
            from shutil import copy
            copy(image_path, unknown_path)
            logger.info(f"Stored unknown face: {unknown_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store unknown face: {e}")
            return False

    def list_authorized_users(self) -> List[Dict[str, str]]:
        """Get a list of all authorized users"""
        try:
            users = []
            for username, data in self.config["authorized_users"].items():
                users.append({
                    "username": username,
                    "name": data.get("name", username),
                    "image_path": data.get("image_path", ""),
                    "added_date": data.get("added_date", "unknown")
                })
            return users
        except Exception as e:
            logger.error(f"Failed to list authorized users: {e}")
            return []

    def remove_user(self, username: str) -> bool:
        """Remove an authorized user"""
        try:
            if username not in self.config["authorized_users"]:
                logger.warning(f"User does not exist: {username}")
                return False
                
            # Get image path before removing from config
            image_path = self.config["authorized_users"][username].get("image_path", "")
            
            # Remove from config
            del self.config["authorized_users"][username]
            with open(CONFIG_PATH, 'w') as f:
                json.dump(self.config, f, indent=2)
                
            # Try to remove the image file
            if image_path and os.path.exists(image_path):
                try:
                    os.unlink(image_path)
                except Exception as e:
                    logger.warning(f"Could not remove user image: {e}")
            
            logger.info(f"Removed user: {username}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to remove user: {e}")
            return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print(f"{sys.argv[0]} enroll <image_path> <username> [full_name]")
        print(f"{sys.argv[0]} verify <image_path>")
        print(f"{sys.argv[0]} list")
        print(f"{sys.argv[0]} remove <username>")
        sys.exit(1)
        
    manager = FacialRecognitionManager()
    command = sys.argv[1]
    
    if command == "enroll" and len(sys.argv) >= 4:
        image_path = sys.argv[2]
        username = sys.argv[3]
        full_name = sys.argv[4] if len(sys.argv) > 4 else None
        
        if not os.path.exists(image_path):
            print(f"Error: Image not found: {image_path}")
            sys.exit(1)
            
        result = manager.enroll_user(image_path, username, full_name)
        if result:
            print(f"Successfully enrolled user: {username}")
        else:
            print("Failed to enroll user")
            sys.exit(1)
            
    elif command == "verify" and len(sys.argv) >= 3:
        image_path = sys.argv[2]
        
        if not os.path.exists(image_path):
            print(f"Error: Image not found: {image_path}")
            sys.exit(1)
            
        result = manager.verify_face(image_path)
        print(json.dumps(result, indent=2))
        
    elif command == "list":
        users = manager.list_authorized_users()
        if users:
            print(f"Found {len(users)} authorized users:")
            for user in users:
                print(f"  - {user['username']} ({user['name']})")
        else:
            print("No authorized users found")
            
    elif command == "remove" and len(sys.argv) >= 3:
        username = sys.argv[2]
        result = manager.remove_user(username)
        if result:
            print(f"Successfully removed user: {username}")
        else:
            print(f"Failed to remove user: {username}")
            sys.exit(1)
            
    else:
        print("Invalid command or missing arguments")
        sys.exit(1)
