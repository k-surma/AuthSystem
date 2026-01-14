"""
Testy jednostkowe dla systemu weryfikacji tożsamości
Testują podstawowe funkcjonalności bez zależności od biblioteki face-recognition
"""

import pytest
import os
import tempfile
import shutil
from datetime import datetime, timedelta, date
from qr_service import QRService
from report_service import ReportService
from database import User, Badge, AccessLog
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


# ============================================================================
# TESTY DLA QRService - generowanie i walidacja kodów QR
# ============================================================================

class TestQRService:
    """
    Testy dla serwisu generowania kodów QR
    Sprawdzają czy kody QR są poprawnie generowane i walidowane
    """
    
    def test_generate_qr_code(self):
        """
        Test: Generowanie podstawowego kodu QR
        Sprawdza czy funkcja zwraca string base64 z obrazem QR
        """
        qr_service = QRService()
        test_data = "TEST_QR_CODE_123"
        qr_image = qr_service.generate_qr_code(test_data)
        
        # Sprawdź czy zwrócony jest string base64
        assert isinstance(qr_image, str)
        assert len(qr_image) > 0
    
    def test_generate_qr_code_different_data(self):
        """
        Test: Różne dane dają różne kody QR
        Sprawdza czy różne dane wejściowe generują różne kody QR
        """
        qr_service = QRService()
        data1 = "QR_CODE_1"
        data2 = "QR_CODE_2"
        
        qr1 = qr_service.generate_qr_code(data1)
        qr2 = qr_service.generate_qr_code(data2)
        
        # Różne dane powinny dać różne kody QR
        assert qr1 != qr2
    
    def test_validate_qr_code_valid(self):
        """
        Test: Walidacja prawidłowych kodów QR
        Sprawdza czy funkcja akceptuje prawidłowe kody QR
        """
        qr_service = QRService()
        valid_codes = ["ABC123", "TEST_CODE", "QR_CODE_12345"]
        
        for code in valid_codes:
            assert qr_service.validate_qr_code(code) == True
    
    def test_validate_qr_code_invalid(self):
        """
        Test: Walidacja nieprawidłowych kodów QR
        Sprawdza czy funkcja odrzuca nieprawidłowe kody (puste lub za długie)
        """
        qr_service = QRService()
        
        # Pusty string powinien być odrzucony
        assert qr_service.validate_qr_code("") == False
        
        # Zbyt długi kod (powyżej 1000 znaków) powinien być odrzucony
        long_code = "A" * 1001
        assert qr_service.validate_qr_code(long_code) == False


# ============================================================================
# TESTY DLA ReportService - generowanie raportów PDF
# ============================================================================

class TestReportService:
    """
    Testy dla serwisu generowania raportów PDF
    Sprawdzają czy raporty są poprawnie generowane z różnymi danymi
    """
    
    def setup_method(self):
        """Przygotowanie: tworzy tymczasowy katalog na raporty przed każdym testem"""
        self.temp_dir = tempfile.mkdtemp()
        self.report_service = ReportService(reports_dir=self.temp_dir)
    
    def teardown_method(self):
        """Sprzątanie: usuwa tymczasowy katalog po każdym teście"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_generate_access_report_empty_logs(self):
        """
        Test: Generowanie raportu z pustą listą logów
        Sprawdza czy system potrafi wygenerować raport nawet bez danych
        """
        start_date = datetime.now() - timedelta(days=7)
        end_date = datetime.now()
        
        report_path = self.report_service.generate_access_report(
            logs=[],
            start_date=start_date,
            end_date=end_date
        )
        
        # Sprawdź czy plik PDF został utworzony
        assert os.path.exists(report_path)
        assert report_path.endswith('.pdf')
    
    def test_generate_access_report_with_logs(self):
        """
        Test: Generowanie raportu z przykładowymi logami
        Sprawdza czy raport zawiera dane z logów (ACCEPT, REJECT, SUSPICIOUS)
        """
        start_date = datetime.now() - timedelta(days=7)
        end_date = datetime.now()
        
        # Przykładowe logi z różnymi wynikami
        logs = [
            {
                "timestamp": datetime.now() - timedelta(days=1),
                "result": "ACCEPT",
                "match_score": 0.95,
                "badge_id": 1,
                "user_id": 1,
                "image_path": "/path/to/image.jpg"
            },
            {
                "timestamp": datetime.now() - timedelta(days=2),
                "result": "REJECT",
                "match_score": 0.45,
                "badge_id": 2,
                "user_id": 2,
                "image_path": "/path/to/image2.jpg"
            },
            {
                "timestamp": datetime.now() - timedelta(days=3),
                "result": "SUSPICIOUS",
                "match_score": 0.75,
                "badge_id": 3,
                "user_id": 3,
                "image_path": "/path/to/image3.jpg"
            }
        ]
        
        report_path = self.report_service.generate_access_report(
            logs=logs,
            start_date=start_date,
            end_date=end_date
        )
        
        # Sprawdź czy plik PDF został utworzony i nie jest pusty
        assert os.path.exists(report_path)
        assert report_path.endswith('.pdf')
        assert os.path.getsize(report_path) > 0
    
    def test_generate_access_report_default_dates(self):
        """
        Test: Generowanie raportu z domyślnymi datami
        Sprawdza czy system automatycznie ustawia daty gdy nie są podane
        """
        logs = [
            {
                "timestamp": datetime.now(),
                "result": "ACCEPT",
                "match_score": 0.90,
                "badge_id": 1,
                "user_id": 1,
                "image_path": "/path/to/image.jpg"
            }
        ]
        
        report_path = self.report_service.generate_access_report(logs=logs)
        
        # Sprawdź czy plik PDF został utworzony
        assert os.path.exists(report_path)
        assert report_path.endswith('.pdf')


# ============================================================================
# TESTY DLA BAZY DANYCH - modele i relacje
# ============================================================================

class TestDatabase:
    """
    Testy dla modeli bazy danych
    Sprawdzają czy można tworzyć użytkowników, przepustki i logi oraz relacje między nimi
    """
    
    def setup_method(self):
        """
        Przygotowanie: tworzy bazę danych w pamięci przed każdym testem
        Używa SQLite w pamięci, więc dane nie są zapisywane na dysk
        """
        self.test_db_url = "sqlite:///:memory:"
        self.engine = create_engine(self.test_db_url, connect_args={"check_same_thread": False})
        from database import Base
        Base.metadata.create_all(bind=self.engine)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
    
    def test_create_user(self):
        """
        Test: Tworzenie użytkownika w bazie danych
        Sprawdza czy można utworzyć użytkownika z podstawowymi danymi
        """
        db = self.SessionLocal()
        try:
            user = User(
                first_name="Jan",
                last_name="Kowalski",
                face_id="face_123",
                is_active=True
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            
            # Sprawdź czy użytkownik został utworzony z poprawnymi danymi
            assert user.id is not None
            assert user.first_name == "Jan"
            assert user.last_name == "Kowalski"
            assert user.face_id == "face_123"
            assert user.is_active == True
        finally:
            db.close()
    
    def test_create_badge(self):
        """
        Test: Tworzenie przepustki dla użytkownika
        Sprawdza czy można utworzyć przepustkę powiązaną z użytkownikiem
        """
        db = self.SessionLocal()
        try:
            # Najpierw utwórz użytkownika
            user = User(
                first_name="Jan",
                last_name="Kowalski",
                face_id="face_123",
                is_active=True
            )
            db.add(user)
            db.commit()
            
            # Teraz utwórz przepustkę dla tego użytkownika
            badge = Badge(
                qr_code="QR_CODE_123",
                valid_until=date(2025, 12, 31),
                user_id=user.id
            )
            db.add(badge)
            db.commit()
            db.refresh(badge)
            
            # Sprawdź czy przepustka została utworzona z poprawnymi danymi
            assert badge.id is not None
            assert badge.qr_code == "QR_CODE_123"
            assert badge.user_id == user.id
        finally:
            db.close()
    
    def test_create_access_log(self):
        """
        Test: Tworzenie logu dostępu
        Sprawdza czy można zapisać log weryfikacji dostępu
        """
        db = self.SessionLocal()
        try:
            log = AccessLog(
                timestamp=datetime.now(),
                result="ACCEPT",
                match_score=0.95,
                badge_id=1,
                user_id=1,
                image_path="/path/to/image.jpg"
            )
            db.add(log)
            db.commit()
            db.refresh(log)
            
            # Sprawdź czy log został utworzony z poprawnymi danymi
            assert log.id is not None
            assert log.result == "ACCEPT"
            assert log.match_score == 0.95
        finally:
            db.close()
    
    def test_user_badge_relationship(self):
        """
        Test: Relacja między użytkownikiem a przepustką
        Sprawdza czy relacje SQLAlchemy działają poprawnie (użytkownik.badges, badge.user)
        """
        db = self.SessionLocal()
        try:
            # Utwórz użytkownika
            user = User(
                first_name="Jan",
                last_name="Kowalski",
                face_id="face_123",
                is_active=True
            )
            db.add(user)
            db.commit()
            
            # Utwórz przepustkę dla użytkownika
            badge = Badge(
                qr_code="QR_CODE_123",
                valid_until=date(2025, 12, 31),
                user_id=user.id
            )
            db.add(badge)
            db.commit()
            
            # Sprawdź relację - użytkownik powinien mieć przepustkę
            assert len(user.badges) == 1
            assert user.badges[0].qr_code == "QR_CODE_123"
            
            # Sprawdź relację w drugą stronę - przepustka powinna mieć użytkownika
            assert badge.user.first_name == "Jan"
        finally:
            db.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
