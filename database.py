from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, Float, ForeignKey, Date
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime, date
import enum

SQLALCHEMY_DATABASE_URL = "sqlite:///./access_control.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


class ResultEnum(enum.Enum):
    ACCEPT = "ACCEPT"
    REJECT = "REJECT"
    SUSPICIOUS = "SUSPICIOUS"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    face_id = Column(String, unique=True, index=True)
    is_active = Column(Boolean, default=True)
    first_name = Column(String)
    last_name = Column(String)
    
    badges = relationship("Badge", back_populates="user")
    access_logs = relationship("AccessLog", back_populates="user")


class Badge(Base):
    __tablename__ = "badges"

    id = Column(Integer, primary_key=True, index=True)
    qr_code = Column(String, unique=True, index=True)
    valid_until = Column(Date)
    user_id = Column(Integer, ForeignKey("users.id"))
    
    user = relationship("User", back_populates="badges")
    access_logs = relationship("AccessLog", back_populates="badge")


class AccessLog(Base):
    __tablename__ = "access_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    result = Column(String)  # ACCEPT, REJECT, SUSPICIOUS
    match_score = Column(Float)
    badge_id = Column(Integer, ForeignKey("badges.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    image_path = Column(String, nullable=True)
    
    user = relationship("User", back_populates="access_logs")
    badge = relationship("Badge", back_populates="access_logs")


def init_db():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


