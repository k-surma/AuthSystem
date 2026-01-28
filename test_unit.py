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

class TestQRService:
    
    def test_generate_qr_code(self):
        qr_service = QRService()
        test_data = "TEST_QR_CODE_123"
        qr_image = qr_service.generate_qr_code(test_data)
        
        assert isinstance(qr_image, str)
        assert len(qr_image) > 0
    
    def test_generate_qr_code_different_data(self):
        qr_service = QRService()
        data1 = "QR_CODE_1"
        data2 = "QR_CODE_2"
        
        qr1 = qr_service.generate_qr_code(data1)
        qr2 = qr_service.generate_qr_code(data2)
        
        assert qr1 != qr2
    
    def test_validate_qr_code_valid(self):
        qr_service = QRService()
        valid_codes = ["ABC123", "TEST_CODE", "QR_CODE_12345"]
        
        for code in valid_codes:
            assert qr_service.validate_qr_code(code) == True
    
    def test_validate_qr_code_invalid(self):
        qr_service = QRService()
        
        assert qr_service.validate_qr_code("") == False
        
        long_code = "A" * 1001
        assert qr_service.validate_qr_code(long_code) == False


class TestReportService:
    
    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()
        self.report_service = ReportService(reports_dir=self.temp_dir)
    
    def teardown_method(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_generate_access_report_empty_logs(self):
        start_date = datetime.now() - timedelta(days=7)
        end_date = datetime.now()
        
        report_path = self.report_service.generate_access_report(
            logs=[],
            start_date=start_date,
            end_date=end_date
        )
        
        assert os.path.exists(report_path)
        assert report_path.endswith('.pdf')
    
    def test_generate_access_report_with_logs(self):
        start_date = datetime.now() - timedelta(days=7)
        end_date = datetime.now()
        
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
        
        assert os.path.exists(report_path)
        assert report_path.endswith('.pdf')
        assert os.path.getsize(report_path) > 0
    
    def test_generate_access_report_default_dates(self):
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
        
        assert os.path.exists(report_path)
        assert report_path.endswith('.pdf')


class TestDatabase:
    
    def setup_method(self):
        self.test_db_url = "sqlite:///:memory:"
        self.engine = create_engine(self.test_db_url, connect_args={"check_same_thread": False})
        from database import Base
        Base.metadata.create_all(bind=self.engine)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
    
    def test_create_user(self):
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
            
            assert user.id is not None
            assert user.first_name == "Jan"
            assert user.last_name == "Kowalski"
            assert user.face_id == "face_123"
            assert user.is_active == True
        finally:
            db.close()
    
    def test_create_badge(self):
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
            
            badge = Badge(
                qr_code="QR_CODE_123",
                valid_until=date(2025, 12, 31),
                user_id=user.id
            )
            db.add(badge)
            db.commit()
            db.refresh(badge)
            
            assert badge.id is not None
            assert badge.qr_code == "QR_CODE_123"
            assert badge.user_id == user.id
        finally:
            db.close()
    
    def test_create_access_log(self):
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
            
            assert log.id is not None
            assert log.result == "ACCEPT"
            assert log.match_score == 0.95
        finally:
            db.close()
    
    def test_user_badge_relationship(self):
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
            
            badge = Badge(
                qr_code="QR_CODE_123",
                valid_until=date(2025, 12, 31),
                user_id=user.id
            )
            db.add(badge)
            db.commit()
            
            assert len(user.badges) == 1
            assert user.badges[0].qr_code == "QR_CODE_123"
            
            assert badge.user.first_name == "Jan"
        finally:
            db.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
