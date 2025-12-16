# System Weryfikacji Tożsamości Pracowników

System automatycznego logowania wejść i wyjść z funkcją weryfikacji tożsamości pracowników za pomocą kodu QR i biometrii (rozpoznawanie twarzy).

## Wymagania

- Python 3.8+
- Kamera (dla rozpoznawania twarzy)
- Czytnik kodów QR (kamera)

## Instalacja

1. Zainstaluj zależności:
```bash
pip install -r requirements.txt
```

**UWAGA:** Biblioteka `face-recognition` wymaga dodatkowych zależności systemowych:
- **Windows:** Zainstaluj Visual C++ Redistributable
- **Linux:** `sudo apt-get install build-essential cmake libopenblas-dev liblapack-dev libx11-dev libgtk-3-dev`
- **macOS:** `brew install cmake`

2. (Opcjonalnie) Utwórz przykładowe dane testowe:
```bash
python test_setup.py
```

3. Uruchom serwer:
```bash
python main.py
```

4. Otwórz przeglądarkę i przejdź do:
- **Frontend weryfikacji:** http://localhost:8000
- **Panel administracyjny:** http://localhost:8000/admin
- **API docs (Swagger):** http://localhost:8000/docs

## Funkcjonalności

- ✅ Skanowanie kodu QR przez pracownika
- ✅ Wykonanie zdjęcia twarzy i weryfikacja w bazie danych (rozpoznawanie twarzy)
- ✅ Automatyzacja logowania wejść i wyjść
- ✅ Panel administracyjny do zarządzania pracownikami i przepustkami
- ✅ Generowanie raportów PDF z logami dostępu
- ✅ Wykrywanie podejrzanych sytuacji (użycie cudzej karty)

## Jak używać

### 1. Dodaj użytkownika
- Przejdź do panelu administracyjnego (`/admin`)
- Wypełnij formularz "Dodaj nowego użytkownika"
- Kliknij "Dodaj użytkownika"

### 2. Zarejestruj twarz użytkownika
- W panelu admin wybierz użytkownika z listy
- Wybierz zdjęcie z wyraźnie widoczną twarzą
- Kliknij "Zarejestruj twarz"

### 3. Utwórz przepustkę (kod QR)
- Wybierz użytkownika
- Ustaw datę ważności
- Kliknij "Dodaj przepustkę"
- Możesz pobrać kod QR klikając "Pobierz QR"

### 4. Weryfikacja dostępu
- Przejdź do strony głównej (`/`)
- Zezwól na dostęp do kamery
- Wprowadź kod QR (lub zeskanuj)
- Kliknij "Zrób zdjęcie"
- Kliknij "Zweryfikuj"
- System sprawdzi zgodność twarzy z kodem QR

## Struktura projektu

- `main.py` - Główny plik uruchomieniowy FastAPI
- `database.py` - Modele bazy danych
- `models.py` - Modele Pydantic
- `face_recognition_service.py` - Serwis rozpoznawania twarzy
- `qr_service.py` - Serwis obsługi kodów QR
- `report_service.py` - Generowanie raportów PDF
- `static/` - Pliki statyczne (HTML, CSS, JS)
- `uploads/` - Przechowywanie zdjęć
- `reports/` - Wygenerowane raporty PDF

