from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import datetime, date, timedelta
from jose import JWTError, jwt
import os
import shutil
from typing import List, Optional

from database import get_db, init_db, User, Badge, AccessLog, ResultEnum
from models import (
    UserCreate, UserResponse, BadgeCreate, BadgeResponse,
    VerificationRequest, VerificationResponse, AccessLogResponse
)
from face_recognition_service import FaceRecognitionService
from qr_service import QRService
from report_service import ReportService

app = FastAPI(title="System Weryfikacji Tożsamości")

# Konfiguracja JWT
SECRET_KEY = "admin-secret-key-change-in-production"
ALGORITHM = "HS256"
ADMIN_PASSWORD = "admin"

# Inicjalizacja serwisów
face_service = FaceRecognitionService()
qr_service = QRService()
report_service = ReportService()

# Security
security = HTTPBearer(auto_error=False)

# Katalogi
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs("static", exist_ok=True)
os.makedirs("reports", exist_ok=True)

# Montowanie plików statycznych
app.mount("/static", StaticFiles(directory="static"), name="static")

# Inicjalizacja bazy danych przy starcie
@app.on_event("startup")
def startup_event():
    init_db()


@app.get("/", response_class=HTMLResponse)
async def read_root():
    """Główna strona - ekran weryfikacji"""
    with open("static/index.html", "r", encoding="utf-8") as f:
        return f.read()


@app.get("/admin", response_class=HTMLResponse)
async def admin_panel():
    """Panel administracyjny"""
    with open("static/admin.html", "r", encoding="utf-8") as f:
        return f.read()


# Funkcja do tworzenia tokenu JWT
def create_access_token():
    """Tworzy token JWT dla admina"""
    expire = datetime.utcnow() + timedelta(hours=24)
    to_encode = {"sub": "admin", "exp": expire}
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


# Dependency do sprawdzania autoryzacji
async def verify_admin_token(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)):
    """Sprawdza czy token jest prawidłowy"""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Brak autoryzacji"
        )
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("sub") != "admin":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Nieprawidłowy token"
            )
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nieprawidłowy token"
        )


# Endpoint logowania
@app.post("/api/admin/login")
async def admin_login(password: str = Form(...)):
    """Logowanie do panelu admina"""
    if password == "admin":
        token = create_access_token()
        return {"success": True, "token": token, "message": "Zalogowano pomyślnie"}
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nieprawidłowe hasło"
        )


# Endpoint sprawdzania autoryzacji
@app.get("/api/admin/check-auth")
async def check_auth(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)):
    """Sprawdza czy użytkownik jest zalogowany"""
    if not credentials:
        return {"authenticated": False}
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("sub") == "admin":
            return {"authenticated": True}
    except JWTError:
        pass
    return {"authenticated": False}


# API Endpoints

@app.post("/api/verify", response_model=VerificationResponse)
async def verify_access(
    qr_code: str = Form(...),
    image: Optional[UploadFile] = File(None),
    images: List[UploadFile] = File(default=[]),
    db: Session = Depends(get_db)
):
    """
    Weryfikacja dostępu - skanowanie QR i rozpoznawanie twarzy
    """
    try:
        # 1. Zapisz zdjęcie/zdjęcia (dla każdej próby, także nieudanej)
        timestamp = datetime.now()
        timestamp_str = timestamp.strftime("%Y%m%d_%H%M%S")
        image_paths: List[str] = []

        # Preferujemy "images[]" (multi-frame) jeśli przyszło
        if images:
            for idx, up in enumerate(images[:3]):  # ograniczenie na wszelki wypadek
                fn = f"{timestamp_str}_{qr_code}_{idx}.jpg"
                p = os.path.join(UPLOAD_DIR, fn)
                with open(p, "wb") as buffer:
                    shutil.copyfileobj(up.file, buffer)
                image_paths.append(p)
        elif image is not None:
            image_filename = f"{timestamp_str}_{qr_code}.jpg"
            image_path = os.path.join(UPLOAD_DIR, image_filename)

            with open(image_path, "wb") as buffer:
                shutil.copyfileobj(image.file, buffer)
            image_paths.append(image_path)
        else:
            raise HTTPException(status_code=400, detail="Brak zdjęcia do weryfikacji")

        primary_image_path = image_paths[0]

        # 1b. Liveness (mrugnięcie) – jeśli dostaliśmy kilka klatek z kamery
        liveness_ok = False
        if len(image_paths) >= 3:
            # bierzemy do 6 klatek (frontend wysyła kilka)
            liveness_ok = face_service.detect_blink_liveness(image_paths[:6])
            if not liveness_ok:
                log = AccessLog(
                    timestamp=timestamp,
                    result="SUSPICIOUS",
                    match_score=None,
                    badge_id=None,
                    user_id=None,
                    image_path=primary_image_path,
                )
                db.add(log)
                db.commit()

                return VerificationResponse(
                    success=False,
                    message="Brak potwierdzenia liveness (mrugnięcie) – możliwe zdjęcie/ekran",
                    result="SUSPICIOUS",
                    log_id=log.id,
                )

        # 2. Prosta detekcja spoofingu (telefon / ekran ze zdjęciem)
        # Jeśli liveness przeszło, nie blokujemy już heurystyką "ekran" (unikamy fałszywych alarmów).
        if (not liveness_ok) and face_service.detect_screen_spoof(primary_image_path):
            log = AccessLog(
                timestamp=timestamp,
                result="SUSPICIOUS",
                match_score=None,
                badge_id=None,
                user_id=None,
                image_path=primary_image_path,
            )
            db.add(log)
            db.commit()

            return VerificationResponse(
                success=False,
                message="Podejrzenie uzycia zdjecia lub ekranu (telefon, monitor)",
                result="SUSPICIOUS",
                log_id=log.id,
            )

        # 3. Sprawdź czy kod QR istnieje w bazie
        badge = db.query(Badge).filter(Badge.qr_code == qr_code).first()
        if not badge:
            log = AccessLog(
                timestamp=timestamp,
                result="REJECT",
                match_score=None,
                badge_id=None,
                user_id=None,
                image_path=primary_image_path,
            )
            db.add(log)
            db.commit()

            return VerificationResponse(
                success=False,
                message="Nieprawidłowy kod QR",
                result="REJECT",
                log_id=log.id,
            )
        
        # 3. Sprawdź czy badge jest ważny
        if badge.valid_until and badge.valid_until < date.today():
            log = AccessLog(
                timestamp=timestamp,
                result="REJECT",
                match_score=None,
                badge_id=badge.id,
                user_id=badge.user_id,
                image_path=primary_image_path,
            )
            db.add(log)
            db.commit()

            return VerificationResponse(
                success=False,
                message="Przepustka wygasła",
                result="REJECT",
                log_id=log.id,
            )
        
        # 4. Sprawdź czy użytkownik jest aktywny
        user = db.query(User).filter(User.id == badge.user_id).first()
        if not user or not user.is_active:
            log = AccessLog(
                timestamp=timestamp,
                result="REJECT",
                match_score=None,
                badge_id=badge.id,
                user_id=user.id if user else None,
                image_path=primary_image_path,
            )
            db.add(log)
            db.commit()

            return VerificationResponse(
                success=False,
                message="Użytkownik nieaktywny",
                result="REJECT",
                log_id=log.id,
            )
        
        # 5. Rozpoznaj twarz
        # Obniżony threshold z 0.6 do 0.5 dla lepszej tolerancji na zmiany oświetlenia/pozycji
        face_result = face_service.recognize_face(primary_image_path, threshold=0.5)
        
        if not face_result:
            # Nie wykryto twarzy lub nie rozpoznano
            log = AccessLog(
                timestamp=timestamp,
                result="REJECT",
                match_score=None,
                badge_id=badge.id,
                user_id=user.id,
                image_path=primary_image_path
            )
            db.add(log)
            db.commit()
            
            return VerificationResponse(
                success=False,
                message="Nie rozpoznano twarzy",
                result="REJECT",
                log_id=log.id
            )
        
        recognized_face_id, match_score = face_result
        
        # 6. Sprawdź czy rozpoznana twarz pasuje do użytkownika z karty
        if recognized_face_id != user.face_id:
            # Podejrzana sytuacja - ktoś używa cudzej karty
            log = AccessLog(
                timestamp=timestamp,
                result="SUSPICIOUS",
                match_score=match_score,
                badge_id=badge.id,
                user_id=user.id,
                image_path=primary_image_path
            )
            db.add(log)
            db.commit()
            
            return VerificationResponse(
                success=False,
                message="Niezgodność twarzy z kartą - podejrzana sytuacja",
                result="SUSPICIOUS",
                match_score=match_score,
                user_id=user.id,
                log_id=log.id
            )
        
        # 7. Weryfikacja pomyślna
        # Obniżony próg z 0.6 do 0.5 dla lepszej tolerancji
        if match_score >= 0.5:
            log = AccessLog(
                timestamp=timestamp,
                result="ACCEPT",
                match_score=match_score,
                badge_id=badge.id,
                user_id=user.id,
                image_path=primary_image_path
            )
            db.add(log)
            db.commit()
            
            return VerificationResponse(
                success=True,
                message="Dostęp przyznany",
                result="ACCEPT",
                match_score=match_score,
                user_id=user.id,
                log_id=log.id,
                first_name=user.first_name,
                last_name=user.last_name
            )
        else:
            log = AccessLog(
                timestamp=timestamp,
                result="REJECT",
                match_score=match_score,
                badge_id=badge.id,
                user_id=user.id,
                image_path=primary_image_path
            )
            db.add(log)
            db.commit()
            
            return VerificationResponse(
                success=False,
                message="Niskie dopasowanie twarzy",
                result="REJECT",
                match_score=match_score,
                log_id=log.id
            )
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Błąd weryfikacji: {str(e)}")


@app.post("/api/users", response_model=UserResponse)
async def create_user(user: UserCreate, db: Session = Depends(get_db)):
    """Tworzenie nowego użytkownika"""
    # Automatyczne generowanie face_id jeśli nie podano
    if not user.face_id or user.face_id.strip() == "":
        # Generuj face_id na podstawie imienia i nazwiska + timestamp
        import time
        base_id = f"{user.first_name.upper()}_{user.last_name.upper()}"
        face_id = f"{base_id}_{int(time.time())}"
    else:
        face_id = user.face_id
    
    db_user = User(
        first_name=user.first_name,
        last_name=user.last_name,
        face_id=face_id,
        is_active=user.is_active
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


@app.get("/api/users", response_model=List[UserResponse])
async def get_users(db: Session = Depends(get_db)):
    """Pobranie listy wszystkich użytkowników"""
    users = db.query(User).all()
    return users


@app.get("/api/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: int, db: Session = Depends(get_db)):
    """Pobranie użytkownika po ID"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Użytkownik nie znaleziony")
    return user


@app.post("/api/users/{user_id}/register-face")
async def register_user_face(
    user_id: int,
    image: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Rejestracja twarzy użytkownika"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Użytkownik nie znaleziony")
    
    # Zapisz zdjęcie
    image_filename = f"register_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
    image_path = os.path.join(UPLOAD_DIR, image_filename)
    
    with open(image_path, "wb") as buffer:
        shutil.copyfileobj(image.file, buffer)
    
    # Zarejestruj twarz
    success = face_service.register_face(image_path, user.face_id)
    
    if success:
        return {"message": "Twarz zarejestrowana pomyślnie", "success": True}
    else:
        return {"message": "Nie wykryto twarzy na zdjęciu", "success": False}


@app.post("/api/badges", response_model=BadgeResponse)
async def create_badge(badge: BadgeCreate, db: Session = Depends(get_db)):
    """Tworzenie nowej przepustki"""
    db_badge = Badge(
        qr_code=badge.qr_code,
        valid_until=badge.valid_until,
        user_id=badge.user_id
    )
    db.add(db_badge)
    db.commit()
    db.refresh(db_badge)
    return db_badge


@app.get("/api/badges", response_model=List[BadgeResponse])
async def get_badges(db: Session = Depends(get_db)):
    """Pobranie listy wszystkich przepustek"""
    badges = db.query(Badge).all()
    return badges


@app.get("/api/badges/{badge_id}/qr")
async def get_badge_qr(badge_id: int, db: Session = Depends(get_db)):
    """Generowanie kodu QR dla przepustki"""
    badge = db.query(Badge).filter(Badge.id == badge_id).first()
    if not badge:
        raise HTTPException(status_code=404, detail="Przepustka nie znaleziona")
    
    qr_image = qr_service.generate_qr_code(badge.qr_code)
    return {"qr_code": badge.qr_code, "qr_image": qr_image}


@app.get("/api/users/{user_id}/check-qr")
async def check_user_qr(user_id: int, qr_code: str, db: Session = Depends(get_db)):
    """Sprawdzenie czy kod QR należy do użytkownika"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Użytkownik nie znaleziony")
    
    badge = db.query(Badge).filter(Badge.qr_code == qr_code).first()
    if not badge:
        return {"valid": False, "message": "Kod QR nie istnieje"}
    
    if badge.user_id != user_id:
        return {"valid": False, "message": "Kod QR nie należy do tego użytkownika"}
    
    # Sprawdź czy badge jest ważny
    if badge.valid_until and badge.valid_until < date.today():
        return {"valid": False, "message": "Przepustka wygasła"}
    
    return {"valid": True, "message": "Kod QR jest prawidłowy"}


@app.get("/api/logs", response_model=List[AccessLogResponse])
async def get_logs(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Pobranie logów dostępu"""
    query = db.query(AccessLog)
    
    if start_date:
        start = datetime.fromisoformat(start_date)
        query = query.filter(AccessLog.timestamp >= start)
    
    if end_date:
        end = datetime.fromisoformat(end_date)
        query = query.filter(AccessLog.timestamp <= end)
    
    logs = query.order_by(AccessLog.timestamp.desc()).limit(limit).all()
    return logs


@app.get("/api/reports/generate")
async def generate_report(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Generowanie raportu PDF"""
    start = datetime.now() - timedelta(days=30)
    end = datetime.now()
    
    if start_date:
        start = datetime.fromisoformat(start_date)
    if end_date:
        end = datetime.fromisoformat(end_date)
    
    # Pobierz logi
    logs = db.query(AccessLog).filter(
        and_(AccessLog.timestamp >= start, AccessLog.timestamp <= end)
    ).all()
    
    # Konwersja do formatu dict
    logs_data = []
    for log in logs:
        logs_data.append({
            "timestamp": log.timestamp,
            "result": log.result,
            "match_score": log.match_score,
            "badge_id": log.badge_id,
            "user_id": log.user_id,
            "image_path": log.image_path
        })
    
    # Generuj raport
    report_path = report_service.generate_access_report(logs_data, start, end)
    
    return FileResponse(
        report_path,
        media_type="application/pdf",
        filename=os.path.basename(report_path)
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)




