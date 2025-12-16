"""
Skrypt pomocniczy do inicjalizacji przykładowych danych testowych
Uruchom: python test_setup.py
"""
from database import SessionLocal, init_db, User, Badge
from datetime import date, timedelta
import random
import string

def generate_random_string(length=10):
    """Generuje losowy string"""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

def setup_test_data():
    """Tworzy przykładowe dane testowe"""
    init_db()
    db = SessionLocal()
    
    try:
        # Sprawdź czy już istnieją dane
        if db.query(User).count() > 0:
            print("Baza danych już zawiera dane. Pomijam tworzenie przykładowych danych.")
            return
        
        # Tworzenie przykładowych użytkowników
        users_data = [
            {"first_name": "Jan", "last_name": "Kowalski", "face_id": "JAN_KOWALSKI_001"},
            {"first_name": "Anna", "last_name": "Nowak", "face_id": "ANNA_NOWAK_002"},
            {"first_name": "Piotr", "last_name": "Wiśniewski", "face_id": "PIOTR_WISNIEWSKI_003"},
        ]
        
        users = []
        for user_data in users_data:
            user = User(
                first_name=user_data["first_name"],
                last_name=user_data["last_name"],
                face_id=user_data["face_id"],
                is_active=True
            )
            db.add(user)
            users.append(user)
        
        db.commit()
        
        # Tworzenie przepustek dla użytkowników
        for user in users:
            qr_code = f"QR_{user.face_id}_{generate_random_string(8)}"
            badge = Badge(
                qr_code=qr_code,
                valid_until=date.today() + timedelta(days=365),  # Ważna przez rok
                user_id=user.id
            )
            db.add(badge)
            print(f"Utworzono przepustkę dla {user.first_name} {user.last_name}: {qr_code}")
        
        db.commit()
        print("\n✓ Przykładowe dane zostały utworzone!")
        print("\nUżytkownicy:")
        for user in users:
            print(f"  - {user.first_name} {user.last_name} (Face ID: {user.face_id})")
        
        print("\n⚠ UWAGA: Aby system działał poprawnie, musisz zarejestrować twarze użytkowników")
        print("   przez panel administracyjny (/admin) -> 'Zarejestruj twarz użytkownika'")
        
    except Exception as e:
        print(f"Błąd podczas tworzenia danych testowych: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    setup_test_data()


