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
        """Zapisuje encoding twarzy.

        Od teraz dla kazdego face_id przechowujemy liste encodings,
        co pozwala np. zarejestrowac twarz w okularach i bez okularow,
        a przy rozpoznawaniu porownywac do obu wariantow.
        """
        filepath = os.path.join(self.encodings_dir, f"{face_id}.pkl")

        # Jesli istnieje juz plik, dolacz encoding do listy (multi‑sample)
        existing_encodings = []
        if os.path.exists(filepath):
            try:
                with open(filepath, 'rb') as f:
                    loaded = pickle.load(f)
                    if isinstance(loaded, list):
                        existing_encodings = loaded
                    else:
                        existing_encodings = [loaded]
            except Exception:
                existing_encodings = []

        all_encodings = existing_encodings + [encoding]

        with open(filepath, 'wb') as f:
            pickle.dump(all_encodings, f)

        self.known_encodings[face_id] = all_encodings
        self.known_face_ids[face_id] = face_id
    
    def register_face(self, image_path: str, face_id: str) -> bool:
        """Rejestruje nową twarz w systemie"""
        try:
            if not os.path.exists(image_path):
                print(f"Plik nie istnieje: {image_path}")
                return False
                
            image = face_recognition.load_image_file(image_path)
            # Uzyj modelu 'large' dla bardziej stabilnych cech
            encodings = face_recognition.face_encodings(image, model="large")
            
            if len(encodings) == 0:
                print("Nie wykryto twarzy na zdjęciu")
                return False
            
            # Uzyj pierwszego znalezionego encoding
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
            # 'large' lepiej radzi sobie z roznymi wariantami twarzy (np. z okularami / bez)
            unknown_encodings = face_recognition.face_encodings(unknown_image, model="large")
            
            if len(unknown_encodings) == 0:
                return None
            
            unknown_encoding = unknown_encodings[0]
            
            best_match = None
            best_distance = float('inf')
            
            for face_id, known_encoding in self.known_encodings.items():
                # known_encoding moze byc pojedynczym wektorem lub lista wektorow
                if isinstance(known_encoding, list):
                    distances = face_recognition.face_distance(known_encoding, unknown_encoding)
                    distance = float(np.min(distances))
                else:
                    distance = face_recognition.face_distance([known_encoding], unknown_encoding)[0]

                if distance < best_distance:
                    best_distance = distance
                    best_match = face_id
            
            # Konwersja distance na score (0-1, gdzie 1 to najlepsze dopasowanie)
            match_score = 1.0 - best_distance
            
            # Nieco obnizony prog, aby lepiej akceptowac naturalne roznice (okulary / bez)
            effective_threshold = threshold * 0.95
            
            if match_score >= effective_threshold:
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

    def detect_screen_spoof(self, image_path: str) -> bool:
        """
        Prosta heurystyka anty‑spoofingowa:
        próbuje wykryć duży, jasny, prostokątny obszar przypominający ekran telefonu.
        Zwraca True, jeśli obraz wygląda podejrzanie (możliwy ekran / zdjęcie).
        """
        try:
            img = cv2.imread(image_path)
            if img is None:
                return False

            h, w = img.shape[:2]
            # Zmniejsz obraz dla szybszego przetwarzania
            scale = 600.0 / max(h, w)
            if scale < 1.0:
                img = cv2.resize(img, (int(w * scale), int(h * scale)))

            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            blur = cv2.GaussianBlur(gray, (5, 5), 0)

            # Wykryj krawędzie
            edges = cv2.Canny(blur, 50, 150)

            # Znajdź kontury (kandydaci na prostokąt ekranu)
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            img_area = img.shape[0] * img.shape[1]
            suspect_rectangles = 0

            for cnt in contours:
                area = cv2.contourArea(cnt)
                # Interesują nas tylko dość duże obszary
                if area < 0.15 * img_area:
                    continue

                peri = cv2.arcLength(cnt, True)
                approx = cv2.approxPolyDP(cnt, 0.02 * peri, True)

                # Prostokąt = 4 wierzchołki
                if len(approx) == 4:
                    x, y, w_box, h_box = cv2.boundingRect(approx)
                    aspect = w_box / float(h_box)

                    # Typowe proporcje telefonu (portret/landscape) i nie za bardzo kwadratowe
                    if 0.3 < aspect < 3.5:
                        # Sprawdź jasność i równomierność wewnątrz tego prostokąta
                        roi = gray[y : y + h_box, x : x + w_box]
                        mean_intensity = float(np.mean(roi))
                        std_intensity = float(np.std(roi))

                        # Ekran telefonu: zwykle dosyć jasny i dość jednorodny
                        if mean_intensity > 120 and std_intensity < 40:
                            suspect_rectangles += 1

            # Jeśli znaleźliśmy co najmniej jeden „ekranopodobny” prostokąt – oznacz jako podejrzane
            return suspect_rectangles > 0

        except Exception as e:
            print(f"Błąd podczas detekcji spoofingu: {e}")
            return False

