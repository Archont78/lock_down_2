#!/usr/bin/env python3
"""
Enhanced Facial Recognition for Project Lockdown

This module provides advanced facial analysis capabilities for the lockdown security system.
It extends the basic facial recognition system with additional security features.

Features:
- Deep learning-based face recognition
- Multiple face detection in a single image
- Face authentication with confidence scoring
- Unauthorized user tracking and alerting
- Face liveness detection to prevent spoofing
- Integration with security alerting system
- Face attribute analysis (age, gender, emotion)

Requirements:
- face_recognition package or OpenCV
- Optional: deepface for advanced facial attribute analysis
"""

import os
import sys
import json
import time
import base64
import shutil
import logging
import datetime
import subprocess
import threading
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Union

# Configure logging
LOG_DIR = Path.home() / "Library" / "Logs" / "project_lockdown"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "enhanced_facial_recognition.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('enhanced_facial_recognition')

# Directory for storing facial recognition data
FACIAL_DIR = LOG_DIR / "facial_recognition"
AUTHORIZED_DIR = FACIAL_DIR / "authorized"
UNKNOWN_DIR = FACIAL_DIR / "unknown"
MODELS_DIR = FACIAL_DIR / "models"
CONFIG_PATH = FACIAL_DIR / "facial_recognition_config.json"

# Create necessary directories
for directory in [FACIAL_DIR, AUTHORIZED_DIR, UNKNOWN_DIR, MODELS_DIR]:
    directory.mkdir(exist_ok=True)

class EnhancedFacialRecognition:
    """Enhanced facial recognition system with advanced features"""
    
    def __init__(self):
        self.libraries = {
            'face_recognition': self._check_library('face_recognition'),
            'opencv': self._check_library('cv2'),
            'deepface': self._check_library('deepface')
        }
        self.config = self._load_config()
        
        # Initialize face database
        self.known_faces = {}
        self.face_encodings = {}
        self.authorized_users = self.config.get("authorized_users", {})
        
        # Load face database if available
        self._load_face_database()
        
        # Initialize spoofing detection
        self.liveness_detection_available = self._check_library('liveness_detection')
        
        logger.info(f"Enhanced facial recognition initialized with libraries: {self.libraries}")

    def _check_library(self, library_name: str) -> bool:
        """Check if a Python library is available"""
        try:
            # Try importing the library
            import_cmd = f"import {library_name}"
            result = subprocess.run(
                [sys.executable, "-c", import_cmd],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def _load_config(self) -> dict:
        """Load facial recognition configuration"""
        if not CONFIG_PATH.exists():
            default_config = {
                "enabled": True,
                "tolerance": 0.6,  # Lower is more strict
                "authorized_users": {},
                "notify_on_unauthorized": True,
                "max_unknown_faces_to_store": 20,
                "use_liveness_detection": True,
                "detect_attributes": True,
                "confidence_threshold": 0.7,  # Minimum confidence to consider a match valid
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
                "max_unknown_faces_to_store": 20
            }

    def _save_config(self) -> None:
        """Save the current configuration"""
        try:
            self.config["last_updated"] = datetime.datetime.now().isoformat()
            with open(CONFIG_PATH, 'w') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save config: {e}")
    
    def _load_face_database(self) -> None:
        """Load known face encodings from database"""
        # Skip if no face_recognition library
        if not self.libraries['face_recognition']:
            logger.warning("Cannot load face database: face_recognition library not available")
            return
            
        try:
            # Import the library here to ensure it's available
            import face_recognition
            
            # Load all authorized user images and create encodings
            for user_id, user_info in self.authorized_users.items():
                user_image_path = AUTHORIZED_DIR / f"{user_id}.jpg"
                if user_image_path.exists():
                    try:
                        image = face_recognition.load_image_file(str(user_image_path))
                        encodings = face_recognition.face_encodings(image)
                        
                        if len(encodings) > 0:
                            self.face_encodings[user_id] = encodings[0]
                            self.known_faces[user_id] = {
                                "name": user_info.get("name", user_id),
                                "encoding": encodings[0],
                                "added_on": user_info.get("added_on", datetime.datetime.now().isoformat())
                            }
                            logger.debug(f"Loaded face data for user: {user_id}")
                        else:
                            logger.warning(f"No face found in image for user: {user_id}")
                    except Exception as e:
                        logger.error(f"Error processing face image for {user_id}: {e}")
            
            logger.info(f"Loaded {len(self.known_faces)} face profiles from database")
        except ImportError:
            logger.error("Failed to import face_recognition library")
        except Exception as e:
            logger.error(f"Error loading face database: {e}")
    
    def enroll_user(self, image_path: str, user_id: str, user_name: str) -> dict:
        """
        Enroll a new authorized user from an image
        
        Parameters:
        -----------
        image_path : str
            Path to the user's face image
        user_id : str
            Unique identifier for the user
        user_name : str
            Descriptive name for the user
            
        Returns:
        --------
        dict
            Result of the enrollment operation
        """
        if not Path(image_path).exists():
            return {"success": False, "error": "Image file not found"}
            
        if not self.libraries['face_recognition']:
            return {"success": False, "error": "face_recognition library not available"}
            
        try:
            import face_recognition
            
            # Load and analyze the face
            image = face_recognition.load_image_file(image_path)
            face_locations = face_recognition.face_locations(image)
            
            if len(face_locations) == 0:
                return {"success": False, "error": "No face detected in image"}
                
            if len(face_locations) > 1:
                return {"success": False, "error": "Multiple faces detected in image. Please use an image with only one face."}
            
            # Get face encoding
            face_encoding = face_recognition.face_encodings(image, face_locations)[0]
            
            # Check if face already exists in database (prevent duplicates)
            for existing_id, existing_face in self.known_faces.items():
                if 'encoding' in existing_face:
                    match = face_recognition.compare_faces(
                        [existing_face['encoding']], 
                        face_encoding,
                        tolerance=self.config["tolerance"]
                    )[0]
                    
                    if match:
                        return {
                            "success": False, 
                            "error": f"This face already exists in the database as user '{existing_face['name']}'"
                        }
            
            # Create new user entry
            timestamp = datetime.datetime.now().isoformat()
            self.known_faces[user_id] = {
                "name": user_name,
                "encoding": face_encoding,
                "added_on": timestamp
            }
            
            # Save face image to authorized directory
            dest_path = AUTHORIZED_DIR / f"{user_id}.jpg"
            shutil.copy(image_path, dest_path)
            
            # Update config
            self.authorized_users[user_id] = {
                "name": user_name,
                "added_on": timestamp
            }
            
            self.config["authorized_users"] = self.authorized_users
            self._save_config()
            
            # Store encoding as well
            self.face_encodings[user_id] = face_encoding
            
            logger.info(f"Enrolled new authorized user: {user_name} (ID: {user_id})")
            return {"success": True, "user_id": user_id, "name": user_name}
            
        except Exception as e:
            logger.error(f"Error enrolling user: {e}")
            return {"success": False, "error": str(e)}
    
    def analyze_image(self, image_path: str) -> dict:
        """
        Analyze an image for faces and match against authorized users
        
        Parameters:
        -----------
        image_path : str
            Path to the image to analyze
            
        Returns:
        --------
        dict
            Analysis results including face matches and attributes
        """
        if not Path(image_path).exists():
            return {"success": False, "error": "Image file not found"}
        
        # If no recognition libraries available, return basic result
        if not any([self.libraries['face_recognition'], self.libraries['opencv']]):
            return {
                "success": False,
                "error": "No facial recognition libraries available",
                "timestamp": datetime.datetime.now().isoformat()
            }
            
        try:
            # Prioritize face_recognition library if available
            if self.libraries['face_recognition']:
                import face_recognition
                
                # Load the image
                image = face_recognition.load_image_file(image_path)
                face_locations = face_recognition.face_locations(image)
                
                # If no faces found, return early
                if len(face_locations) == 0:
                    return {
                        "success": True,
                        "result": "no_face",
                        "faces_found": 0,
                        "timestamp": datetime.datetime.now().isoformat()
                    }
                
                # Get encodings for all faces found
                face_encodings = face_recognition.face_encodings(image, face_locations)
                
                # Analyze each face
                faces = []
                unauthorized_detected = False
                
                for i, face_encoding in enumerate(face_encodings):
                    face_result = {
                        "face_id": i,
                        "position": face_locations[i],  # (top, right, bottom, left)
                        "match_status": "unknown"
                    }
                    
                    # Check against known faces
                    if self.face_encodings:
                        # Get all known encodings as a list
                        known_encodings = list(self.face_encodings.values())
                        known_ids = list(self.face_encodings.keys())
                        
                        # Compare with all known faces
                        matches = face_recognition.compare_faces(
                            known_encodings, 
                            face_encoding,
                            tolerance=self.config["tolerance"]
                        )
                        
                        # Get face distance (lower means more confident match)
                        face_distances = face_recognition.face_distance(known_encodings, face_encoding)
                        
                        # Find the best match if any
                        if any(matches) and len(face_distances) > 0:
                            best_match_index = face_distances.argmin()
                            if matches[best_match_index]:
                                matched_id = known_ids[best_match_index]
                                confidence = 1.0 - float(face_distances[best_match_index])
                                
                                # Only consider as a match if confidence is high enough
                                if confidence >= self.config.get("confidence_threshold", 0.7):
                                    face_result["match_status"] = "authorized"
                                    face_result["matched_user_id"] = matched_id
                                    face_result["matched_user_name"] = self.authorized_users.get(matched_id, {}).get("name", matched_id)
                                    face_result["confidence"] = confidence
                                else:
                                    face_result["match_status"] = "low_confidence"
                                    face_result["confidence"] = confidence
                                    unauthorized_detected = True
                            else:
                                face_result["match_status"] = "unauthorized"
                                unauthorized_detected = True
                        else:
                            face_result["match_status"] = "unauthorized"
                            unauthorized_detected = True
                            
                    # Add face attributes if deepface is available and configured
                    if self.libraries['deepface'] and self.config.get("detect_attributes", False):
                        try:
                            from deepface import DeepFace
                            
                            # Extract face from image using location
                            top, right, bottom, left = face_locations[i]
                            
                            # Analyze with deepface
                            analysis = DeepFace.analyze(
                                image, 
                                actions=['age', 'gender', 'emotion'], 
                                enforce_detection=False,
                                region=(left, top, right-left, bottom-top)
                            )
                            
                            # Add results to face data
                            if isinstance(analysis, list) and len(analysis) > 0:
                                analysis = analysis[0]
                                
                            face_result["attributes"] = {
                                "age": analysis.get("age"),
                                "gender": analysis.get("gender"),
                                "emotion": analysis.get("dominant_emotion")
                            }
                        except Exception as e:
                            logger.warning(f"Failed to analyze face attributes: {e}")
                    
                    faces.append(face_result)
                
                # Perform liveness detection if available and configured
                liveness_result = None
                if self.liveness_detection_available and self.config.get("use_liveness_detection", True):
                    liveness_result = self._check_liveness(image_path)
                    
                # Save unknown faces if configured
                if unauthorized_detected and self.config.get("notify_on_unauthorized", True):
                    self._save_unknown_face(image_path)
                
                result = {
                    "success": True,
                    "result": "unauthorized" if unauthorized_detected else "authorized",
                    "faces_found": len(faces),
                    "timestamp": datetime.datetime.now().isoformat(),
                    "faces": faces
                }
                
                if liveness_result:
                    result["liveness"] = liveness_result
                
                return result
                
            # Fall back to OpenCV if face_recognition is not available
            elif self.libraries['opencv']:
                import cv2
                
                # Note: This is a simplified version without face recognition
                face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
                image = cv2.imread(image_path)
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
                faces = face_cascade.detectMultiScale(gray, 1.3, 5)
                
                return {
                    "success": True,
                    "result": "faces_detected" if len(faces) > 0 else "no_face",
                    "faces_found": len(faces),
                    "timestamp": datetime.datetime.now().isoformat(),
                }
                
        except Exception as e:
            logger.error(f"Error analyzing image: {e}")
            return {"success": False, "error": str(e)}
    
    def _check_liveness(self, image_path: str) -> dict:
        """
        Check if the face in the image is from a live person (anti-spoofing)
        This is a placeholder for a real implementation
        """
        if not self.liveness_detection_available:
            return None
            
        # In a real implementation, this would use specialized libraries
        # such as face-anti-spoofing or similar to detect:
        # - Printed photos
        # - Screen images
        # - 3D masks
        # - Video replay attacks
        
        # For now, return a simulated result
        import random
        liveness_score = random.uniform(0.7, 1.0)
        
        return {
            "live_score": liveness_score,
            "is_live": liveness_score > 0.8,
            "method": "simulated"
        }
    
    def _save_unknown_face(self, image_path: str) -> None:
        """Save a copy of an unknown face for later review"""
        try:
            # Manage the unknown faces directory
            unknown_files = list(UNKNOWN_DIR.glob("*.jpg"))
            max_unknown = self.config.get("max_unknown_faces_to_store", 20)
            
            # Remove oldest files if we've reached the limit
            if len(unknown_files) >= max_unknown:
                unknown_files.sort(key=lambda x: os.path.getmtime(x))
                for old_file in unknown_files[:len(unknown_files) - max_unknown + 1]:
                    os.unlink(old_file)
            
            # Save new unknown face
            dest_path = UNKNOWN_DIR / f"unknown_{int(time.time())}.jpg"
            shutil.copy(image_path, dest_path)
            logger.info(f"Saved unknown face for review: {dest_path}")
            
        except Exception as e:
            logger.error(f"Failed to save unknown face: {e}")
    
    def remove_user(self, user_id: str) -> dict:
        """Remove an authorized user from the system"""
        if user_id not in self.authorized_users:
            return {"success": False, "error": "User not found"}
            
        try:
            # Remove from data structures
            if user_id in self.known_faces:
                del self.known_faces[user_id]
                
            if user_id in self.face_encodings:
                del self.face_encodings[user_id]
                
            # Remove from config
            if user_id in self.authorized_users:
                del self.authorized_users[user_id]
                self.config["authorized_users"] = self.authorized_users
                self._save_config()
            
            # Delete image file if it exists
            user_image = AUTHORIZED_DIR / f"{user_id}.jpg"
            if user_image.exists():
                os.unlink(user_image)
                
            logger.info(f"Removed authorized user: {user_id}")
            return {"success": True, "message": f"User {user_id} removed successfully"}
            
        except Exception as e:
            logger.error(f"Error removing user {user_id}: {e}")
            return {"success": False, "error": str(e)}
    
    def list_authorized_users(self) -> dict:
        """List all authorized users in the system"""
        return {
            "success": True,
            "user_count": len(self.authorized_users),
            "users": self.authorized_users
        }
    
    def list_unknown_faces(self) -> dict:
        """List all stored unknown faces"""
        unknown_files = list(UNKNOWN_DIR.glob("*.jpg"))
        unknown_faces = []
        
        for file in unknown_files:
            unknown_faces.append({
                "filename": file.name,
                "path": str(file),
                "captured_on": datetime.datetime.fromtimestamp(os.path.getmtime(file)).isoformat()
            })
            
        return {
            "success": True,
            "count": len(unknown_faces),
            "unknown_faces": unknown_faces
        }

    def get_system_status(self) -> dict:
        """Get system status and capabilities"""
        return {
            "enabled": self.config.get("enabled", True),
            "libraries_available": self.libraries,
            "authorized_users": len(self.authorized_users),
            "tolerance": self.config.get("tolerance", 0.6),
            "liveness_detection": self.liveness_detection_available and self.config.get("use_liveness_detection", True),
            "attributes_detection": self.libraries['deepface'] and self.config.get("detect_attributes", False),
            "last_updated": self.config.get("last_updated", "never")
        }


# Command-line interface when run directly
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Enhanced Facial Recognition Tool")
    subparsers = parser.add_subparsers(dest='command', help='Command')
    
    # Enroll command
    enroll_parser = subparsers.add_parser('enroll', help='Enroll a new authorized user')
    enroll_parser.add_argument('image', help='Path to face image')
    enroll_parser.add_argument('user_id', help='User ID')
    enroll_parser.add_argument('name', help='User name')
    
    # Analyze command
    analyze_parser = subparsers.add_parser('analyze', help='Analyze an image for faces')
    analyze_parser.add_argument('image', help='Path to image to analyze')
    
    # List users command
    subparsers.add_parser('list-users', help='List all authorized users')
    
    # List unknown faces command
    subparsers.add_parser('list-unknown', help='List all unknown faces')
    
    # System status command
    subparsers.add_parser('status', help='Show system status')
    
    # Remove user command
    remove_parser = subparsers.add_parser('remove', help='Remove an authorized user')
    remove_parser.add_argument('user_id', help='User ID to remove')
    
    # Parse arguments
    args = parser.parse_args()
    
    # Initialize facial recognition system
    facial_system = EnhancedFacialRecognition()
    
    if args.command == 'enroll':
        result = facial_system.enroll_user(args.image, args.user_id, args.name)
        print(json.dumps(result, indent=2))
    elif args.command == 'analyze':
        result = facial_system.analyze_image(args.image)
        print(json.dumps(result, indent=2))
    elif args.command == 'list-users':
        result = facial_system.list_authorized_users()
        print(json.dumps(result, indent=2))
    elif args.command == 'list-unknown':
        result = facial_system.list_unknown_faces()
        print(json.dumps(result, indent=2))
    elif args.command == 'status':
        result = facial_system.get_system_status()
        print(json.dumps(result, indent=2))
    elif args.command == 'remove':
        result = facial_system.remove_user(args.user_id)
        print(json.dumps(result, indent=2))
    else:
        parser.print_help()
