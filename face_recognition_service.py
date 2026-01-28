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

    # === POMOCNICZE ===================================================================
    def _load_and_normalize_image(self, image_path: str) -> Optional[np.ndarray]:
        """
        Wczytuje obraz i lekko normalizuje oświetlenie, żeby zwiększyć odporność
        na zmiane miejsca / światła (CLAHE na kanale jasności).
        Zwraca obraz w formacie RGB (numpy array) lub None.
        """
        img_bgr = cv2.imread(image_path)
        if img_bgr is None:
            return None

        # Konwersja do YCrCb i wyrównanie histogramu tylko kanału jasności
        ycrcb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2YCrCb)
        y, cr, cb = cv2.split(ycrcb)

        # CLAHE lepiej zachowuje szczegóły niż zwykłe equalizeHist
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        y_eq = clahe.apply(y)

        ycrcb_eq = cv2.merge((y_eq, cr, cb))
        img_eq_bgr = cv2.cvtColor(ycrcb_eq, cv2.COLOR_YCrCb2BGR)

        # face_recognition oczekuje RGB
        img_rgb = cv2.cvtColor(img_eq_bgr, cv2.COLOR_BGR2RGB)
        return img_rgb

    # === ZARZĄDZANIE ENCODINGAMI ======================================================
    def load_encodings(self):
        """Wczytuje zapisane encodings twarzy"""
        for filename in os.listdir(self.encodings_dir):
            if filename.endswith(".pkl"):
                face_id = filename[:-4]  # usuń .pkl
                filepath = os.path.join(self.encodings_dir, filename)
                with open(filepath, "rb") as f:
                    encoding = pickle.load(f)
                    self.known_encodings[face_id] = encoding
                    self.known_face_ids[face_id] = face_id

    def save_encoding(self, face_id: str, encoding):
        """Zapisuje encoding twarzy.

        Dla kazdego face_id przechowujemy liste encodings,
        co pozwala np. zarejestrowac twarz w okularach i bez okularow,
        a przy rozpoznawaniu porownywac do obu wariantow.
        """
        filepath = os.path.join(self.encodings_dir, f"{face_id}.pkl")

        # Jesli istnieje juz plik, dolacz encoding do listy (multi‑sample)
        existing_encodings = []
        if os.path.exists(filepath):
            try:
                with open(filepath, "rb") as f:
                    loaded = pickle.load(f)
                    if isinstance(loaded, list):
                        existing_encodings = loaded
                    else:
                        existing_encodings = [loaded]
            except Exception:
                existing_encodings = []

        all_encodings = existing_encodings + [encoding]

        with open(filepath, "wb") as f:
            pickle.dump(all_encodings, f)

        self.known_encodings[face_id] = all_encodings
        self.known_face_ids[face_id] = face_id

    # === REJESTRACJA ==================================================================
    def register_face(self, image_path: str, face_id: str) -> bool:
        """Rejestruje nową twarz w systemie"""
        try:
            if not os.path.exists(image_path):
                print(f"Plik nie istnieje: {image_path}")
                return False

            # Odrzuć od razu ewidentne zdjęcie z telefonu / ekranu
            if self.detect_screen_spoof(image_path):
                print("Wykryto możliwe użycie ekranu/zdjęcia przy rejestracji – odrzucono")
                return False

            image = self._load_and_normalize_image(image_path)
            if image is None:
                print("Nie udało się wczytać obrazu przy rejestracji")
                return False

            # Użyj modelu 'large' + kilka prób (jitters) do stabilniejszego wektora
            encodings = face_recognition.face_encodings(
                image, model="large", num_jitters=3
            )

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

    # === ROZPOZNAWANIE ===============================================================
    def recognize_face(
        self, image_path: str, threshold: float = 0.6
    ) -> Optional[Tuple[str, float]]:
        """
        Rozpoznaje twarz na zdjęciu.
        Zwraca (face_id, match_score) lub None.
        """
        try:
            # Dodatkowe zabezpieczenie przed zdjęciem z ekranu
            if self.detect_screen_spoof(image_path):
                print("Podejrzenie spoofingu ekranu/telefonu – rozpoznawanie przerwane")
                return None

            unknown_image = self._load_and_normalize_image(image_path)
            if unknown_image is None:
                return None

            # 'large' lepiej radzi sobie z roznymi wariantami twarzy (np. z okularami / bez)
            unknown_encodings = face_recognition.face_encodings(
                unknown_image, model="large"
            )

            if len(unknown_encodings) == 0:
                return None

            unknown_encoding = unknown_encodings[0]

            best_match = None
            best_distance = float("inf")

            for face_id, known_encoding in self.known_encodings.items():
                # known_encoding moze byc pojedynczym wektorem lub lista wektorow
                if isinstance(known_encoding, list):
                    distances = face_recognition.face_distance(
                        known_encoding, unknown_encoding
                    )
                    distance = float(np.min(distances))
                else:
                    distance = face_recognition.face_distance(
                        [known_encoding], unknown_encoding
                    )[0]

                if distance < best_distance:
                    best_distance = distance
                    best_match = face_id

            # Konwersja distance na score (0-1, gdzie 1 to najlepsze dopasowanie)
            match_score = 1.0 - best_distance

            # Bardziej liberalny próg przy rozpoznawaniu,
            # żeby lepiej tolerować zmiany oświetlenia, pozy, okulary.
            # Dla threshold=0.5 efektywny próg to 0.45 (obniżony o 0.1).
            effective_threshold = max(0.0, threshold - 0.1)

            if match_score >= effective_threshold:
                return (best_match, match_score)
            else:
                return None

        except Exception as e:
            print(f"Błąd podczas rozpoznawania twarzy: {e}")
            return None

    # === PROSTE NARZĘDZIA ============================================================
    def detect_face(self, image_path: str) -> bool:
        """Sprawdza czy na zdjęciu jest twarz"""
        try:
            image = self._load_and_normalize_image(image_path)
            if image is None:
                return False
            face_locations = face_recognition.face_locations(image)
            return len(face_locations) > 0
        except Exception as e:
            print(f"Błąd podczas wykrywania twarzy: {e}")
            return False

    def _eye_aspect_ratio(self, eye_points) -> float:
        """
        Eye Aspect Ratio (EAR) z 6 punktów oka:
        p1..p6 zgodnie z dlib/face_recognition (kolejność w face_landmarks).
        """
        try:
            p1, p2, p3, p4, p5, p6 = [np.array(p, dtype=np.float32) for p in eye_points]
            # EAR = (||p2-p6|| + ||p3-p5||) / (2*||p1-p4||)
            a = float(np.linalg.norm(p2 - p6))
            b = float(np.linalg.norm(p3 - p5))
            c = float(np.linalg.norm(p1 - p4))
            if c <= 1e-6:
                return 0.0
            return (a + b) / (2.0 * c)
        except Exception:
            return 0.0

    def detect_blink_liveness(self, image_paths) -> bool:
        """
        Prosty test liveness na podstawie mrugnięcia na wielu klatkach.
        - Wymaga, aby na klatkach była ta sama twarz (mała odległość embeddingu)
        - Wymaga zmiany EAR: w sekwencji musi wystąpić stan "oczy otwarte" i "oczy bardziej zamknięte"
        """
        try:
            if not image_paths or len(image_paths) < 3:
                return False

            ears = []
            encs = []

            for p in image_paths:
                img = self._load_and_normalize_image(p)
                if img is None:
                    return False

                # embedding (ta sama osoba między klatkami)
                e = face_recognition.face_encodings(img, model="large")
                if len(e) == 0:
                    return False
                encs.append(e[0])

                lm = face_recognition.face_landmarks(img)
                if not lm:
                    return False

                left = lm[0].get("left_eye")
                right = lm[0].get("right_eye")
                if not left or not right or len(left) < 6 or len(right) < 6:
                    return False

                ear = (self._eye_aspect_ratio(left) + self._eye_aspect_ratio(right)) / 2.0
                ears.append(float(ear))

            # Sprawdź, że to ta sama twarz (nie podmieniono w trakcie)
            base = encs[0]
            for e in encs[1:]:
                dist = float(face_recognition.face_distance([base], e)[0])
                # troszkę luźniej, bo klatki mogą być poruszone / inne światło
                if dist > 0.42:
                    return False

            ear_min = float(np.min(ears))
            ear_max = float(np.max(ears))

            # Progi luźniejsze (różne kamery / okulary / światło)
            # Typowo: otwarte oczy ~0.20-0.30, zamknięte spadają poniżej ~0.18-0.19
            has_open = ear_max >= 0.21
            has_closed = ear_min <= 0.19
            enough_delta = (ear_max - ear_min) >= 0.05

            # Dodatkowo: szukamy "przejścia" (żeby nie łapać przypadkowego szumu)
            blink_transition = False
            for i in range(1, len(ears)):
                if ears[i - 1] >= 0.21 and ears[i] <= 0.19:
                    blink_transition = True
                    break
                if ears[i - 1] <= 0.19 and ears[i] >= 0.21:
                    blink_transition = True
                    break

            return bool(has_open and has_closed and enough_delta and blink_transition)

        except Exception as e:
            print(f"Błąd podczas detekcji liveness (blink): {e}")
            return False

    def detect_screen_spoof(self, image_path: str) -> bool:
        """
        Konserwatywna heurystyka anty‑spoofingowa:
        próbuje wykryć duży, jasny, prostokątny obszar przypominający ekran telefonu.
        Zwraca True TYLKO jeśli obraz wygląda BARDZO podejrzanie (możliwy ekran / zdjęcie).
        
        Funkcja jest bardzo konserwatywna - lepiej nie wykryć telefonu niż odrzucić prawdziwą twarz.
        """
        try:
            img = cv2.imread(image_path)
            if img is None:
                return False

            # NAJPIERW: Sprawdź czy na obrazie jest wykryta twarz przez face_recognition.
            # Jeśli jest, nadal MOŻE to być zdjęcie z telefonu, więc nie wyłączamy detekcji,
            # tylko podnosimy wymagania (żeby uniknąć fałszywych pozytywów).
            try:
                face_image = face_recognition.load_image_file(image_path)
                face_locations = face_recognition.face_locations(face_image)
                # Jeśli wykryto twarz, jesteśmy bardziej konserwatywni
                has_face = len(face_locations) > 0
            except:
                has_face = False

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
            contours, _ = cv2.findContours(
                edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )

            img_area = img.shape[0] * img.shape[1]
            # Zbieramy najlepszy (największy) kandydat na ekran
            best_rect = None  # (x, y, w, h)
            best_area = 0.0

            for cnt in contours:
                area = cv2.contourArea(cnt)
                # Interesują nas tylko dość duże obszary - telefon powinien zajmować znaczną część kadru
                if area < 0.15 * img_area:  # Wróciliśmy do wyższego progu
                    continue

                peri = cv2.arcLength(cnt, True)
                approx = cv2.approxPolyDP(cnt, 0.02 * peri, True)

                # Prostokąt = 4 wierzchołki
                if len(approx) == 4:
                    x, y, w_box, h_box = cv2.boundingRect(approx)
                    aspect = w_box / float(h_box)

                    # Typowe proporcje telefonu (portret/landscape)
                    if 0.4 < aspect < 2.5:  # Bardziej restrykcyjne proporcje
                        if area > best_area:
                            best_area = area
                            best_rect = (x, y, w_box, h_box)

            # Brak sensownego prostokąta = brak spoofingu (konserwatywnie)
            if best_rect is None:
                return False

            x, y, w_box, h_box = best_rect
            roi = gray[y : y + h_box, x : x + w_box]
            if roi.size == 0:
                return False

            # --- Punktacja sygnałów "to jest ekran" ---
            # 1) Jednorodność/jasność (ekran bywa jasny i dość równy)
            mean_intensity = float(np.mean(roi))
            std_intensity = float(np.std(roi))
            uniform_score = 0
            if mean_intensity > 160 and std_intensity < 35:
                uniform_score = 1
            if mean_intensity > 185 and std_intensity < 30:
                uniform_score = 2

            # 2) Ramka: dużo krawędzi blisko granic prostokąta (bezel/obramowanie)
            roi_edges = edges[y : y + h_box, x : x + w_box]
            border = max(2, int(min(w_box, h_box) * 0.06))  # ~6% szerokości
            # Maska brzegu: góra/dół/lewo/prawo
            top = roi_edges[:border, :]
            bottom = roi_edges[-border:, :]
            left = roi_edges[:, :border]
            right = roi_edges[:, -border:]
            border_edges = (
                int(np.count_nonzero(top))
                + int(np.count_nonzero(bottom))
                + int(np.count_nonzero(left))
                + int(np.count_nonzero(right))
            )
            border_area = (
                top.size + bottom.size + left.size + right.size
            )
            border_edge_density = border_edges / float(max(1, border_area))
            border_score = 0
            if border_edge_density > 0.06:
                border_score = 1
            if border_edge_density > 0.10:
                border_score = 2

            # 3) Moiré / "siatka pikseli": prosta analiza widma FFT w ROI.
            # Nie jest to idealne, ale często wyłapuje ekran/telefon z fotografią.
            moire_score = 0
            try:
                roi_small = cv2.resize(roi, (256, 256))
                roi_small = roi_small.astype(np.float32)
                roi_small -= float(np.mean(roi_small))
                fft = np.fft.fft2(roi_small)
                mag = np.abs(np.fft.fftshift(fft))
                # Maskujemy centrum (niskie częstotliwości)
                c = 128
                r = 18
                mag[c - r : c + r, c - r : c + r] = 0
                m_mean = float(np.mean(mag))
                m_std = float(np.std(mag))
                # Bierzemy kilka najwyższych pików – ekrany częściej mają wyraźne piki
                flat = mag.reshape(-1)
                if flat.size > 0:
                    topk = np.partition(flat, -10)[-10:]
                    peaks = [float(x) for x in topk if x > m_mean + 6.0 * m_std]
                    if len(peaks) >= 2:
                        moire_score = 1
                    if len(peaks) >= 5:
                        moire_score = 2
            except Exception:
                moire_score = 0

            # 4) Wielkość prostokąta (im większy, tym bardziej prawdopodobny ekran pokazany do kamery)
            area_ratio = best_area / float(img_area)
            size_score = 0
            if area_ratio > 0.25:
                size_score = 1
            if area_ratio > 0.40:
                size_score = 2

            total_score = uniform_score + border_score + moire_score + size_score

            # Wymagania zależnie od tego, czy wykryto twarz:
            # - jeśli jest twarz: wymagamy wyższego score, żeby nie oznaczać prawdziwych twarzy jako spoof
            # - jeśli nie ma twarzy: możemy być nieco bardziej agresywni
            if has_face:
                return total_score >= 5
            else:
                return total_score >= 4

        except Exception as e:
            print(f"Błąd podczas detekcji spoofingu: {e}")
            return False

