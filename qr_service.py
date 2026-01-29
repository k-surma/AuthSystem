import qrcode
from PIL import Image
import io
import base64
from typing import Optional


class QRService:
    @staticmethod
    def generate_qr_code(data: str) -> str:
        """
        Zwraca obraz QR zakodowany jako base64 PNG na podstawie przekazanego tekstu.
        """
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(data)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        
        return img_str
    
    @staticmethod
    def validate_qr_code(qr_code: str) -> bool:
        """
        Prosta walidacja techniczna (np. długość).
        Faktyczne sprawdzenie, czy kod jest „nasz”, odbywa się w bazie (tabela Badge).
        """
        return bool(qr_code) and len(qr_code) < 1000
