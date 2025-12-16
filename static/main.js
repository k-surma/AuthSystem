let stream = null;
let capturedImage = null;

// Inicjalizacja kamery
async function initCamera() {
    try {
        stream = await navigator.mediaDevices.getUserMedia({ 
            video: { 
                facingMode: 'user',
                width: { ideal: 640 },
                height: { ideal: 480 }
            } 
        });
        const video = document.getElementById('video');
        video.srcObject = stream;
        
        updateStatus('Kamera gotowa. Zeskanuj kod QR i kliknij "Zweryfikuj"');
    } catch (error) {
        console.error('Błąd dostępu do kamery:', error);
        updateStatus('Błąd: Nie można uzyskać dostępu do kamery', 'error');
    }
}

// Zatrzymanie kamery
function stopCamera() {
    if (stream) {
        stream.getTracks().forEach(track => track.stop());
        stream = null;
    }
}

// Aktualizacja statusu
function updateStatus(message, type = 'info') {
    const statusEl = document.getElementById('status');
    statusEl.textContent = message;
    statusEl.className = `status-message ${type}`;
}

// Wykonanie zdjęcia
function capturePhoto() {
    const video = document.getElementById('video');
    const canvas = document.getElementById('canvas');
    const context = canvas.getContext('2d');
    
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    context.drawImage(video, 0, 0);
    
    canvas.toBlob((blob) => {
        capturedImage = blob;
        updateStatus('Zdjęcie wykonane! Teraz kliknij "Zweryfikuj"');
    }, 'image/jpeg', 0.95);
}

// Weryfikacja dostępu
async function verifyAccess() {
    const qrCode = document.getElementById('qr-code').value.trim();
    const resultEl = document.getElementById('result');
    
    if (!qrCode) {
        resultEl.textContent = 'Proszę wprowadzić kod QR';
        resultEl.className = 'result-message error';
        return;
    }
    
    if (!capturedImage) {
        resultEl.textContent = 'Proszę najpierw wykonać zdjęcie';
        resultEl.className = 'result-message error';
        return;
    }
    
    // Wykonaj zdjęcie jeśli nie zostało wykonane
    if (!capturedImage) {
        capturePhoto();
        await new Promise(resolve => setTimeout(resolve, 500));
    }
    
    const formData = new FormData();
    formData.append('qr_code', qrCode);
    formData.append('image', capturedImage, 'photo.jpg');
    
    resultEl.textContent = 'Weryfikacja w toku...';
    resultEl.className = 'result-message';
    
    try {
        const response = await fetch('/api/verify', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (data.success) {
            resultEl.textContent = `✓ ${data.message} (Score: ${(data.match_score * 100).toFixed(1)}%)`;
            resultEl.className = 'result-message success';
            updateStatus('Dostęp przyznany!', 'success');
        } else {
            if (data.result === 'SUSPICIOUS') {
                resultEl.textContent = `⚠ ${data.message}`;
                resultEl.className = 'result-message warning';
                updateStatus('Podejrzana sytuacja wykryta!', 'warning');
            } else {
                resultEl.textContent = `✗ ${data.message}`;
                resultEl.className = 'result-message error';
                updateStatus('Dostęp odrzucony', 'error');
            }
        }
        
        // Reset po 3 sekundach
        setTimeout(() => {
            capturedImage = null;
            document.getElementById('qr-code').value = '';
        }, 3000);
        
    } catch (error) {
        console.error('Błąd weryfikacji:', error);
        resultEl.textContent = 'Błąd podczas weryfikacji. Spróbuj ponownie.';
        resultEl.className = 'result-message error';
    }
}

// Skanowanie QR (uproszczone - wymaga biblioteki jsQR)
async function scanQR() {
    const video = document.getElementById('video');
    const canvas = document.getElementById('canvas');
    const context = canvas.getContext('2d');
    
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    context.drawImage(video, 0, 0);
    
    // Uproszczone - w rzeczywistości potrzebna biblioteka jsQR
    // Tutaj tylko symulacja - użytkownik może ręcznie wprowadzić kod
    updateStatus('Skanowanie QR... (Wprowadź kod ręcznie lub użyj biblioteki jsQR)');
}

// Event listeners
document.addEventListener('DOMContentLoaded', () => {
    initCamera();
    
    document.getElementById('capture-btn').addEventListener('click', capturePhoto);
    document.getElementById('verify-btn').addEventListener('click', verifyAccess);
    document.getElementById('scan-qr-btn').addEventListener('click', scanQR);
    
    // Cleanup przy zamknięciu strony
    window.addEventListener('beforeunload', stopCamera);
});

// Obsługa Enter w polu QR
document.getElementById('qr-code').addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        capturePhoto();
        setTimeout(verifyAccess, 500);
    }
});


