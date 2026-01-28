import qrcode
from PIL import Image
import io
import base64
from typing import Optional

class QRService:
    @staticmethod
    def generate_qr_code(data: str) -> str:
        """Generuje kod QR i zwraca jako base64 string"""
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(data)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Konwersja do base64
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        
        return img_str
    
    @staticmethod
    def validate_qr_code(qr_code: str) -> bool:
        """Podstawowa walidacja formatu kodu QR"""
        # Można dodać bardziej zaawansowaną walidację
        return len(qr_code) > 0 and len(qr_code) < 1000




