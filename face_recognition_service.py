import face_recognition
import numpy as np
import cv2
import os
from typing import Optional, Tuple
import pickle

class FaceRecognitionService:
    def __init__(self, encodings_dir: str = "face_encodings"):
        self.encodings_dir = encodings_dir
        os.makedirs(encodings_dir, exist_ok=True)
        self.known_encodings = {}
        self.known_face_ids = {}
        self.load_encodings()
    
    def load_encodings(self):
        """Wczytuje zapisane encodings twarzy"""
        for filename in os.listdir(self.encodings_dir):
            if filename.endswith('.pkl'):
                face_id = filename[:-4]  # usuń .pkl
                filepath = os.path.join(self.encodings_dir, filename)
                with open(filepath, 'rb') as f:
                    encoding = pickle.load(f)
                    self.known_encodings[face_id] = encoding
                    self.known_face_ids[face_id] = face_id
    
    def save_encoding(self, face_id: str, encoding):
        """Zapisuje encoding twarzy"""
        filepath = os.path.join(self.encodings_dir, f"{face_id}.pkl")
        with open(filepath, 'wb') as f:
            pickle.dump(encoding, f)
        self.known_encodings[face_id] = encoding
        self.known_face_ids[face_id] = face_id
    
    def register_face(self, image_path: str, face_id: str) -> bool:
        """Rejestruje nową twarz w systemie"""
        try:
            if not os.path.exists(image_path):
                print(f"Plik nie istnieje: {image_path}")
                return False
                
            image = face_recognition.load_image_file(image_path)
            encodings = face_recognition.face_encodings(image)
            
            if len(encodings) == 0:
                print("Nie wykryto twarzy na zdjęciu")
                return False
            
            # Użyj pierwszego znalezionego encoding
            encoding = encodings[0]
            self.save_encoding(face_id, encoding)
            return True
        except Exception as e:
            print(f"Błąd podczas rejestracji twarzy: {e}")
            return False
    
    def recognize_face(self, image_path: str, threshold: float = 0.6) -> Optional[Tuple[str, float]]:
        """
        Rozpoznaje twarz na zdjęciu
        Zwraca (face_id, match_score) lub None
        """
        try:
            unknown_image = face_recognition.load_image_file(image_path)
            unknown_encodings = face_recognition.face_encodings(unknown_image)
            
            if len(unknown_encodings) == 0:
                return None
            
            unknown_encoding = unknown_encodings[0]
            
            best_match = None
            best_distance = float('inf')
            
            for face_id, known_encoding in self.known_encodings.items():
                distance = face_recognition.face_distance([known_encoding], unknown_encoding)[0]
                if distance < best_distance:
                    best_distance = distance
                    best_match = face_id
            
            # Konwersja distance na score (0-1, gdzie 1 to najlepsze dopasowanie)
            match_score = 1.0 - best_distance
            
            if match_score >= threshold:
                return (best_match, match_score)
            else:
                return None
                
        except Exception as e:
            print(f"Błąd podczas rozpoznawania twarzy: {e}")
            return None
    
    def detect_face(self, image_path: str) -> bool:
        """Sprawdza czy na zdjęciu jest twarz"""
        try:
            image = face_recognition.load_image_file(image_path)
            face_locations = face_recognition.face_locations(image)
            return len(face_locations) > 0
        except Exception as e:
            print(f"Błąd podczas wykrywania twarzy: {e}")
            return False

